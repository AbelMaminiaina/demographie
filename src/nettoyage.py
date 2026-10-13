"""Étape 2 : mise en forme et harmonisation des données brutes."""
import json
import re
import unicodedata

import pandas as pd

from config import DOSSIER_BRUT, DOSSIER_TRAITE, INDICATEURS, NIVEAUX, PARENTS
from geometrie import boite, contient, point_interieur, superficie_km2

# Variantes d'orthographe connues -> forme normalisée de référence
ALIAS_NOMS = {
    "matsiatraambony": "hautematsiatra",
}


def cle_nom(nom):
    """Clé de jointure robuste : sans accents, apostrophes, tirets ni espaces.

    Les chiffres sont conservés pour distinguer les arrondissements (« 2e Arrondissement »).
    """
    nom = unicodedata.normalize("NFKD", str(nom)).encode("ascii", "ignore").decode()
    cle = re.sub(r"[^a-z0-9]", "", nom.lower())
    return ALIAS_NOMS.get(cle, cle)


def indicateurs_nationaux():
    with open(DOSSIER_BRUT / "banque_mondiale.json", encoding="utf-8") as f:
        brut = pd.DataFrame(json.load(f))
    df = pd.DataFrame({
        "code": brut["indicator"].str["id"],
        "annee": brut["date"].astype(int),
        "valeur": brut["value"],
    }).dropna()

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
    df = pd.read_csv(DOSSIER_BRUT / f"hdx_population_{code.lower()}.csv", encoding="utf-8-sig")
    # La dernière colonne « T_TL » correspond à 2018 (année du RGPH-3).
    df = df.rename(columns={"T_TL": "T_TL_2018"})
    identifiants = {f"{code}_PCODE": "pcode", f"{code}_EN": "nom"}
    if code in ("ADM2", "ADM3"):
        identifiants |= {"ADM1_PCODE": "region_pcode", "ADM1_EN": "region"}
    if code == "ADM3":
        identifiants |= {"ADM2_PCODE": "district_pcode", "ADM2_EN": "district"}
    long = df.melt(id_vars=list(identifiants),
                   value_vars=[c for c in df.columns if c.startswith("T_TL_")],
                   var_name="annee", value_name="population")
    long["annee"] = long["annee"].str[-4:].astype(int)
    long = long.rename(columns=identifiants)
    # Clé de jointure avec les contours ; les noms de communes se répètent d'un district à l'autre.
    long["cle"] = long["nom"].map(cle_nom)
    if niveau == "communes":
        long["cle"] = long["district"].map(cle_nom) + "/" + long["cle"]
    return long.sort_values(["annee", "pcode"]).reset_index(drop=True)


def _lire_contours(niveau):
    with open(DOSSIER_BRUT / f"{niveau}.geojson", encoding="utf-8") as f:
        return json.load(f)["features"]


def rattacher_contours(niveau, cles_connues, contours_districts=None):
    """Associe chaque contour geoBoundaries à une clé de la table de population.

    Les contours de communes n'indiquent pas leur district : on le retrouve en cherchant
    le district qui contient un point intérieur de la commune.
    """
    rattaches, erreurs = {}, []
    if niveau == "communes":
        districts = [(cle, geo, boite(geo)) for cle, geo in contours_districts.items()]
    for feat in _lire_contours(niveau):
        cle = cle_nom(feat["properties"]["shapeName"])
        if niveau == "communes":
            x, y = point_interieur(feat["geometry"])
            candidats = [f"{d}/{cle}" for d, geo, b in districts
                         if b[0] <= x <= b[2] and b[1] <= y <= b[3] and contient(geo, (x, y))]
            # Les contours simplifiés se chevauchent parfois aux frontières.
            valides = [c for c in candidats if c in cles_connues]
            cle = valides[0] if valides else (candidats[0] if candidats else f"?/{cle}")
        if cle in rattaches:
            erreurs.append(f"contour en double : {cle}")
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
    """Population, superficie et densité pour l'année la plus récente (2018, RGPH-3)."""
    t = df[df["annee"] == df["annee"].max()].drop(columns="annee").copy()
    t["superficie_km2"] = [superficie_km2(contours[c]) for c in t["cle"]]
    t["densite"] = t["population"] / t["superficie_km2"]
    return t.sort_values("population", ascending=False).reset_index(drop=True)


def controles(series, pyramide, niveaux):
    """Contrôles de cohérence simples ; lève une erreur si un contrôle échoue."""
    erreurs = []
    for niveau, donnees in niveaux.items():
        df = donnees["population"]
        n, attendus = df["pcode"].nunique(), NIVEAUX[niveau]["attendus"]
        if n != attendus:
            erreurs.append(f"{n} {niveau} trouvés au lieu de {attendus}")
        if df["cle"].nunique() != n:
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


def tout_nettoyer():
    """Renvoie les séries nationales, la pyramide et, par niveau administratif,
    un dictionnaire {population (format long), unites (dernière année), contours}."""
    DOSSIER_TRAITE.mkdir(parents=True, exist_ok=True)
    series, pyramide = indicateurs_nationaux()
    niveaux = {niveau: {"population": population(niveau)} for niveau in NIVEAUX}
    controles(series, pyramide, niveaux)

    for niveau, donnees in niveaux.items():
        donnees["contours"] = rattacher_contours(
            niveau, set(donnees["population"]["cle"]),
            niveaux["districts"].get("contours"))
        donnees["unites"] = table_unites(donnees["population"], donnees["contours"])
    print("  Rattachement des contours : OK")

    series.to_csv(DOSSIER_TRAITE / "indicateurs_nationaux.csv")
    pyramide.to_csv(DOSSIER_TRAITE / "pyramide_ages.csv", index=False)
    for niveau, donnees in niveaux.items():
        donnees["population"].drop(columns="cle").to_csv(
            DOSSIER_TRAITE / f"population_{niveau}.csv", index=False)
        donnees["unites"].drop(columns="cle").round(2).to_csv(
            DOSSIER_TRAITE / f"{niveau}.csv", index=False)
    print(f"  -> {len(series)} années d'indicateurs, "
          + ", ".join(f"{d['population']['pcode'].nunique()} {n}" for n, d in niveaux.items()))
    return series, pyramide, niveaux
