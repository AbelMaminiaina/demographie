"""Étape 2 : mise en forme et harmonisation des données brutes."""
import json
import re
import unicodedata

import pandas as pd

from config import DOSSIER_BRUT, DOSSIER_TRAITE, INDICATEURS, NIVEAUX

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
    if code != "ADM1":
        identifiants |= {"ADM1_PCODE": "region_pcode", "ADM1_EN": "region"}
    long = df.melt(id_vars=list(identifiants),
                   value_vars=[c for c in df.columns if c.startswith("T_TL_")],
                   var_name="annee", value_name="population")
    long["annee"] = long["annee"].str[-4:].astype(int)
    long = long.rename(columns=identifiants)
    long["cle"] = long["nom"].map(cle_nom)
    return long.sort_values(["annee", "pcode"]).reset_index(drop=True)


def controles(series, pyramide, regions, districts):
    """Contrôles de cohérence simples ; lève une erreur si un contrôle échoue."""
    erreurs = []
    for niveau, df in (("regions", regions), ("districts", districts)):
        n, attendus = df["pcode"].nunique(), NIVEAUX[niveau]["attendus"]
        if n != attendus:
            erreurs.append(f"{n} {niveau} trouvés au lieu de {attendus}")
        if df["cle"].nunique() != n:
            erreurs.append(f"noms de {niveau} en double après normalisation")
        if df["population"].isna().any() or (df["population"] <= 0).any():
            erreurs.append(f"population manquante ou nulle ({niveau})")

    somme = districts.groupby(["annee", "region_pcode"])["population"].sum()
    reference = regions.set_index(["annee", "pcode"])["population"]
    ecart = (somme / reference.reindex(somme.index) - 1).abs()
    if ecart.isna().any() or (ecart > 0.005).any():
        erreurs.append(f"somme des districts ≠ population régionale (écart max {ecart.max():.2%})")

    annee = pyramide["annee"].max()
    total_pyr = pyramide.loc[pyramide["annee"] == annee, "effectif"].sum()
    total = series.loc[annee, "population"]
    if abs(total_pyr - total) / total > 0.01:
        erreurs.append(f"pyramide {annee} ({total_pyr:,.0f}) ≠ population totale ({total:,.0f})")
    if erreurs:
        raise ValueError("Contrôles qualité échoués :\n- " + "\n- ".join(erreurs))
    print("  Contrôles qualité : OK")


def tout_nettoyer():
    DOSSIER_TRAITE.mkdir(parents=True, exist_ok=True)
    series, pyramide = indicateurs_nationaux()
    regions = population("regions")
    districts = population("districts")
    controles(series, pyramide, regions, districts)
    series.to_csv(DOSSIER_TRAITE / "indicateurs_nationaux.csv")
    pyramide.to_csv(DOSSIER_TRAITE / "pyramide_ages.csv", index=False)
    regions.drop(columns="cle").to_csv(DOSSIER_TRAITE / "population_regions.csv", index=False)
    districts.drop(columns="cle").to_csv(DOSSIER_TRAITE / "population_districts.csv", index=False)
    print(f"  -> {len(series)} années d'indicateurs, {regions['pcode'].nunique()} régions, "
          f"{districts['pcode'].nunique()} districts")
    return series, pyramide, regions, districts
