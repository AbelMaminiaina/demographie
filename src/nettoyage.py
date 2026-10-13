"""Étape 2 : mise en forme et harmonisation des données brutes."""
import difflib
import json
import re
import unicodedata

import numpy as np
import pandas as pd
import rasterio
from rasterio.features import rasterize
from rasterio.windows import Window

from config import (DOSSIER_TRAITE, INDICATEURS, INDICATEURS_DHS, INDICATEURS_PROJECTIONS,
                    NIVEAUX, PARENTS, RGPH3_TOTAL, brut, traite)
from geometrie import boite, contient, point_interieur, superficie_km2
import rgph3

# Variantes d'orthographe connues -> forme normalisée de référence
ALIAS_NOMS = {
    "matsiatraambony": "hautematsiatra",
    "vakinankarata": "vakinankaratra",      # DHS
    "anamoroniimania": "amoronimania",      # DHS
    "toliarai": "toliaryi",                 # RGPH-3
    "toliaraii": "toliaryii",               # RGPH-3
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


COLONNES_RGPH = ["hommes", "femmes", "population", "urbain", "rural"]


def _chiffres(ligne):
    return {c: ligne[c] for c in COLONNES_RGPH}


def _completer(df, superficies, estimations):
    """Ajoute les indicateurs dérivés et l'écart avec l'estimation INSTAT/BNGRC de HDX."""
    df["part_urbaine_pct"] = 100 * df["urbain"] / df["population"]
    df["rapport_masculinite"] = 100 * df["hommes"] / df["femmes"]
    df["femmes_pct"] = 100 * df["femmes"] / df["population"]
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
            lignes_d.append({"cle": cle_d, **_chiffres(bloc["total"]), "densite_officielle": d["densite"]})
        # Communes de HDX disponibles dans ce district, par nom normalisé
        candidats = {}
        for cle in unites_c["cle"]:
            dist, com = cle.split("/", 1)
            if dist == cle_d or (arrondissements and dist == com and "arrondissement" in com):
                candidats[com] = cle
        restants = dict(candidats)
        for c in bloc["communes"]:
            cle_c, correspondance = cle_nom(c["nom"]), "aucune"
            if arrondissements:
                lignes_d.append({"cle": cle_c, **_chiffres(c), "densite_officielle": float("nan")})
            if cle_c in restants:
                correspondance = "exacte"
            else:
                proche = difflib.get_close_matches(cle_c, list(restants), n=1, cutoff=0.8)
                if proche:
                    cle_c, correspondance = proche[0], "approchée"
            cle_hdx = restants.pop(cle_c) if correspondance != "aucune" else None
            lignes_c.append({"nom": c["nom"], "district_rgph": d["nom"], **_chiffres(c),
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
    reg = _completer(reg, niveaux["regions"]["unites"].set_index("cle")["superficie_km2"],
                     niveaux["regions"]["unites"].set_index("cle")["population"])

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
    com = com[["nom", "district_rgph", "district_pcode", "region_pcode", "region", *COLONNES_RGPH,
               "part_urbaine_pct", "pcode_hdx", "cle_hdx", "correspondance", "decoupage_identique"]]
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


def tout_nettoyer():
    """Renvoie un dictionnaire avec :
    - series, pyramide : indicateurs nationaux (Banque mondiale) ;
    - projections : projections ONU jusqu'en 2050 ;
    - niveaux : par découpage, {population (format long), unites (2018), contours} ;
    - dhs : indicateurs régionaux de la dernière enquête DHS ;
    - worldpop : estimations annuelles 2015-2030 par région, district et commune ;
    - rgph3 : résultats du recensement de 2018 par région, district et commune ;
    - fokontany_cales : population 2018 des fokontany estimée en calant sur le recensement ;
    - worldpop_100m : estimations WorldPop à 100 m par fokontany, 2015-2030.
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
    rgph = recensement(niveaux)
    reliees = rgph["communes"]["correspondance"].value_counts()
    print(f"  RGPH-3 : {len(rgph['districts'])} districts, {len(rgph['communes'])} communes "
          f"({reliees.get('exacte', 0)} reliées exactement, {reliees.get('approchée', 0)} approximativement, "
          f"{reliees.get('aucune', 0)} sans correspondance)")
    cales = fokontany_cales(niveaux, rgph)
    n_cales = cales["population_calee"].notna().sum()
    print(f"  Fokontany calés sur le recensement : {n_cales} sur {len(cales)} "
          f"({cales['population_calee'].sum():,.0f} habitants)".replace(",", " "))

    series.to_csv(traite("indicateurs"))
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
            "worldpop_100m": wp100}
