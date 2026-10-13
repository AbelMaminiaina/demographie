"""Étape 2 : mise en forme et harmonisation des données brutes."""
import json
import re
import unicodedata

import pandas as pd

from config import DOSSIER_BRUT, DOSSIER_TRAITE, INDICATEURS

# Variantes d'orthographe connues -> forme normalisée de référence
ALIAS_REGIONS = {
    "matsiatraambony": "hautematsiatra",
}


def cle_region(nom):
    """Clé de jointure robuste : sans accents, apostrophes, tirets ni espaces."""
    nom = unicodedata.normalize("NFKD", str(nom)).encode("ascii", "ignore").decode()
    cle = re.sub(r"[^a-z]", "", nom.lower())
    return ALIAS_REGIONS.get(cle, cle)


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


def population_regions():
    df = pd.read_csv(DOSSIER_BRUT / "hdx_population_adm1.csv", encoding="utf-8-sig")
    # La dernière colonne « T_TL » correspond à 2018 (année du RGPH-3).
    df = df.rename(columns={"T_TL": "T_TL_2018"})
    long = df.melt(id_vars=["ADM1_PCODE", "ADM1_EN"],
                   value_vars=[c for c in df.columns if c.startswith("T_TL_")],
                   var_name="annee", value_name="population")
    long["annee"] = long["annee"].str[-4:].astype(int)
    long = long.rename(columns={"ADM1_PCODE": "pcode", "ADM1_EN": "region"})
    long["cle"] = long["region"].map(cle_region)
    return long.sort_values(["annee", "region"])


def controles(series, pyramide, regions):
    """Contrôles de cohérence simples ; lève une erreur si un contrôle échoue."""
    erreurs = []
    if regions["region"].nunique() != 22:
        erreurs.append(f"{regions['region'].nunique()} régions trouvées au lieu de 22")
    if regions["population"].isna().any() or (regions["population"] <= 0).any():
        erreurs.append("population régionale manquante ou nulle")
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
    regions = population_regions()
    controles(series, pyramide, regions)
    series.to_csv(DOSSIER_TRAITE / "indicateurs_nationaux.csv")
    pyramide.to_csv(DOSSIER_TRAITE / "pyramide_ages.csv", index=False)
    regions.drop(columns="cle").to_csv(DOSSIER_TRAITE / "population_regions.csv", index=False)
    print(f"  -> {len(series)} années d'indicateurs, {regions['region'].nunique()} régions")
    return series, pyramide, regions
