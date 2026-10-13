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
GEOBOUNDARIES_URL = "https://www.geoboundaries.org/api/current/gbOpen/MDG/ADM1/"

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
