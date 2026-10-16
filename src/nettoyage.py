"""Étape 2 : mise en forme et harmonisation des données brutes."""
import difflib
import json
import math
import re
import unicodedata

import numpy as np
import pandas as pd
import rasterio
from rasterio.features import rasterize
from rasterio.windows import Window

from config import (DOSSIER_TRAITE, INDICATEURS, INDICATEURS_DHS, INDICATEURS_EMPLOI, INDICATEURS_PROJECTIONS,
                    NIVEAUX, PARENTS, RGPH3_TOTAL, TYPES_SANTE, brut, traite)
from geometrie import anneaux, boite, contient, point_interieur, superficie_km2
import rgph3

# Variantes d'orthographe connues -> forme normalisée de référence
ALIAS_NOMS = {
    "matsiatraambony": "hautematsiatra",
    "vakinankarata": "vakinankaratra",      # DHS
    "anamoroniimania": "amoronimania",      # DHS
    "toliarai": "toliaryi",                 # RGPH-3
    "toliaraii": "toliaryii",               # RGPH-3
    "vakinakaratra": "vakinankaratra",      # établissements de santé
    "analanjorofo": "analanjirofo",         # établissements de santé
}


def cle_nom(nom):
    """Clé de jointure robuste : sans accents, apostrophes, tirets ni espaces.

    Les chiffres sont conservés pour distinguer les arrondissements (« 2e Arrondissement »).
    """
    nom = unicodedata.normalize("NFKD", str(nom)).encode("ascii", "ignore").decode()
    cle = re.sub(r"[^a-z0-9]", "", nom.lower())
    return ALIAS_NOMS.get(cle, cle)


def _lire_banque_mondiale(cle):
    with open(brut(cle), encoding="utf-8") as f:
        lu = pd.DataFrame(json.load(f))
    return pd.DataFrame({
        "code": lu["indicator"].str["id"],
        "annee": lu["date"].astype(int),
        "valeur": lu["value"],
    }).dropna()


def indicateurs_nationaux():
    df = _lire_banque_mondiale("indicateurs")

    series = (df[df["code"].isin(INDICATEURS)]
              .pivot(index="annee", columns="code", values="valeur")
              .rename(columns=INDICATEURS)
              .sort_index())

    pyr = df[df["code"].str.match(r"SP\.POP\.\d{4}\.|SP\.POP\.80UP\.")].copy()
    pyr["groupe_age"] = (pyr["code"].str.split(".").str[2]
                         .str.replace(r"^(\d\d)(\d\d)$", lambda m: f"{int(m[1])}-{int(m[2])}", regex=True)
                         .replace("80UP", "80+"))
    pyr["sexe"] = pyr["code"].str[-2:].map({"FE": "F", "MA": "H"})
    pyramide = pyr[["annee", "groupe_age", "sexe", "valeur"]].rename(columns={"valeur": "effectif"})
    return series, pyramide


def population(niveau):
    """Population par unité administrative et par année, au format long."""
    code = NIVEAUX[niveau]["code"]
    df = pd.read_csv(brut("population", code=code.lower()), encoding="utf-8-sig")
    # La dernière colonne « T_TL » correspond à 2018. Ce sont des estimations INSTAT/BNGRC
    # projetées depuis les données de 2009, pas les résultats du recensement RGPH-3.
    df = df.rename(columns={"T_TL": "T_TL_2018"})
    identifiants = {f"{code}_PCODE": "pcode", f"{code}_EN": "nom"}
    for parent, colonne in (("ADM1", "region"), ("ADM2", "district"), ("ADM3", "commune")):
        if parent < code:
            identifiants |= {f"{parent}_PCODE": f"{colonne}_pcode", f"{parent}_EN": colonne}
    long = df.melt(id_vars=list(identifiants),
                   value_vars=[c for c in df.columns if c.startswith("T_TL_")],
                   var_name="annee", value_name="population")
    long["annee"] = long["annee"].str[-4:].astype(int)
    long = long.rename(columns=identifiants)
    # Clé de jointure avec les contours : les noms de communes se répètent d'un district
    # à l'autre, et ceux des fokontany d'une commune à l'autre.
    long["cle"] = long["nom"].map(cle_nom)
    if code in ("ADM3", "ADM4"):
        long["cle"] = long["district"].map(cle_nom) + "/" + long["cle"]
    if code == "ADM4":
        long["cle"] = (long["district"].map(cle_nom) + "/" + long["commune"].map(cle_nom)
                       + "/" + long["nom"].map(cle_nom))
        # Deux fokontany homonymes d'une même commune ne peuvent pas être distingués dans
        # les contours (qui n'ont pas de P-code) : on les fusionne.
        colonnes = [c for c in long.columns if c not in ("pcode", "population")]
        long = (long.groupby(colonnes, as_index=False)
                .agg(pcode=("pcode", "|".join), population=("population", "sum")))
        long = long[["pcode", *[c for c in long.columns if c != "pcode"]]]
    return long.sort_values(["annee", "pcode"]).reset_index(drop=True)


def _lire_contours(niveau):
    with open(brut("contours", niveau=niveau), encoding="utf-8") as f:
        return json.load(f)["features"]


def _fusionner(geo1, geo2):
    polys = [g["coordinates"] if g["type"] == "MultiPolygon" else [g["coordinates"]] for g in (geo1, geo2)]
    return {"type": "MultiPolygon", "coordinates": polys[0] + polys[1]}


def rattacher_contours(niveau, cles_connues, contours_parent=None, cles_fusionnees=()):
    """Associe chaque contour geoBoundaries à une clé de la table de population.

    Les contours de communes et de fokontany n'indiquent pas leur unité parente : on la
    retrouve en cherchant le contour parent qui contient un point intérieur de l'unité.
    """
    rattaches, erreurs = {}, []
    if contours_parent is not None:
        parents = [(cle, geo, boite(geo)) for cle, geo in contours_parent.items()]
    for feat in _lire_contours(niveau):
        cle = cle_nom(feat["properties"]["shapeName"])
        if contours_parent is not None:
            x, y = point_interieur(feat["geometry"])
            candidats = [f"{c}/{cle}" for c, geo, b in parents
                         if b[0] <= x <= b[2] and b[1] <= y <= b[3] and contient(geo, (x, y))]
            # Les contours simplifiés se chevauchent parfois aux frontières.
            valides = [c for c in candidats if c in cles_connues]
            cle = valides[0] if valides else (candidats[0] if candidats else f"?/{cle}")
        if cle in rattaches:
            if cle not in cles_fusionnees:
                erreurs.append(f"contour en double : {cle}")
            rattaches[cle] = _fusionner(rattaches[cle], feat["geometry"])
            continue
        rattaches[cle] = feat["geometry"]
    sans_contour = sorted(set(cles_connues) - set(rattaches))
    sans_population = sorted(set(rattaches) - set(cles_connues))
    if sans_contour:
        erreurs.append(f"{len(sans_contour)} sans contour : {sans_contour[:10]}")
    if sans_population:
        erreurs.append(f"{len(sans_population)} contours sans population : {sans_population[:10]}")
    if erreurs:
        raise ValueError(f"Rattachement des contours ({niveau}) :\n- " + "\n- ".join(erreurs))
    return rattaches


