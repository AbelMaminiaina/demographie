"""Étape 1 : téléchargement des données brutes depuis les API publiques.

Chaque fichier est rangé dans le dossier de sa source (voir `config.BRUT`) et inscrit
dans `data/brut/journal_collecte.json` : adresse d'origine, date, taille et empreinte SHA-256.
"""
import hashlib
import json
import time
from datetime import datetime, timezone

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from config import (BANQUE_MONDIALE_URL, DHS_PAYS, DHS_URL, DOSSIER_BRUT, GEOBOUNDARIES_URL,
                    HDX_DATASET, HDX_SANTE_DATASET, HDX_URL, ILO_SDMX_URL, INDICATEURS, INDICATEURS_DHS, INDICATEURS_EMPLOI,
                    PIP_URL, SEUILS_PAUVRETE,
                    INDICATEURS_PROJECTIONS, NIVEAUX, PAYS, RGPH3_URL, SOURCE_PROJECTIONS, WORLDPOP_100M_URL,
                    WORLDPOP_URL, brut)

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


def _telecharger_gros_fichier(url, chemin, essais=5):
    """Téléchargement en flux vers un fichier temporaire, renommé une fois complet.

    Le serveur de WorldPop coupe parfois la connexion en cours de transfert : on recommence.
    """
    chemin.parent.mkdir(parents=True, exist_ok=True)
    partiel = chemin.with_suffix(chemin.suffix + ".partiel")
    for essai in range(1, essais + 1):
        try:
            with SESSION.get(url, stream=True, timeout=300) as r:
                r.raise_for_status()
                attendu = int(r.headers.get("Content-Length", 0))
                with open(partiel, "wb") as f:
                    for bloc in r.iter_content(chunk_size=1 << 20):
                        f.write(bloc)
            if attendu and partiel.stat().st_size != attendu:
                raise requests.ConnectionError(f"fichier incomplet ({partiel.stat().st_size} sur {attendu} octets)")
            partiel.replace(chemin)
            return chemin
        except requests.RequestException as erreur:
            if essai == essais:
                raise
            print(f"  nouvel essai ({essai}/{essais}) : {erreur}")


def worldpop(cle="worldpop", url_api=WORLDPOP_URL, libelle="1 km"):
    """Grilles de population WorldPop, une par année (2015-2030)."""
    print(f"WorldPop (grilles {libelle})...")
    r = SESSION.get(url_api, params={"iso3": PAYS}, timeout=TIMEOUT)
    r.raise_for_status()
    jeux = r.json()["data"]
    for jeu in jeux:
        url = jeu["files"][0]
        fichier = brut(cle, annee=jeu["popyear"])
        if not fichier.exists():  # les versions publiées ne changent pas : on garde celles déjà là
            _telecharger_gros_fichier(url, fichier)
            _consigner(fichier, f"WorldPop R2025A, {libelle}", url)
        else:
            _consigner(fichier, f"WorldPop R2025A, {libelle}", url, telecharge=False)
    print(f"  -> data/brut/{brut(cle, annee='*').parent.name}/ ({len(jeux)} années)")


def emploi_oit(essais=6):
    """Indicateurs d'emploi de l'OIT pour Madagascar (API SDMX, sans clé).

    Le serveur refuse par intermittence les requêtes rapprochées (erreur 403) : on espace les
    appels et on recommence en attendant de plus en plus longtemps.
    """
    print("OIT (indicateurs d'emploi des enquêtes ENEMPSI, ENESI et EPM)...")
    for indicateur, (cle, _, _) in INDICATEURS_EMPLOI.items():
        url = ILO_SDMX_URL.format(indicateur=indicateur, cle=cle)
        for essai in range(1, essais + 1):
            r = SESSION.get(url, timeout=TIMEOUT, headers={"Accept": "application/vnd.sdmx.data+csv"})
            if r.status_code == 200 and "sdmx" in r.headers.get("Content-Type", "") and r.text.startswith("DATAFLOW"):
                break
            if essai == essais:
                raise RuntimeError(f"OIT : {indicateur} indisponible (code {r.status_code})")
            time.sleep(5 * essai)
        _ecrire(brut("emploi", indicateur=indicateur), r.text, "OIT, ILOSTAT (API SDMX)", url)
        time.sleep(2)


def pauvrete_pip():
    """Taux de pauvreté et inégalités tirés des enquêtes auprès des ménages (Banque mondiale, PIP)."""
    print("Banque mondiale, Poverty and Inequality Platform (enquêtes EPM)...")
    lignes = []
    for seuil in SEUILS_PAUVRETE:
        r = SESSION.get(PIP_URL, params={"country": PAYS, "year": "all", "povline": seuil, "format": "json"},
                        timeout=TIMEOUT)
        r.raise_for_status()
        lignes += r.json()
    if not lignes:
        raise RuntimeError("PIP : aucune donnée pour Madagascar")
    return _ecrire(brut("pauvrete"), json.dumps(lignes, ensure_ascii=False), "Banque mondiale, PIP",
                   f"{PIP_URL}?country={PAYS}&year=all&povline=<seuil>")


def rgph3():
    """Résultats globaux du RGPH-3, tome 2 (PDF de l'INSTAT, copie de l'UNFPA Madagascar)."""
    print("RGPH-3 (résultats globaux, tome 2)...")
    fichier = brut("rgph3")
    if fichier.exists():  # publication de décembre 2020, définitive
        _consigner(fichier, "INSTAT, RGPH-3 résultats globaux tome 2 (copie UNFPA)", RGPH3_URL, telecharge=False)
        return fichier
    r = SESSION.get(RGPH3_URL, timeout=300)
    r.raise_for_status()
    if not r.content.startswith(b"%PDF"):
        raise RuntimeError("RGPH-3 : le fichier téléchargé n'est pas un PDF")
    return _ecrire(fichier, r.content, "INSTAT, RGPH-3 résultats globaux tome 2 (copie UNFPA)", RGPH3_URL)


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


def etablissements_sante():
    """Établissements de santé publics géolocalisés (liste de 2019 diffusée sur HDX)."""
    print("Établissements de santé publics (HDX)...")
    fichier = brut("sante_etablissements")
    source = "Maina et al. 2019, établissements de santé publics d'Afrique subsaharienne (HDX, CC BY 4.0)"
    r = SESSION.get(f"{HDX_URL}/package_show", params={"id": HDX_SANTE_DATASET}, timeout=TIMEOUT)
    r.raise_for_status()
    url = next(x["url"] for x in r.json()["result"]["resources"] if x["format"].upper() == "XLSX")
    if fichier.exists():  # liste publiée en 2019, définitive
        _consigner(fichier, source, url, telecharge=False)
        return fichier
    _telecharger_gros_fichier(url, fichier)
    _consigner(fichier, source, url)
    print(f"  -> data/brut/{fichier.relative_to(DOSSIER_BRUT).as_posix()}")
    return fichier


def tout_collecter():
    JOURNAL.clear()
    debut = _maintenant()
    banque_mondiale()
    projections_onu()
    dhs()
    worldpop()
    worldpop("worldpop_100m", WORLDPOP_100M_URL, "100 m")
    rgph3()
    emploi_oit()
    pauvrete_pip()
    etablissements_sante()
    for niveau in NIVEAUX:
        instat_population(niveau)
        contours(niveau)
    chemin = brut("journal")
    chemin.write_text(json.dumps({"debut": debut, "fin": _maintenant(), "fichiers": JOURNAL},
                                 ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"  -> data/brut/{chemin.name} ({len(JOURNAL)} fichiers)")
