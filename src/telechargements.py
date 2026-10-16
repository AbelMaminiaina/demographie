"""Données téléchargeables depuis l'application : sorties/web/donnees/telechargements/.

Chaque fichier traité est publié à une adresse stable (CSV, UTF-8, séparateur virgule), avec :
- une archive ZIP de tous les fichiers et du catalogue DONNEES.md ;
- un classeur Excel, une feuille par fichier ;
- catalogue.json, que l'application lit pour afficher la liste.
Les séries 2009-2018 des fokontany (17 Mo, calculées avec un taux uniforme) ne sont pas publiées.
"""
import json
import zipfile
from datetime import date

import pandas as pd

from config import DOSSIER_SORTIES, DOSSIER_TRAITE, RACINE

DOSSIER = DOSSIER_SORTIES / "web" / "donnees" / "telechargements"

LICENCES = {
    "instat": "Publication officielle de l'INSTAT, citation obligatoire",
    "hdx": "CC BY 3.0 IGO (INSTAT et BNGRC, diffusion OCHA)",
    "worldpop": "CC BY 4.0 (WorldPop, université de Southampton)",
    "bm": "CC BY 4.0 (Banque mondiale)",
    "onu": "CC BY 3.0 IGO (ONU, World Population Prospects)",
    "dhs": "Données publiques du programme DHS, citation obligatoire",
    "oit": "CC BY 4.0 (OIT, ILOSTAT)",
    "sante": "CC BY 4.0 (Maina et al., 2019, Scientific Data, diffusion HDX)",
}

# (chemin dans data/traite, thème, description, licence, nom de feuille Excel)
FICHIERS = [
    ("recensement/rgph3_regions.csv", "recensement", "Recensement 2018 par région : population par sexe et milieu, ménages, taille des ménages, densité", "instat", "Recensement régions"),
    ("recensement/rgph3_districts.csv", "recensement", "Recensement 2018 par district (Antananarivo détaillé par arrondissement)", "instat", "Recensement districts"),
    ("recensement/rgph3_communes.csv", "recensement", "Recensement 2018 par commune (1 727), avec la correspondance au découpage de la carte", "instat", "Recensement communes"),
    ("recensement/fokontany_estimation_calee_rgph3.csv", "recensement", "Fokontany : estimation 2018 calée sur le recensement de la commune (estimation, pas un comptage)", "instat", "Fokontany calés 2018"),
    ("estimations/worldpop_regions.csv", "estimations", "Population estimée par région, 2015-2030 (WorldPop, grille de 1 km)", "worldpop", "WorldPop régions"),
    ("estimations/worldpop_districts.csv", "estimations", "Population estimée par district, 2015-2030 (WorldPop, grille de 1 km)", "worldpop", "WorldPop districts"),
    ("estimations/worldpop_communes.csv", "estimations", "Population estimée par commune, 2015-2030 (WorldPop, grille de 1 km)", "worldpop", "WorldPop communes"),
    ("estimations/worldpop_100m_fokontany.csv", "estimations", "Population estimée par fokontany, 2015-2030 (WorldPop, grille de 100 m)", "worldpop", "WorldPop fokontany"),
    ("territoires/regions.csv", "territoires", "Régions : codes, superficie, estimation 2018 INSTAT/BNGRC (base 2009)", "hdx", "Territoires régions"),
    ("territoires/districts.csv", "territoires", "Districts : codes, rattachement, superficie, estimation 2018", "hdx", "Territoires districts"),
    ("territoires/communes.csv", "territoires", "Communes : codes, rattachement, superficie, estimation 2018", "hdx", "Territoires communes"),
    ("territoires/fokontany.csv", "territoires", "Fokontany (17 464) : codes, rattachement, superficie, estimation 2018", "hdx", "Territoires fokontany"),
    ("territoires/regions_series_2009_2018.csv", "territoires", "Régions : estimations annuelles 2009-2018 (taux de croissance uniforme)", "hdx", None),
    ("territoires/districts_series_2009_2018.csv", "territoires", "Districts : estimations annuelles 2009-2018 (taux de croissance uniforme)", "hdx", None),
    ("territoires/communes_series_2009_2018.csv", "territoires", "Communes : estimations annuelles 2009-2018 (taux de croissance uniforme)", "hdx", None),
    ("national/indicateurs_annuels.csv", "national", "Madagascar, 1960 à aujourd'hui : population, croissance, fécondité, mortalité, espérance de vie, urbanisation", "bm", "National annuel"),
    ("national/projections_onu.csv", "national", "Projections de population de l'ONU jusqu'en 2050", "onu", "Projections ONU"),
    ("national/pyramide_ages.csv", "national", "Population par groupe d'âge de 5 ans et par sexe, chaque année", "bm", "Pyramide des âges"),
    ("sante/dhs_regions.csv", "sante", "Santé et fécondité par région (enquête DHS 2021)", "dhs", "Santé DHS régions"),
    ("sante/etablissements_sante_publics.csv", "sante", "Établissements de santé publics géolocalisés (liste de 2019) : type, coordonnées, commune, district et région", "sante", "Établissements de santé"),
    ("enquetes/pauvrete_epm.csv", "enquetes", "Pauvreté et inégalités par enquête EPM (Banque mondiale)", "bm", "Pauvreté"),
    ("enquetes/emploi_synthese.csv", "enquetes", "Emploi : synthèse par enquête (activité, chômage, informalité, NEET)", "oit", "Emploi synthèse"),
    ("enquetes/emploi_oit.csv", "enquetes", "Emploi : toutes les observations de l'OIT (par sexe, âge, secteur, statut)", "oit", None),
]