def table_unites(df, contours):
    """Population, superficie et densité pour l'année la plus récente (estimation 2018)."""
    t = df[df["annee"] == df["annee"].max()].drop(columns="annee").copy()
    t["superficie_km2"] = [superficie_km2(contours[c]) for c in t["cle"]]
    t["densite"] = t["population"] / t["superficie_km2"]
    return t.sort_values("population", ascending=False).reset_index(drop=True)


def controles(series, pyramide, niveaux):
    """Contrôles de cohérence simples ; lève une erreur si un contrôle échoue."""
    erreurs = []
    for niveau, donnees in niveaux.items():
        df = donnees["population"]
        n, attendus = df["pcode"].str.split("|").explode().nunique(), NIVEAUX[niveau]["attendus"]
        if n != attendus:
            erreurs.append(f"{n} {niveau} trouvés au lieu de {attendus}")
        if df["cle"].nunique() != df["pcode"].nunique():
            erreurs.append(f"noms de {niveau} en double après normalisation")
        if df["population"].isna().any() or (df["population"] <= 0).any():
            erreurs.append(f"population manquante ou nulle ({niveau})")

    # Chaque niveau doit s'emboîter exactement dans son niveau parent.
    for niveau, parent in PARENTS.items():
        colonne = parent[:-1] + "_pcode"   # « regions » -> « region_pcode »
        somme = niveaux[niveau]["population"].groupby(["annee", colonne])["population"].sum()
        reference = niveaux[parent]["population"].set_index(["annee", "pcode"])["population"]
        ecart = (somme / reference.reindex(somme.index) - 1).abs()
        if ecart.isna().any() or (ecart > 0.005).any():
            erreurs.append(f"somme des {niveau} ≠ population des {parent} (écart max {ecart.max():.2%})")

    annee = pyramide["annee"].max()
    total_pyr = pyramide.loc[pyramide["annee"] == annee, "effectif"].sum()
    total = series.loc[annee, "population"]
    if abs(total_pyr - total) / total > 0.01:
        erreurs.append(f"pyramide {annee} ({total_pyr:,.0f}) ≠ population totale ({total:,.0f})")
    if erreurs:
        raise ValueError("Contrôles qualité échoués :\n- " + "\n- ".join(erreurs))
    print("  Contrôles qualité : OK")


def projections():
    """Projections ONU (WPP) annuelles jusqu'en 2050."""
    df = _lire_banque_mondiale("projections")
    return (df.pivot(index="annee", columns="code", values="valeur")
            .rename(columns=INDICATEURS_PROJECTIONS).sort_index())


def dhs(regions):
    """Indicateurs DHS de la dernière enquête, une ligne par région (22)."""
    with open(brut("dhs"), encoding="utf-8") as f:
        lu = json.load(f)
    df = pd.DataFrame(lu["donnees"])
    # « Province » sans préfixe, « ..Région », « ....sous-région » : on garde les régions.
    df = df[df["CharacteristicLabel"].str.match(r"^\.\.[^.]")]
    df = df[df["IsPreferred"] == 1].copy()
    df["cle"] = df["CharacteristicLabel"].str.lstrip(".").map(cle_nom)
    if df.duplicated(["cle", "IndicatorId"]).any():
        raise ValueError("DHS : plusieurs valeurs pour un même indicateur et une même région")
    table = (df.pivot(index="cle", columns="IndicatorId", values="Value")
             .rename(columns=INDICATEURS_DHS))
    ref = regions.drop_duplicates("cle").set_index("cle")[["pcode", "nom"]]
    inconnues = sorted(set(table.index) - set(ref.index))
    manquantes = sorted(set(ref.index) - set(table.index))
    if inconnues or manquantes:
        raise ValueError(f"DHS : régions non reconnues {inconnues}, régions manquantes {manquantes}")
    table = ref.join(table).reset_index()
    enquete = lu["enquete"]
    table.attrs["enquete"] = f"{enquete['SurveyType']} {enquete['SurveyYear']}"
    return table[["cle", "pcode", "nom", *[c for c in INDICATEURS_DHS.values() if c in table]]]


def worldpop(niveaux, series_projetees):
    """Somme des pixels WorldPop par commune et par année, agrégée aux niveaux supérieurs."""
    contours = niveaux["communes"]["contours"]
    cles = list(contours)
    motif = brut("worldpop", annee="*")
    fichiers = sorted(motif.parent.glob(motif.name))
    if not fichiers:
        raise ValueError("WorldPop : aucune grille téléchargée")
    zones, lignes, hors_communes = None, [], {}
    for fichier in fichiers:
        annee = int(fichier.stem.split("_")[1])
        with rasterio.open(fichier) as src:
            grille = src.read(1, masked=True).filled(0).astype("float64")
            if zones is None:  # toutes les années partagent la même grille
                zones = rasterize(((g, i + 1) for i, g in enumerate(contours.values())),
                                  out_shape=src.shape, transform=src.transform, fill=0, dtype="int32")
        sommes = np.bincount(zones.ravel(), weights=grille.ravel(), minlength=len(cles) + 1)
        hors_communes[annee] = sommes[0] / sommes.sum()
        lignes.append(pd.DataFrame({"cle": cles, "annee": annee, "population": sommes[1:]}))
    communes = pd.concat(lignes, ignore_index=True)

    # Contrôle : écart au total national de l'ONU et part de la population hors contours
    total = communes.groupby("annee")["population"].sum() / (1 - pd.Series(hors_communes))
    onu = series_projetees["population"].reindex(total.index)
    ecart = (total / onu - 1).abs()
    if (ecart > 0.05).any() or max(hors_communes.values()) > 0.02:
        raise ValueError(f"WorldPop : écart à l'ONU {ecart.max():.1%}, "
                         f"hors communes {max(hors_communes.values()):.1%}")

    parents = niveaux["communes"]["unites"].set_index("cle")[["district_pcode", "region_pcode"]]
    communes = communes.join(parents, on="cle")
    resultats = {"communes": communes.drop(columns=["district_pcode", "region_pcode"])}
    for niveau, colonne in (("districts", "district_pcode"), ("regions", "region_pcode")):
        cle_par_pcode = niveaux[niveau]["unites"].set_index("pcode")["cle"]
        agrege = communes.groupby([colonne, "annee"], as_index=False)["population"].sum()
        agrege["cle"] = agrege[colonne].map(cle_par_pcode)
        resultats[niveau] = agrege[["cle", "annee", "population"]]
    return resultats


