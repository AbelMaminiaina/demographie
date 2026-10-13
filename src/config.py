"""Paramètres communs du pipeline."""
from pathlib import Path

RACINE = Path(__file__).resolve().parent.parent
DOSSIER_BRUT = RACINE / "data" / "brut"
DOSSIER_TRAITE = RACINE / "data" / "traite"
DOSSIER_SORTIES = RACINE / "sorties"

PAYS = "MDG"

BANQUE_MONDIALE_URL = "https://api.worldbank.org/v2"
HDX_URL = "https://data.humdata.org/api/3/action"
HDX_DATASET = "cod-ps-mdg"
GEOBOUNDARIES_URL = "https://www.geoboundaries.org/api/current/gbOpen/MDG/{niveau}/"

# Découpages administratifs : code HDX/geoBoundaries et nombre d'unités attendu
NIVEAUX = {
    "regions": {"code": "ADM1", "attendus": 22},
    "districts": {"code": "ADM2", "attendus": 119},  # dont 6 arrondissements d'Antananarivo
    "communes": {"code": "ADM3", "attendus": 1579},
}

# Niveau parent de chaque découpage (pour les contrôles d'emboîtement)
PARENTS = {"districts": "regions", "communes": "districts"}

# Indicateurs nationaux (code Banque mondiale -> nom de colonne)
INDICATEURS = {
    "SP.POP.TOTL": "population",
    "SP.POP.GROW": "croissance_pct",
    "SP.DYN.TFRT.IN": "fecondite_isf",
    "SP.DYN.CBRT.IN": "natalite_pour_mille",
    "SP.DYN.CDRT.IN": "mortalite_pour_mille",
    "SP.DYN.IMRT.IN": "mortalite_infantile_pour_mille",
    "SP.DYN.LE00.IN": "esperance_vie",
    "SP.URB.TOTL.IN.ZS": "urbanisation_pct",
    "SP.POP.DPND": "ratio_dependance",
}
