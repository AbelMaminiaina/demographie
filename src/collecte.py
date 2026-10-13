"""Étape 1 : téléchargement des données brutes depuis les API publiques."""
import json
from datetime import datetime, timezone

import requests

from config import (BANQUE_MONDIALE_URL, DOSSIER_BRUT, GEOBOUNDARIES_URL,
                    HDX_DATASET, HDX_URL, INDICATEURS, PAYS)

TIMEOUT = 60


def _ecrire(nom, contenu):
    DOSSIER_BRUT.mkdir(parents=True, exist_ok=True)
    chemin = DOSSIER_BRUT / nom
    mode = "wb" if isinstance(contenu, bytes) else "w"
    with open(chemin, mode, **({} if mode == "wb" else {"encoding": "utf-8"})) as f:
        f.write(contenu)
    print(f"  -> {chemin.relative_to(DOSSIER_BRUT.parent.parent)}")
    return chemin


def codes_pyramide():
    """Codes Banque mondiale des effectifs par groupe d'âge quinquennal et sexe."""
    groupes = [f"{a:02d}{a + 4:02d}" for a in range(0, 80, 5)] + ["80UP"]
    return [f"SP.POP.{g}.{s}" for g in groupes for s in ("FE", "MA")]


def banque_mondiale():
    """Indicateurs nationaux (séries annuelles) via l'API WDI."""
    print("Banque mondiale (WDI)...")
    codes = list(INDICATEURS) + codes_pyramide()
    lignes = []
    # Une requête par indicateur : les effectifs par âge viennent d'une autre
    # base (Santé/Population) que les indicateurs WDI, ce qui empêche de les grouper.
    with requests.Session() as session:
        for code in codes:
            r = session.get(f"{BANQUE_MONDIALE_URL}/country/{PAYS}/indicator/{code}",
                            params={"format": "json", "per_page": 1000}, timeout=TIMEOUT)
            r.raise_for_status()
            reponse = r.json()
            if len(reponse) < 2:
                raise RuntimeError(f"Réponse inattendue pour {code} : {reponse}")
            lignes += reponse[1] or []
    return _ecrire("banque_mondiale.json", json.dumps(lignes, ensure_ascii=False))


def hdx_population_regions():
    """Population par région (ADM1), projections INSTAT publiées sur HDX."""
    print("HDX (population par région)...")
    r = requests.get(f"{HDX_URL}/package_show", params={"id": HDX_DATASET}, timeout=TIMEOUT)
    r.raise_for_status()
    ressource = next(x for x in r.json()["result"]["resources"]
                     if x["name"].endswith("adm1_2018.csv"))
    fichier = requests.get(ressource["url"], timeout=TIMEOUT)
    fichier.raise_for_status()
    return _ecrire("hdx_population_adm1.csv", fichier.content)


def limites_regions():
    """Contours simplifiés des régions (geoBoundaries)."""
    print("geoBoundaries (contours des régions)...")
    r = requests.get(GEOBOUNDARIES_URL, timeout=TIMEOUT)
    r.raise_for_status()
    geo = requests.get(r.json()["simplifiedGeometryGeoJSON"], timeout=TIMEOUT)
    geo.raise_for_status()
    return _ecrire("regions.geojson", geo.content)


def tout_collecter():
    banque_mondiale()
    hdx_population_regions()
    limites_regions()
    horodatage = datetime.now(timezone.utc).isoformat(timespec="seconds")
    _ecrire("derniere_collecte.txt", horodatage + "\n")