COLONNES_RGPH = ["hommes", "femmes", "population", "urbain", "rural", "menages", "menages_chef_femme",
                 "menages_urbains"]


def _chiffres(ligne):
    return {c: ligne[c] for c in COLONNES_RGPH}


def _menages(df):
    """Taille moyenne des ménages ordinaires et part des ménages dirigés par une femme."""
    df["taille_menage"] = df["population"] / df["menages"]
    df["taille_menage_urbain"] = (df["urbain"] / df["menages_urbains"]).where(df["menages_urbains"] > 0)
    df["taille_menage_rural"] = (df["rural"] / (df["menages"] - df["menages_urbains"])).where(
        df["menages"] > df["menages_urbains"])
    df["chef_femme_pct"] = 100 * df["menages_chef_femme"] / df["menages"]


def _ajouter_menages(blocs, blocs_menages, districts_pdf):
    """Joint le tableau 13 (ménages) au tableau 10 (population), commune par commune.

    Les deux tableaux listent les mêmes communes dans le même ordre, mais leurs noms diffèrent
    parfois : le tableau 10 imprime souvent le nom du district à la place de celui de la
    commune (« Taolagnaro » cinq fois), le tableau 13 le fait précéder du nom du district
    (« Soavinandriana Amparaky »). L'alignement est donc vérifié par les nombres (sommes,
    milieu urbain ou rural, taille des ménages), et le nom du tableau 13 est gardé en second
    choix pour le rapprochement avec HDX (voir _noms_possibles).
    """
    erreurs = []
    if len(blocs_menages) != len(blocs):
        return [f"{len(blocs_menages)} districts au tableau 13 contre {len(blocs)} au tableau 10"]
    for d, bloc, bloc_m in zip(districts_pdf, blocs, blocs_menages):
        if len(bloc_m["communes"]) != len(bloc["communes"]):
            erreurs.append(f"{d['nom']} : {len(bloc_m['communes'])} communes au tableau 13 "
                           f"contre {len(bloc['communes'])} au tableau 10")
            continue
        if sum(c["menages"] for c in bloc_m["communes"]) != bloc_m["total"]["menages"]:
            erreurs.append(f"ménages de {d['nom']} : somme des communes différente du total du district")
        for ligne, ligne_m in zip([bloc["total"], *bloc["communes"]], [bloc_m["total"], *bloc_m["communes"]]):
            nom = ligne_m.get("nom", d["nom"])
            if (ligne_m["menages_urbains"] > 0) != (ligne["urbain"] > 0):
                erreurs.append(f"{d['nom']} : « {ligne.get('nom')} » (tableau 10) et « {nom} » (tableau 13) "
                               "n'ont pas le même milieu")
            if (ligne_m["menages_urbains"] + ligne_m["menages_ruraux"] != ligne_m["menages"]
                    or ligne_m["menages_chef_homme"] + ligne_m["menages_chef_femme"] != ligne_m["menages"]):
                erreurs.append(f"{nom} : sous-totaux des ménages incohérents")
            if not 1 < ligne["population"] / max(ligne_m["menages"], 1) < 10:
                erreurs.append(f"{nom} : taille de ménage invraisemblable")
            ligne["menages"] = ligne_m["menages"]
            ligne["menages_chef_femme"] = ligne_m["menages_chef_femme"]
            ligne["menages_urbains"] = ligne_m["menages_urbains"]
            if "nom" in ligne_m:
                ligne["nom_tableau_13"] = ligne_m["nom"]
    return erreurs


def _controler_tableau_16(blocs, blocs_controle, districts_pdf):
    """Le tableau 16 doit redonner, ligne à ligne, la population (tableau 10), les ménages
    (tableau 13) et, à l'arrondi près, la taille moyenne des ménages par milieu."""
    if len(blocs_controle) != len(blocs):
        return [f"{len(blocs_controle)} districts au tableau 16 contre {len(blocs)} au tableau 10"]
    erreurs = []
    for d, bloc, bloc_c in zip(districts_pdf, blocs, blocs_controle):
        if len(bloc_c["communes"]) != len(bloc["communes"]):
            erreurs.append(f"{d['nom']} : {len(bloc_c['communes'])} communes au tableau 16 "
                           f"contre {len(bloc['communes'])} au tableau 10")
            continue
        for ligne, ligne_c in zip([bloc["total"], *bloc["communes"]], [bloc_c["total"], *bloc_c["communes"]]):
            nom = ligne_c.get("nom", d["nom"])
            attendu = {"population_menages": ligne["population"], "population_urbaine_menages": ligne["urbain"],
                       "menages": ligne["menages"], "menages_urbains": ligne["menages_urbains"]}
            ecarts = [c for c, v in attendu.items() if ligne_c[c] != v]
            for population, menages, taille in [("population_menages", "menages", "taille_menage"),
                                                ("population_urbaine_menages", "menages_urbains", "taille_urbain"),
                                                ("population_rurale_menages", "menages_ruraux", "taille_rural")]:
                if ligne_c[menages] and abs(ligne_c[population] / ligne_c[menages] - ligne_c[taille]) > 0.051:
                    ecarts.append(taille)
            if ecarts:
                erreurs.append(f"{nom} : tableau 16 différent ({', '.join(ecarts)})")
    return erreurs


def _tailles_par_sexe(districts_pdf, blocs, tailles):
    """Taille moyenne des ménages selon le sexe du chef (tableau 14), alignée sur les districts
    du tableau 8 ; contrôle par la population et le nombre de ménages."""
    if len(tailles) != len(districts_pdf):
        return [f"{len(tailles)} districts au tableau 14 contre {len(districts_pdf)} au tableau 8"]
    erreurs = []
    for d, bloc, t in zip(districts_pdf, blocs, tailles):
        if t["population_menages"] != d["population"] or t["menages"] != bloc["total"]["menages"]:
            erreurs.append(f"{d['nom']} : tableau 14 différent des tableaux 8 et 13 (« {t['nom']} »)")
        d["taille_menage_chef_homme"] = t["taille_chef_homme"]
        d["taille_menage_chef_femme"] = t["taille_chef_femme"]
    return erreurs


