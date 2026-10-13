"""Étape 1 : téléchargement des données brutes depuis les API publiques."""
import json
from datetime import datetime, timezone

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from config import (BANQUE_MONDIALE_URL, DHS_PAYS, DHS_URL, DOSSIER_BRUT, GEOBOUNDARIES_URL,
                    HDX_DATASET, HDX_URL, INDICATEURS, INDICATEURS_DHS,
                    INDICATEURS_PROJECTIONS, NIVEAUX, PAYS, SOURCE_PROJECTIONS, WORLDPOP_URL)

TIMEOUT = 60

# Les serveurs coupent parfois la connexion : jusqu'à 5 nouvelles tentatives espacées.
SESSION = requests.Session()
SESSION.mount("https://", HTTPAdapter(max_retries=Retry(
    total=5, backoff_factor=2, status_forcelist=(429, 500, 502, 503, 504))))


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


def _series_banque_mondiale(codes, **params):
    lignes = []
    # Une requête par indicateur : les effectifs par âge viennent d'une autre
    # base (Santé/Population) que les indicateurs WDI, ce qui empêche de les grouper.
    for code in codes:
        r = SESSION.get(f"{BANQUE_MONDIALE_URL}/country/{PAYS}/indicator/{code}",
                        params={"format": "json", "per_page": 1000, **params}, timeout=TIMEOUT)
        r.raise_for_status()
        reponse = r.json()
        if len(reponse) < 2:
            raise RuntimeError(f"Réponse inattendue pour {code} : {reponse}")
        if not reponse[1]:
            raise RuntimeError(f"Aucune donnée pour {code}")
        lignes += reponse[1]
    return lignes


def banque_mondiale():
    """Indicateurs nationaux (séries annuelles) via l'API WDI."""
    print("Banque mondiale (WDI)...")
    lignes = _series_banque_mondiale(list(INDICATEURS) + codes_pyramide())
    return _ecrire("banque_mondiale.json", json.dumps(lignes, ensure_ascii=False))


def projections_onu():
    """Projections de l'ONU (WPP) jusqu'en 2050, via la Banque mondiale."""
    print("Projections ONU (via Banque mondiale)...")
    lignes = _series_banque_mondiale(list(INDICATEURS_PROJECTIONS), source=SOURCE_PROJECTIONS)
    return _ecrire("projections_onu.json", json.dumps(lignes, ensure_ascii=False))


def dhs():
    """Indicateurs régionaux de la dernière enquête DHS (API publique, sans clé)."""
    print("DHS (enquêtes démographiques et de santé)...")
    r = SESSION.get(f"{DHS_URL}/surveys", params={"countryIds": DHS_PAYS, "surveyType": "DHS",
                                                    "f": "json"}, timeout=TIMEOUT)
    r.raise_for_status()
    enquete = max(r.json()["Data"], key=lambda e: int(e["SurveyYear"]))
    r = SESSION.get(f"{DHS_URL}/data", params={
        "countryIds": DHS_PAYS, "surveyIds": enquete["SurveyId"], "breakdown": "subnational",
        "indicatorIds": ",".join(INDICATEURS_DHS), "f": "json", "perpage": 5000}, timeout=TIMEOUT)
    r.raise_for_status()
    return _ecrire("dhs.json", json.dumps({"enquete": enquete, "donnees": r.json()["Data"]},
                                          ensure_ascii=False))


def worldpop():
    """Grilles de population WorldPop à 1 km, une par année (2015-2030)."""
    print("WorldPop (grilles 1 km)...")
    r = SESSION.get(WORLDPOP_URL, params={"iso3": PAYS}, timeout=TIMEOUT)
    r.raise_for_status()
    dossier = DOSSIER_BRUT / "worldpop"
    dossier.mkdir(parents=True, exist_ok=True)
    for jeu in r.json()["data"]:
        fichier = dossier / f"worldpop_{jeu['popyear']}.tif"
        if fichier.exists():  # les versions publiées ne changent pas
            continue
        tif = SESSION.get(jeu["files"][0], timeout=300)
        tif.raise_for_status()
        fichier.write_bytes(tif.content)
    print(f"  -> data/brut/worldpop/ ({len(list(dossier.glob('*.tif')))} années)")


def hdx_population(niveau):
    """Population par unité administrative, projections INSTAT publiées sur HDX."""
    code = NIVEAUX[niveau]["code"].lower()
    print(f"HDX (population par {niveau})...")
    r = SESSION.get(f"{HDX_URL}/package_show", params={"id": HDX_DATASET}, timeout=TIMEOUT)
    r.raise_for_status()
    ressource = next(x for x in r.json()["result"]["resources"]
                     if x["name"].endswith(f"{code}_2018.csv"))
    fichier = SESSION.get(ressource["url"], timeout=TIMEOUT)
    fichier.raise_for_status()
    return _ecrire(f"hdx_population_{code}.csv", fichier.content)


def limites(niveau):
    """Contours simplifiés des unités administratives (geoBoundaries)."""
    print(f"geoBoundaries (contours des {niveau})...")
    r = SESSION.get(GEOBOUNDARIES_URL.format(niveau=NIVEAUX[niveau]["code"]), timeout=TIMEOUT)
    r.raise_for_status()
    geo = SESSION.get(r.json()["simplifiedGeometryGeoJSON"], timeout=TIMEOUT)
    geo.raise_for_status()
    return _ecrire(f"{niveau}.geojson", geo.content)


def tout_collecter():
    banque_mondiale()
    projections_onu()
    dhs()
    worldpop()
    for niveau in NIVEAUX:
        hdx_population(niveau)
        limites(niveau)
    horodatage = datetime.now(timezone.utc).isoformat(timespec="seconds")
    _ecrire("derniere_collecte.txt", horodatage + "\n")
