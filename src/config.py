"""Paramètres communs du pipeline."""
from pathlib import Path

RACINE = Path(__file__).resolve().parent.parent
DOSSIER_BRUT = RACINE / "data" / "brut"
DOSSIER_TRAITE = RACINE / "data" / "traite"
DOSSIER_SORTIES = RACINE / "sorties"

# Classement des fichiers (décrit dans DONNEES.md).
# Données brutes : un dossier par source, fichiers tels que téléchargés.
BRUT = {
    "indicateurs": "banque_mondiale/indicateurs_nationaux.json",
    "projections": "onu_wpp/projections_population.json",
    "population": "instat_hdx/population_{code}_2018.csv",      # code = adm1 ... adm4
    "contours": "geoboundaries/contours_{niveau}.geojson",
    "dhs": "dhs/indicateurs_regions.json",
    "worldpop": "worldpop/population_{annee}_1km.tif",
    "worldpop_100m": "worldpop_100m/population_{annee}_100m.tif",
    "rgph3": "instat_rgph3/resultats_globaux_tome2.pdf",
    "emploi": "oit_ilostat/{indicateur}.csv",
    "pauvrete": "banque_mondiale_pip/pauvrete_madagascar.json",
    "sante_etablissements": "sante_etablissements/etablissements_publics_afrique_subsaharienne.xlsx",
    "journal": "journal_collecte.json",
}
# Données traitées : un dossier par thème, fichiers CSV prêts à l'emploi.
TRAITE = {
    "indicateurs": "national/indicateurs_annuels.csv",
    "pyramide": "national/pyramide_ages.csv",
    "projections": "national/projections_onu.csv",
    "unites": "territoires/{niveau}.csv",
    "series": "territoires/{niveau}_series_2009_2018.csv",
    "dhs": "sante/dhs_regions.csv",
    "worldpop": "estimations/worldpop_{niveau}.csv",
    "worldpop_100m": "estimations/worldpop_100m_fokontany.csv",
    "rgph3": "recensement/rgph3_{niveau}.csv",
    "fokontany_cales": "recensement/fokontany_estimation_calee_rgph3.csv",
    "emploi": "enquetes/emploi_oit.csv",
    "emploi_synthese": "enquetes/emploi_synthese.csv",
    "pauvrete": "enquetes/pauvrete_epm.csv",
    "sante_etablissements": "sante/etablissements_sante_publics.csv",
}


def brut(cle, **parametres):
    return DOSSIER_BRUT / BRUT[cle].format(**parametres)


def traite(cle, **parametres):
    chemin = DOSSIER_TRAITE / TRAITE[cle].format(**parametres)
    chemin.parent.mkdir(parents=True, exist_ok=True)
    return chemin

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
    "fokontany": {"code": "ADM4", "attendus": 17465},
}

# Niveau parent de chaque découpage (pour les contrôles d'emboîtement)
PARENTS = {"districts": "regions", "communes": "districts", "fokontany": "communes"}

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

# Projections démographiques de l'ONU (WPP), republiées par la Banque mondiale
# (base 40 « Population estimates and projections ») : pas de jeton d'accès requis.
SOURCE_PROJECTIONS = 40
INDICATEURS_PROJECTIONS = {
    "SP.POP.TOTL": "population",
    "SP.POP.0014.TO.ZS": "part_0_14_pct",
    "SP.POP.65UP.TO.ZS": "part_65_plus_pct",
}

# Enquêtes démographiques et de santé (DHS) : indicateurs régionaux de la dernière enquête
DHS_URL = "https://api.dhsprogram.com/rest/dhs"
DHS_PAYS = "MD"
INDICATEURS_DHS = {
    "FE_FRTR_W_TFR": "fecondite_isf",
    "FE_AAFB_W_M2B": "age_median_premiere_naissance",
    "FP_CUSM_W_MOD": "contraception_moderne_pct",
    "RH_DELP_C_DHF": "accouchement_etablissement_pct",
    "CM_ECMR_C_IMR": "mortalite_infantile_pour_mille",
    "CM_ECMR_C_U5M": "mortalite_moins_5_ans_pour_mille",
    "CN_NUTS_C_HA2": "retard_croissance_pct",
    "ED_LITR_W_LIT": "alphabetisation_femmes_pct",
}

# WorldPop : estimations de population sur grille de 1 km, 2015-2030 (version R2025A)
WORLDPOP_URL = "https://hub.worldpop.org/rest/data/pop/G2_CN_POP_R25A_1km"
# Même jeu à 100 m (environ 55 Mo par année), agrégé par fokontany
WORLDPOP_100M_URL = "https://hub.worldpop.org/rest/data/pop/G2_CN_POP_R25A_100m"

# Recensement RGPH-3 (2018) : tome 2 des résultats globaux de l'INSTAT, copie hébergée par
# l'UNFPA Madagascar (le site de l'INSTAT est écarté, voir DONNEES.md).
RGPH3_URL = "https://madagascar.unfpa.org/sites/default/files/pub-pdf/resultat_globaux_rgph3_tome_02.pdf"
RGPH3_TOTAL = 25_674_196   # population résidente publiée par l'INSTAT

# Emploi : indicateurs de l'OIT calculés à partir des enquêtes ENEMPSI (2012), ENESI (2015) et EPM.
# Clé SDMX : « MDG » suivi d'une position vide par dimension restante de l'indicateur.
ILO_SDMX_URL = "https://sdmx.ilo.org/rest/data/ILO,{indicateur},1.0/{cle}"
INDICATEURS_EMPLOI = {
    "DF_EAP_DWAP_SEX_AGE_RT": ("MDG....", "taux_activite_pct", "Taux d'activité (%)"),
    "DF_EMP_DWAP_SEX_AGE_RT": ("MDG....", "taux_emploi_pct", "Taux d'emploi (%)"),
    "DF_UNE_DEAP_SEX_AGE_RT": ("MDG....", "taux_chomage_pct", "Taux de chômage (%)"),
    "DF_EMP_NIFL_SEX_RT": ("MDG...", "emploi_informel_pct", "Part de l'emploi informel (%)"),
    "DF_EIP_NEET_SEX_RT": ("MDG....", "jeunes_neet_pct", "Jeunes ni en emploi, ni en études, ni en formation (%)"),
    "DF_EMP_TEMP_SEX_ECO_NB": ("MDG....", "emploi_par_secteur_milliers", "Emploi par secteur d'activité (milliers)"),
    "DF_EMP_TEMP_SEX_STE_NB": ("MDG....", "emploi_par_statut_milliers", "Emploi par statut (milliers)"),
}

# Pauvreté : estimations de la Banque mondiale (Poverty and Inequality Platform) à partir des EPM.
# Seuils internationaux en dollars par jour et par personne, en parité de pouvoir d'achat 2021.
PIP_URL = "https://api.worldbank.org/pip/v1/pip"
SEUILS_PAUVRETE = (3.00, 4.20, 8.30)

# Établissements de santé publics : liste géolocalisée de 50 pays d'Afrique subsaharienne
# (Maina et al., 2019, Scientific Data), compilée à partir de sources gouvernementales.
HDX_SANTE_DATASET = "health-facilities-in-sub-saharan-africa"
TYPES_SANTE = {"Health Centre": "centre de santé", "Health Post": "poste de santé", "Hospital": "hôpital"}