def _national_rgph(reg, tailles):
    """Valeurs nationales du recensement (somme des régions), pour les comparaisons."""
    if tailles is None:
        raise ValueError("RGPH-3 : ligne MADAGASCAR du tableau 14 introuvable")
    n = pd.DataFrame([reg[COLONNES_RGPH].sum()])
    n["superficie_km2"] = reg["superficie_km2"].sum()
    if int(n.loc[0, "menages"]) != tailles["menages"]:
        raise ValueError("RGPH-3 : ménages nationaux différents entre les tableaux 13 et 14")
    _menages(n)
    n = n.iloc[0]
    return {"population": int(n["population"]), "part_urbaine_pct": 100 * n["urbain"] / n["population"],
            "rapport_masculinite": 100 * n["hommes"] / n["femmes"], "densite": n["population"] / n["superficie_km2"],
            "menages": int(n["menages"]), "taille_menage": n["taille_menage"], "chef_femme_pct": n["chef_femme_pct"],
            "taille_menage_urbain": n["taille_menage_urbain"], "taille_menage_rural": n["taille_menage_rural"],
            "taille_menage_chef_homme": tailles["taille_chef_homme"],
            "taille_menage_chef_femme": tailles["taille_chef_femme"]}


def _sans_district(nom, district):
    """Retire le nom du district placé devant celui de la commune (« Soavinandriana Amparaky »)."""
    mots = nom.split()
    for k in range(len(mots) - 1, 0, -1):
        if cle_nom(" ".join(mots[:k])) == cle_nom(district):
            return " ".join(mots[k:])
    return nom


def _noms_possibles(commune, district):
    """Noms à essayer, dans l'ordre, pour relier une commune du recensement à HDX.

    Quand le tableau 10 donne un morceau du nom du district, c'est sans doute une erreur
    d'impression : le nom du tableau 13 passe alors en premier.
    """
    nom_10 = commune["nom"]
    nom_13 = _sans_district(commune.get("nom_tableau_13", nom_10), district)
    if cle_nom(nom_13) == cle_nom(nom_10):
        return [nom_10]
    return [nom_13, nom_10] if cle_nom(nom_10) in cle_nom(district) else [nom_10, nom_13]


def _completer(df, superficies, estimations):
    """Ajoute les indicateurs dérivés et l'écart avec l'estimation INSTAT/BNGRC de HDX."""
    df["part_urbaine_pct"] = 100 * df["urbain"] / df["population"]
    df["rapport_masculinite"] = 100 * df["hommes"] / df["femmes"]
    df["femmes_pct"] = 100 * df["femmes"] / df["population"]
    _menages(df)
    df["superficie_km2"] = df["cle"].map(superficies)
    df["densite"] = df["population"] / df["superficie_km2"]
    df["estimation_hdx_2018"] = df["cle"].map(estimations)
    df["ecart_estimation_pct"] = 100 * (df["estimation_hdx_2018"] / df["population"] - 1)
    return df