def _lisez_moi(collecte):
    return pd.DataFrame({"Démographie de Madagascar": [
        "Données ouvertes sur la population de Madagascar, de la région au fokontany.",
        f"Données collectées le {collecte}. Classeur produit le {date.today().isoformat()}.",
        "Une feuille par fichier ; les mêmes données existent en CSV et sont décrites colonne par colonne dans DONNEES.md.",
        "Chaque source garde sa licence (colonne « Licence » ci-dessous) : citez la source et ce site.",
        "Les populations des fokontany et les séries après 2018 sont des estimations, pas des comptages.",
        "https://abelmaminiaina.github.io/demographie/",
    ]})


def generer(collecte):
    DOSSIER.mkdir(parents=True, exist_ok=True)
    catalogue = []
    for chemin, theme, description, licence, feuille in FICHIERS:
        source = DOSSIER_TRAITE / chemin
        nom = chemin.replace("/", "_")
        contenu = source.read_bytes()
        (DOSSIER / nom).write_bytes(contenu)
        lignes = contenu.count(b"\n") - 1
        catalogue.append({"fichier": nom, "theme": theme, "description": description,
                          "licence": LICENCES[licence], "lignes": lignes, "octets": len(contenu), "excel": feuille})

    with zipfile.ZipFile(DOSSIER / "donnees_madagascar.zip", "w", zipfile.ZIP_DEFLATED) as z:
        for entree in catalogue:
            z.write(DOSSIER / entree["fichier"], entree["fichier"])
        z.write(RACINE / "DONNEES.md", "DONNEES.md")

    with pd.ExcelWriter(DOSSIER / "donnees_madagascar.xlsx", engine="openpyxl") as classeur:
        feuilles = [e for e in catalogue if e["excel"]]
        _lisez_moi(collecte).to_excel(classeur, sheet_name="Lisez-moi", index=False)
        pd.DataFrame([{"Feuille": e["excel"], "Contenu": e["description"], "Licence": e["licence"],
                       "Fichier CSV": e["fichier"]} for e in feuilles]).to_excel(
            classeur, sheet_name="Lisez-moi", index=False, startrow=8)
        for e in feuilles:
            pd.read_csv(DOSSIER / e["fichier"]).to_excel(classeur, sheet_name=e["excel"], index=False, freeze_panes=(1, 0))

    archives = {nom: (DOSSIER / nom).stat().st_size for nom in ("donnees_madagascar.zip", "donnees_madagascar.xlsx")}
    (DOSSIER / "catalogue.json").write_text(json.dumps({"collecte": collecte, "fichiers": catalogue, "archives": archives},
                                                       ensure_ascii=False, indent=1), encoding="utf-8")
    total = sum(e["octets"] for e in catalogue) / 1e6
    print(f"  -> {len(catalogue)} fichiers CSV ({total:.1f} Mo), archive ZIP ({archives['donnees_madagascar.zip'] / 1e6:.1f} Mo), "
          f"classeur Excel ({archives['donnees_madagascar.xlsx'] / 1e6:.1f} Mo)")
