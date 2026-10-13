"""Étape 1 : téléchargement des données brutes depuis les API publiques.

Chaque fichier est rangé dans le dossier de sa source (voir `config.BRUT`) et inscrit
dans `data/brut/journal_collecte.json` : adresse d'origine, date, taille et empreinte SHA-256.
"""
import hashlib
import json
from datetime import datetime, timezone

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from config import (BANQUE_MONDIALE_URL, DHS_PAYS, DHS_URL, DOSSIER_BRUT, GEOBOUNDARIES_URL,
                    HDX_DATASET, HDX_URL, INDICATEURS, INDICATEURS_DHS,
                    INDICATEURS_PROJECTIONS, NIVEAUX, PAYS, SOURCE_PROJECTIONS, WORLDPOP_URL, brut)

TIMEOUT = 60

# Les serveurs coupent parfois la connexion : jusqu'à 5 nouvelles tentatives espacées.
SESSION = requests.Session()
SESSION.mount("https://", HTTPAdapter(max_retries=Retry(
    total=5, backoff_factor=2, status_forcelist=(429, 500, 502, 503, 504))))

JOURNAL = []


def _maintenant():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _consigner(chemin, source, url, telecharge=True):
    contenu = chemin.read_bytes()
    JOURNAL.append({
        "fichier": chemin.relative_to(DOSSIER_BRUT).as_posix(),
        "source": source,
        "url": url,
        "date": _maintenant() if telecharge else "déjà présent (version publiée inchangée)",
        "octets": len(contenu),
        "sha256": hashlib.sha256(contenu).hexdigest(),
    })


def _ecrire(chemin, contenu, source, url):
    chemin.parent.mkdir(parents=True, exist_ok=True)
    if isinstance(contenu, bytes):
        chemin.write_bytes(contenu)
    else:
        chemin.write_text(contenu, encoding="utf-8")
    _consigner(chemin, source, url)
    print(f"  -> data/brut/{chemin.relative_to(DOSSIER_BRUT).as_posix()}")
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
    """Indicateurs nationaux (séries annuelles) via l'API de la Banque mondiale."""
    print("Banque mondiale (indicateurs nationaux)...")
    lignes = _series_banque_mondiale(list(INDICATEURS) + codes_pyramide())
    return _ecrire(brut("indicateurs"), json.dumps(lignes, ensure_ascii=False), "Banque mondiale (WDI, HNP)",
                   f"{BANQUE_MONDIALE_URL}/country/{PAYS}/indicator/<code>")


def projections_onu():
    """Projections de l'ONU (WPP) jusqu'en 2050, via la Banque mondiale."""
    print("ONU, World Population Prospects (via Banque mondiale)...")
    lignes = _series_banque_mondiale(list(INDICATEURS_PROJECTIONS), source=SOURCE_PROJECTIONS)
    return _ecrire(brut("projections"), json.dumps(lignes, ensure_ascii=False),
                   "ONU, World Population Prospects (base 40 de la Banque mondiale)",
                   f"{BANQUE_MONDIALE_URL}/country/{PAYS}/indicator/<code>?source={SOURCE_PROJECTIONS}")


def dhs():
    """Indicateurs régionaux de la dernière enquête DHS (API publique, sans clé)."""
    print("DHS (enquête démographique et de santé)...")
    r = SESSION.get(f"{DHS_URL}/surveys", params={"countryIds": DHS_PAYS, "surveyType": "DHS",
                                                    "f": "json"}, timeout=TIMEOUT)
    r.raise_for_status()
    enquete = max(r.json()["Data"], key=lambda e: int(e["SurveyYear"]))
    r = SESSION.get(f"{DHS_URL}/data", params={
        "countryIds": DHS_PAYS, "surveyIds": enquete["SurveyId"], "breakdown": "subnational",
        "indicatorIds": ",".join(INDICATEURS_DHS), "f": "json", "perpage": 5000}, timeout=TIMEOUT)
    r.raise_for_status()
    return _ecrire(brut("dhs"), json.dumps({"enquete": enquete, "donnees": r.json()["Data"]}, ensure_ascii=False),
                   f"DHS Program, enquête {enquete['SurveyId']}", r.url)


def worldpop():
    """Grilles de population WorldPop à 1 km, une par année (2015-2030)."""
    print("WorldPop (grilles 1 km)...")
    r = SESSION.get(WORLDPOP_URL, params={"iso3": PAYS}, timeout=TIMEOUT)
    r.raise_for_status()
    for jeu in r.json()["data"]:
        url = jeu["files"][0]
        fichier = brut("worldpop", annee=jeu["popyear"])
        if fichier.exists():  # déjà téléchargé : les versions publiées ne changent pas
            _consigner(fichier, "WorldPop R2025A", url, telecharge=False)
            continue
        tif = SESSION.get(url, timeout=300)
        tif.raise_for_status()
        _ecrire(fichier, tif.content, "WorldPop R2025A", url)
    print(f"  -> data/brut/worldpop/ ({len(r.json()['data'])} années)")


def instat_population(niveau):
    """Population par unité administrative (estimations INSTAT/BNGRC diffusées par OCHA sur HDX)."""
    code = NIVEAUX[niveau]["code"].lower()
    print(f"INSTAT via HDX (population des {niveau})...")
    r = SESSION.get(f"{HDX_URL}/package_show", params={"id": HDX_DATASET}, timeout=TIMEOUT)
    r.raise_for_status()
    ressource = next(x for x in r.json()["result"]["resources"]
                     if x["name"].endswith(f"{code}_2018.csv"))
    fichier = SESSION.get(ressource["url"], timeout=TIMEOUT)
    fichier.raise_for_status()
    return _ecrire(brut("population", code=code), fichier.content,
                   f"INSTAT/BNGRC via OCHA (HDX {HDX_DATASET})", ressource["url"])


def contours(niveau):
    """Contours simplifiés des unités administratives (geoBoundaries)."""
    print(f"geoBoundaries (contours des {niveau})...")
    r = SESSION.get(GEOBOUNDARIES_URL.format(niveau=NIVEAUX[niveau]["code"]), timeout=TIMEOUT)
    r.raise_for_status()
    meta = r.json()
    geo = SESSION.get(meta["simplifiedGeometryGeoJSON"], timeout=TIMEOUT)
    geo.raise_for_status()
    return _ecrire(brut("contours", niveau=niveau), geo.content,
                   f"geoBoundaries ({meta['boundarySource']}, licence {meta['boundaryLicense']})",
                   meta["simplifiedGeometryGeoJSON"])


def tout_collecter():
    JOURNAL.clear()
    debut = _maintenant()
    banque_mondiale()
    projections_onu()
    dhs()
    worldpop()
    for niveau in NIVEAUX:
        instat_population(niveau)
        contours(niveau)
    chemin = brut("journal")
    chemin.write_text(json.dumps({"debut": debut, "fin": _maintenant(), "fichiers": JOURNAL},
                                 ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"  -> data/brut/{chemin.name} ({len(JOURNAL)} fichiers)")