def recensement(niveaux):
    """Résultats du RGPH-3 (2018) par région, district et commune.

    Les districts du recensement sont reliés aux districts HDX par leur nom ; Antananarivo
    Renivohitra est détaillé par arrondissement (ce sont des districts dans HDX). Les communes
    sont reliées par leur nom à l'intérieur de chaque district, d'abord exactement puis de façon
    approchée ; les communes créées depuis le découpage HDX restent sans correspondance.
    """
    extrait = rgph3.extraire(brut("rgph3"))
    erreurs = []
    if extrait["national"] is None or extrait["national"]["population"] != RGPH3_TOTAL:
        erreurs.append(f"total national lu : {extrait['national']}")
    districts_pdf, blocs = extrait["districts"], extrait["blocs_communes"]
    if [d["population"] for d in districts_pdf] != [b["total"]["population"] for b in blocs]:
        erreurs.append("les districts des tableaux 8 et 10 ne concordent pas")
    for d, b in zip(districts_pdf, blocs):
        lignes = [b["total"], *b["communes"]]
        if sum(c["population"] for c in b["communes"]) != b["total"]["population"]:
            erreurs.append(f"communes de {d['nom']} : somme différente du total du district")
        if any(c["urbain"] + c["rural"] != c["population"] for c in lignes):
            erreurs.append(f"{d['nom']} : urbain + rural différent du total")
    erreurs += _ajouter_menages(blocs, extrait["blocs_menages"], districts_pdf)
    if extrait["menages_national"] is None:
        erreurs.append("total national des ménages introuvable (tableau 13)")
    elif sum(b["total"]["menages"] for b in extrait["blocs_menages"]) != extrait["menages_national"]["menages"]:
        erreurs.append("ménages : la somme des districts diffère du total national")
    erreurs += _controler_tableau_16(blocs, extrait["blocs_controle"], districts_pdf)
    erreurs += _tailles_par_sexe(districts_pdf, blocs, extrait["tailles_districts"])
    if erreurs:
        raise ValueError("RGPH-3 : extraction incohérente :\n- " + "\n- ".join(erreurs))

    unites_d = niveaux["districts"]["unites"].set_index("cle")
    unites_c = niveaux["communes"]["unites"]
    lignes_d, lignes_c = [], []
    for d, bloc in zip(districts_pdf, blocs):
        cle_d = cle_nom(d["nom"])
        arrondissements = cle_d == "antananarivorenivohitra"
        if not arrondissements:
            if cle_d not in unites_d.index:
                raise ValueError(f"RGPH-3 : district sans correspondance « {d['nom']} »")
            lignes_d.append({"cle": cle_d, **_chiffres(bloc["total"]), "densite_officielle": d["densite"],
                             "taille_menage_chef_homme": d["taille_menage_chef_homme"],
                             "taille_menage_chef_femme": d["taille_menage_chef_femme"]})
        # Communes de HDX disponibles dans ce district, par nom normalisé
        candidats = {}
        for cle in unites_c["cle"]:
            dist, com = cle.split("/", 1)
            if dist == cle_d or (arrondissements and dist == com and "arrondissement" in com):
                candidats[com] = cle
        restants = dict(candidats)
        for c in bloc["communes"]:
            if arrondissements:
                lignes_d.append({"cle": cle_nom(c["nom"]), **_chiffres(c), "densite_officielle": float("nan")})
            noms = _noms_possibles(c, d["nom"])
            nom, cle_hdx, correspondance = noms[0], None, "aucune"
            for essai in noms:
                if cle_nom(essai) in restants:
                    nom, cle_hdx, correspondance = essai, restants.pop(cle_nom(essai)), "exacte"
                    break
            else:
                for essai in noms:
                    proche = difflib.get_close_matches(cle_nom(essai), list(restants), n=1, cutoff=0.8)
                    if proche:
                        nom, cle_hdx, correspondance = essai, restants.pop(proche[0]), "approchée"
                        break
            lignes_c.append({"nom": nom, "district_rgph": d["nom"], **_chiffres(c),
                             "cle_hdx": cle_hdx, "correspondance": correspondance})
        for ligne in lignes_c[len(lignes_c) - len(bloc["communes"]):]:
            ligne["decoupage_identique"] = not restants and all(
                l["correspondance"] != "aucune" for l in lignes_c[len(lignes_c) - len(bloc["communes"]):])

    # Districts : rattachement aux codes HDX et contrôle de couverture
    dist = pd.DataFrame(lignes_d)
    if set(dist["cle"]) != set(unites_d.index) or dist["cle"].duplicated().any():
        raise ValueError("RGPH-3 : les districts ne couvrent pas exactement les 119 districts HDX")
    dist = unites_d[["pcode", "nom", "region_pcode", "region"]].join(dist.set_index("cle")).reset_index()
    dist = _completer(dist, unites_d["superficie_km2"], unites_d["population"])

    # Régions : somme des districts, comparée aux totaux régionaux publiés
    unites_r = niveaux["regions"]["unites"].set_index("pcode")
    reg = dist.groupby("region_pcode")[COLONNES_RGPH].sum()
    if sorted(reg["population"]) != sorted(r["population"] for r in extrait["regions"]):
        raise ValueError("RGPH-3 : les totaux régionaux recalculés diffèrent des totaux publiés")
    densites_publiees = {r["population"]: r["densite"] for r in extrait["regions"]}
    reg = unites_r[["cle", "nom"]].join(reg).reset_index()
    reg["densite_officielle"] = reg["population"].map(densites_publiees)
    # Taille des ménages selon le sexe du chef : lignes « Total Région » du tableau 14,
    # reconnues par leur nombre de ménages
    tailles = {r["menages"]: r for r in extrait["tailles_regions"]}
    if set(tailles) != set(reg["menages"]):
        raise ValueError("RGPH-3 : les régions du tableau 14 ne correspondent pas aux ménages recalculés")
    for sexe in ("homme", "femme"):
        reg[f"taille_menage_chef_{sexe}"] = reg["menages"].map(lambda m: tailles[m][f"taille_chef_{sexe}"])
    reg = _completer(reg, niveaux["regions"]["unites"].set_index("cle")["superficie_km2"],
                     niveaux["regions"]["unites"].set_index("cle")["population"])
    reg.attrs["national"] = _national_rgph(reg, extrait["tailles_national"])

    # Communes : codes HDX quand la correspondance existe
    com = pd.DataFrame(lignes_c)
    infos_hdx = unites_c.set_index("cle")[["pcode", "district_pcode", "region_pcode", "region"]]
    com = com.join(infos_hdx.rename(columns={"pcode": "pcode_hdx"}), on="cle_hdx")
    district_par_nom = dist.set_index("cle")[["pcode", "region_pcode", "region"]]
    for i, ligne in com[com["district_pcode"].isna()].iterrows():
        cle_d = cle_nom(ligne["district_rgph"])
        if cle_d == "antananarivorenivohitra":
            cle_d = cle_nom(ligne["nom"])
        if cle_d in district_par_nom.index:
            com.loc[i, ["district_pcode", "region_pcode", "region"]] = district_par_nom.loc[cle_d].values
    com["part_urbaine_pct"] = 100 * com["urbain"] / com["population"]
    _menages(com)
    com = com[["nom", "district_rgph", "district_pcode", "region_pcode", "region", *COLONNES_RGPH,
               "part_urbaine_pct", "taille_menage", "taille_menage_urbain", "taille_menage_rural", "chef_femme_pct",
               "pcode_hdx", "cle_hdx", "correspondance",
               "decoupage_identique"]]
    if com["population"].sum() != RGPH3_TOTAL:
        raise ValueError("RGPH-3 : la somme des communes diffère du total national")
    return {"regions": reg, "districts": dist, "communes": com}


def _repartir(total, poids):
    """Répartit un entier au prorata des poids, en arrondissant sans perdre d'habitant
    (méthode du plus fort reste)."""
    parts = np.asarray(poids, dtype="float64")
    parts = parts / parts.sum() * total
    entiers = np.floor(parts).astype(int)
    reste = int(total - entiers.sum())
    if reste:
        entiers[np.argsort(-(parts - entiers), kind="stable")[:reste]] += 1
    return entiers


def fokontany_cales(niveaux, rgph):
    """Estimation de la population 2018 des fokontany, calée sur le recensement.

    Le RGPH-3 n'est pas publié par fokontany. Pour chaque commune reliée au recensement,
    sa population recensée est répartie entre ses fokontany au prorata de leur poids dans
    l'estimation HDX (répartition de 2009). Les totaux communaux sont exacts ; la
    répartition interne reste une estimation.
    """
    fk = niveaux["fokontany"]["unites"].copy()
    fk["cle_commune"] = fk["cle"].str.rsplit("/", n=1).str[0]
    communes = rgph["communes"].dropna(subset=["cle_hdx"]).set_index("cle_hdx")
    fk["population_calee"] = np.nan
    for cle_commune, groupe in fk.groupby("cle_commune"):
        if cle_commune not in communes.index:
            continue
        total = int(communes.loc[cle_commune, "population"])
        fk.loc[groupe.index, "population_calee"] = _repartir(total, groupe["population"].clip(lower=1))
    fk = fk.join(communes[["population", "correspondance", "decoupage_identique"]]
                 .rename(columns={"population": "population_commune_rgph3",
                                  "correspondance": "correspondance_commune"}), on="cle_commune")

    # Contrôle : chaque commune calée retrouve exactement sa population recensée
    calees = fk.dropna(subset=["population_calee"])
    sommes = calees.groupby("cle_commune")["population_calee"].sum()
    attendu = communes.loc[sommes.index, "population"]
    if not (sommes.astype(int) == attendu.astype(int)).all():
        raise ValueError("Fokontany calés : une commune ne retrouve pas sa population recensée")

    fk["part_commune_pct"] = 100 * fk["population_calee"] / fk["population_commune_rgph3"]
    fk["densite_calee"] = fk["population_calee"] / fk["superficie_km2"]
    fk = fk.rename(columns={"population": "estimation_hdx_2018"})
    return fk[["cle", "pcode", "nom", "commune_pcode", "commune", "district_pcode", "district",
               "region_pcode", "region", "estimation_hdx_2018", "population_calee", "part_commune_pct",
               "superficie_km2", "densite_calee", "population_commune_rgph3", "correspondance_commune",
               "decoupage_identique"]]


def worldpop_fokontany(niveaux, estimations_1km, bande=2048):
    """Somme des pixels WorldPop à 100 m par fokontany et par année.

    Chaque pixel est affecté au fokontany dont le contour contient son centre. Les grilles
    (16 388 × 8 757 pixels) sont lues par bandes de lignes pour limiter la mémoire.
    """
    unites = niveaux["fokontany"]["unites"]
    contours = niveaux["fokontany"]["contours"]
    cles = list(unites["cle"])
    motif = brut("worldpop_100m", annee="*")
    fichiers = sorted(motif.parent.glob(motif.name))
    if not fichiers:
        raise ValueError("WorldPop 100 m : aucune grille téléchargée")
    zones, colonnes, erreurs = None, {}, []
    for fichier in fichiers:
        annee = int(fichier.stem.split("_")[1])
        with rasterio.open(fichier) as src:
            if zones is None:  # toutes les années partagent la même grille
                zones = rasterize(((contours[c], i + 1) for i, c in enumerate(cles)), out_shape=src.shape,
                                  transform=src.transform, fill=0, dtype="uint16")
            sommes = np.zeros(len(cles) + 1)
            for ligne in range(0, src.height, bande):
                hauteur = min(bande, src.height - ligne)
                grille = src.read(1, window=Window(0, ligne, src.width, hauteur), masked=True).filled(0)
                sommes += np.bincount(zones[ligne:ligne + hauteur].ravel(),
                                      weights=grille.astype("float64").ravel(), minlength=len(cles) + 1)
        # Contrôles : même total national que la grille à 1 km, presque tout dans un fokontany
        total_1km = estimations_1km.loc[estimations_1km["annee"] == annee, "population"].sum()
        hors = sommes[0] / sommes.sum()
        if hors > 0.01:
            erreurs.append(f"{annee} : {hors:.1%} de la population hors des fokontany")
        if total_1km and abs(sommes[1:].sum() / total_1km - 1) > 0.02:
            erreurs.append(f"{annee} : total {sommes[1:].sum():,.0f} contre {total_1km:,.0f} à 1 km")
        colonnes[f"wp100_{annee}"] = np.round(sommes[1:]).astype(int)
    if erreurs:
        raise ValueError("WorldPop 100 m :\n- " + "\n- ".join(erreurs))
    resultat = unites[["cle", "pcode", "nom", "commune_pcode", "commune", "district_pcode", "district",
                       "region_pcode", "region", "superficie_km2"]].reset_index(drop=True)
    return pd.concat([resultat, pd.DataFrame(colonnes)], axis=1)


def _nom_enquete(source, annee):
    """Nom court de l'enquête d'origine d'une observation de l'OIT."""
    if source.startswith("HS - Enquête périodique auprès des Ménages"):
        return f"EPM {annee}"
    if source.startswith("LFS - Enquête Nationale sur l'Emploi et le Secteur Informel"):
        return {2012: "ENEMPSI 2012", 2015: "ENESI 2015"}.get(annee, f"Enquête emploi {annee}")
    if source.startswith("LFS - Enquête sur la Population Active"):
        return f"Enquête emploi des grandes villes {annee}"
    return source.split(" - ", 1)[-1] + f" {annee}"


def emploi():
    """Indicateurs d'emploi de l'OIT : un fichier détaillé et une synthèse par enquête.

    Seules les observations issues d'enquêtes auprès des ménages (EPM) ou sur la population
    active (ENEMPSI, ENESI) sont gardées ; les estimations officielles et les recensements
    publiés par l'OIT sont écartés.
    """
    lignes = []
    for indicateur, (_, colonne, libelle) in INDICATEURS_EMPLOI.items():
        df = pd.read_csv(brut("emploi", indicateur=indicateur))
        df = df[df["SOURCE"].str.startswith(("HS -", "LFS -"))].copy()
        ventilation = next((c for c in ("AGE", "ECO", "STE") if c in df), None)
        multiplicateur = 10.0 ** df["UNIT_MULT"].fillna(0)
        lignes.append(pd.DataFrame({
            "indicateur": colonne, "libelle": libelle,
            "annee": df["TIME_PERIOD"].astype(int),
            "enquete": [_nom_enquete(s, a) for s, a in zip(df["SOURCE"], df["TIME_PERIOD"].astype(int))],
            "sexe": df["SEX"].map({"SEX_T": "ensemble", "SEX_M": "hommes", "SEX_F": "femmes"}).fillna(df["SEX"]),
            "ventilation": df[ventilation] if ventilation else "",
            "valeur": df["OBS_VALUE"] * (multiplicateur / 1000 if colonne.endswith("_milliers") else 1),
            "note": (df["NOTE_SOURCE"].fillna("") + " | " + df["NOTE_INDICATOR"].fillna("")).str.strip(" |"),
            "source_oit": df["SOURCE"],
        }))
    detail = pd.concat(lignes, ignore_index=True).sort_values(["indicateur", "annee", "sexe", "ventilation"])
    if detail.empty:
        raise ValueError("Emploi : aucune observation issue d'une enquête")

    # Synthèse : ensemble des deux sexes, 15 ans et plus, une ligne par enquête nationale
    tot = detail[(detail["sexe"] == "ensemble")
                 & detail["ventilation"].isin(["", "AGE_YTHADULT_YGE15", "ECO_AGGREGATE_TOTAL", "STE_AGGREGATE_TOTAL",
                                               "ECO_AGGREGATE_AGR", "STE_AGGREGATE_EES"])]
    tot = tot[~tot["enquete"].str.startswith("Enquête emploi des grandes villes")]
    synthese = {}
    for (annee, enquete), g in tot.groupby(["annee", "enquete"]):
        v = {(r["indicateur"], r["ventilation"]): r["valeur"] for _, r in g.iterrows()}
        emploi_total = v.get(("emploi_par_secteur_milliers", "ECO_AGGREGATE_TOTAL"))
        statut_total = v.get(("emploi_par_statut_milliers", "STE_AGGREGATE_TOTAL"))
        synthese[(annee, enquete)] = {
            # L'OIT signale une rupture de série quand la méthode change (ex. normes de 2013 sur le travail)
            "rupture_de_serie": bool(g["note"].str.contains("Break in series").any()),
            "taux_activite_pct": v.get(("taux_activite_pct", "AGE_YTHADULT_YGE15")),
            "taux_emploi_pct": v.get(("taux_emploi_pct", "AGE_YTHADULT_YGE15")),
            "taux_chomage_pct": v.get(("taux_chomage_pct", "AGE_YTHADULT_YGE15")),
            "emploi_informel_pct": v.get(("emploi_informel_pct", "")),
            "jeunes_neet_pct": v.get(("jeunes_neet_pct", "")),
            "emploi_total_milliers": emploi_total,
            "part_agriculture_pct": (100 * v[("emploi_par_secteur_milliers", "ECO_AGGREGATE_AGR")] / emploi_total
                                     if emploi_total and ("emploi_par_secteur_milliers", "ECO_AGGREGATE_AGR") in v else None),
            "part_salaries_pct": (100 * v[("emploi_par_statut_milliers", "STE_AGGREGATE_EES")] / statut_total
                                  if statut_total and ("emploi_par_statut_milliers", "STE_AGGREGATE_EES") in v else None),
        }
    synthese = (pd.DataFrame.from_dict(synthese, orient="index").rename_axis(["annee", "enquete"])
                .reset_index().sort_values("annee"))
    if synthese["taux_activite_pct"].isna().all():
        raise ValueError("Emploi : la synthèse ne contient aucun taux d'activité")
    return detail, synthese


def pauvrete():
    """Pauvreté et inégalités par enquête (Banque mondiale, PIP), une ligne par année d'enquête."""
    with open(brut("pauvrete"), encoding="utf-8") as f:
        brut_pip = pd.DataFrame(json.load(f))
    brut_pip = brut_pip[brut_pip["reporting_level"] == "national"]
    taux = (brut_pip.pivot_table(index="reporting_year", columns="poverty_line", values="headcount") * 100)
    taux.columns = [f"pauvrete_{seuil:.2f}_dollars_pct".replace(".", "_") for seuil in taux.columns]
    ecart = (brut_pip.pivot_table(index="reporting_year", columns="poverty_line", values="poverty_gap") * 100)
    ecart.columns = [f"ecart_pauvrete_{seuil:.2f}_dollars_pct".replace(".", "_") for seuil in ecart.columns]
    infos = (brut_pip.drop_duplicates("reporting_year").set_index("reporting_year")
             [["survey_acronym", "welfare_type", "survey_coverage", "gini", "mean"]]
             .rename(columns={"survey_acronym": "enquete", "welfare_type": "mesure_du_bien_etre",
                              "survey_coverage": "couverture", "mean": "consommation_moyenne_dollars_jour"}))
    table = infos.join(taux).join(ecart).reset_index().rename(columns={"reporting_year": "annee"})
    table["annee"] = table["annee"].astype(int)
    if table.empty:
        raise ValueError("Pauvreté : aucune estimation nationale")
    return table.sort_values("annee")


def etablissements_sante(niveaux, distance_max_km=10):
    """Établissements de santé publics, chacun rattaché à la commune de la carte qui le contient.

    Les contours simplifiés coupent parfois le littoral : un établissement situé juste à côté est
    rattaché à la commune la plus proche s'il en est à moins de `distance_max_km`.
    """
    brute = pd.read_excel(brut("sante_etablissements"))
    brute = brute[brute["Country"] == "Madagascar"]
    inconnus = set(brute["Facility_t"]) - set(TYPES_SANTE)
    if inconnus:
        raise ValueError(f"Établissements de santé : types inconnus {inconnus}")
    table = pd.DataFrame({
        "nom": brute["Facility_n"].str.strip(), "type": brute["Facility_t"].map(TYPES_SANTE),
        "latitude": brute["Lat"].round(5), "longitude": brute["Long"].round(5),
        "region_source": brute["Admin1"], "source_coordonnees": brute["LL_source"],
    }).reset_index(drop=True)

    communes = niveaux["communes"]["unites"].set_index("cle")
    contours = [(cle, geo, boite(geo)) for cle, geo in niveaux["communes"]["contours"].items()]
    sommets = [(cle, x, y) for cle, geo, _ in contours for a in anneaux(geo) for x, y, *_ in a[::4]]

    def rattacher(x, y):
        for cle, geo, b in contours:
            if b[0] <= x <= b[2] and b[1] <= y <= b[3] and contient(geo, (x, y)):
                return cle, 0.0
        proches = [(cle, sx, sy) for cle, sx, sy in sommets if abs(sx - x) < 0.2 and abs(sy - y) < 0.2]
        if not proches:
            return None, None
        cle, sx, sy = min(proches, key=lambda s: (s[1] - x) ** 2 + (s[2] - y) ** 2)
        return cle, math.hypot((sx - x) * 111.32 * math.cos(math.radians(y)), (sy - y) * 110.57)

    rattachements = [rattacher(x, y) for x, y in zip(table["longitude"], table["latitude"])]
    table["cle"] = [c if d is not None and d <= distance_max_km else None for c, d in rattachements]
    table["distance_commune_km"] = [round(d, 1) if d else 0.0 for _, d in rattachements]
    hors = table["cle"].isna()
    if hors.mean() > 0.01:
        raise ValueError(f"Établissements de santé : {hors.sum()} hors des communes de la carte")
    table = table[~hors].copy()
    infos = communes.loc[table["cle"], ["pcode", "nom", "district_pcode", "district", "region_pcode", "region"]]
    table[["commune_pcode", "commune", "district_pcode", "district", "region_pcode", "region"]] = infos.values
    # Contrôle : la région déduite de la position doit être celle que donne la source
    meme_region = float((table["region_source"].map(cle_nom) == table["region"].map(cle_nom)).mean())
    if meme_region < 0.97:
        raise ValueError(f"Établissements de santé : région différente de la source pour {1 - meme_region:.1%}")
    table.attrs |= {"hors_carte": int(hors.sum()), "pres_du_contour": int((table["distance_commune_km"] > 0).sum()),
                    "meme_region": meme_region}
    return table.sort_values(["region", "district", "commune", "type", "nom"]).reset_index(drop=True)


def tout_nettoyer():
    """Renvoie un dictionnaire avec :
    - series, pyramide : indicateurs nationaux (Banque mondiale) ;
    - projections : projections ONU jusqu'en 2050 ;
    - niveaux : par découpage, {population (format long), unites (2018), contours} ;
    - dhs : indicateurs régionaux de la dernière enquête DHS ;
    - worldpop : estimations annuelles 2015-2030 par région, district et commune ;
    - rgph3 : résultats du recensement de 2018 par région, district et commune ;
    - fokontany_cales : population 2018 des fokontany estimée en calant sur le recensement ;
    - worldpop_100m : estimations WorldPop à 100 m par fokontany, 2015-2030 ;
    - emploi, emploi_detail : indicateurs d'emploi de l'OIT par enquête (ENEMPSI, ENESI, EPM) ;
    - pauvrete : pauvreté et inégalités par enquête EPM (Banque mondiale) ;
    - sante : établissements de santé publics géolocalisés, rattachés aux communes.
    """
    DOSSIER_TRAITE.mkdir(parents=True, exist_ok=True)
    series, pyramide = indicateurs_nationaux()
    proj = projections()
    niveaux = {niveau: {"population": population(niveau)} for niveau in NIVEAUX}
    controles(series, pyramide, niveaux)

    for niveau, donnees in niveaux.items():
        parent = PARENTS.get(niveau)
        df = donnees["population"]
        donnees["contours"] = rattacher_contours(
            niveau, set(df["cle"]),
            niveaux[parent]["contours"] if niveau in ("communes", "fokontany") else None,
            set(df.loc[df["pcode"].str.contains("|", regex=False), "cle"]))
        donnees["unites"] = table_unites(df, donnees["contours"])
    print("  Rattachement des contours : OK")

    table_dhs = dhs(niveaux["regions"]["population"])
    print(f"  DHS : {table_dhs.attrs['enquete']}, {len(table_dhs)} régions")
    estimations = worldpop(niveaux, proj)
    print(f"  WorldPop : {estimations['communes']['annee'].min()}-"
          f"{estimations['communes']['annee'].max()}, contrôle du total national OK")
    wp100 = worldpop_fokontany(niveaux, estimations["communes"])
    annees_100m = [c for c in wp100.columns if c.startswith("wp100_")]
    print(f"  WorldPop 100 m : {len(annees_100m)} années pour {len(wp100)} fokontany, contrôles OK")
    emploi_detail, emploi_synthese = emploi()
    table_pauvrete = pauvrete()
    print(f"  Emploi (OIT) : {len(emploi_detail)} observations, enquêtes "
          + ", ".join(emploi_synthese["enquete"]))
    print(f"  Pauvreté (Banque mondiale) : enquêtes {', '.join(f'{e} {a}' for e, a in zip(table_pauvrete['enquete'], table_pauvrete['annee']))}")
    rgph = recensement(niveaux)
    reliees = rgph["communes"]["correspondance"].value_counts()
    print(f"  RGPH-3 : {len(rgph['districts'])} districts, {len(rgph['communes'])} communes "
          f"({reliees.get('exacte', 0)} reliées exactement, {reliees.get('approchée', 0)} approximativement, "
          f"{reliees.get('aucune', 0)} sans correspondance)")
    cales = fokontany_cales(niveaux, rgph)
    n_cales = cales["population_calee"].notna().sum()
    print(f"  Fokontany calés sur le recensement : {n_cales} sur {len(cales)} "
          f"({cales['population_calee'].sum():,.0f} habitants)".replace(",", " "))

    sante = etablissements_sante(niveaux)
    print(f"  Établissements de santé publics : {len(sante)} ("
          + ", ".join(f"{t} : {n}" for t, n in sante["type"].value_counts().items())
          + f"), {sante.attrs['pres_du_contour']} rattachés à la commune la plus proche, "
          f"{sante.attrs['hors_carte']} hors carte ; région identique à la source : {sante.attrs['meme_region']:.0%}")

    series.to_csv(traite("indicateurs"))
    sante.drop(columns="cle").to_csv(traite("sante_etablissements"), index=False)
    pyramide.to_csv(traite("pyramide"), index=False)
    proj.to_csv(traite("projections"))
    table_dhs.drop(columns="cle").to_csv(traite("dhs"), index=False)
    for niveau, table in rgph.items():
        table.drop(columns=[c for c in ("cle", "cle_hdx") if c in table]).round(2).to_csv(
            traite("rgph3", niveau=niveau), index=False)
    sortie = cales.drop(columns="cle").copy()
    sortie["population_calee"] = sortie["population_calee"].astype("Int64")
    sortie["population_commune_rgph3"] = sortie["population_commune_rgph3"].astype("Int64")
    sortie.round(2).to_csv(traite("fokontany_cales"), index=False)
    wp100.drop(columns="cle").round(2).to_csv(traite("worldpop_100m"), index=False)
    emploi_detail.round(3).to_csv(traite("emploi"), index=False)
    emploi_synthese.round(2).to_csv(traite("emploi_synthese"), index=False)
    table_pauvrete.round(3).to_csv(traite("pauvrete"), index=False)
    for niveau, donnees in niveaux.items():
        donnees["population"].drop(columns="cle").to_csv(
            traite("series", niveau=niveau), index=False)
        unites = donnees["unites"]
        unites.drop(columns="cle").round(2).to_csv(traite("unites", niveau=niveau), index=False)
        if niveau in estimations:
            large = (estimations[niveau].pivot(index="cle", columns="annee", values="population")
                     .round().astype(int).add_prefix("wp_"))
            unites[["cle", "pcode", "nom"]].join(large, on="cle").drop(columns="cle").to_csv(
                traite("worldpop", niveau=niveau), index=False)
    print(f"  -> {len(series)} années d'indicateurs, "
          + ", ".join(f"{len(d['unites'])} {n}" for n, d in niveaux.items()))
    return {"series": series, "pyramide": pyramide, "projections": proj, "niveaux": niveaux,
            "dhs": table_dhs, "worldpop": estimations, "rgph3": rgph, "fokontany_cales": cales,
            "worldpop_100m": wp100, "emploi": emploi_synthese, "emploi_detail": emploi_detail,
            "pauvrete": table_pauvrete, "sante": sante}
