"""Étape 5 : données de l'application web (React), écrites dans sorties/web/donnees/.

Les fichiers sont découpés pour que l'application ne charge d'abord que l'essentiel ;
les fokontany (attributs et contours) ne sont chargés que lorsqu'on choisit ce niveau.
"""
import json

import telechargements
from config import DOSSIER_SORTIES
from config import NIVEAUX_ECOLES, TYPES_SANTE
from tableau_de_bord import NOMS_DHS, _national, _niveaux, annee_courante_wp100, brut

DOSSIER = DOSSIER_SORTIES / "web" / "donnees"


def _ecrire(nom, contenu):
    chemin = DOSSIER / nom
    chemin.write_text(json.dumps(contenu, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    return chemin.stat().st_size


def _enquetes(donnees):
    """Pauvreté (Banque mondiale) et emploi (OIT) d'après les enquêtes de l'INSTAT."""
    pauvrete = donnees["pauvrete"]
    emploi = donnees["emploi"]
    emploi = emploi[emploi["enquete"].str.match(r"ENEMPSI|ENESI|EPM 20(1[5-9]|2)")]

    def valeurs(df, colonnes):
        return [{c: (None if r[c] != r[c] else (round(float(r[c]), 2) if isinstance(r[c], float) else r[c]))
                 for c in colonnes} for _, r in df.iterrows()]

    return {
        "pauvrete": valeurs(pauvrete, ["annee", "enquete", "gini", "pauvrete_3_00_dollars_pct",
                                       "pauvrete_4_20_dollars_pct", "pauvrete_8_30_dollars_pct"]),
        "emploi": valeurs(emploi, ["annee", "enquete", "rupture_de_serie", "taux_activite_pct", "taux_emploi_pct",
                                   "taux_chomage_pct", "emploi_informel_pct", "part_agriculture_pct",
                                   "part_salaries_pct", "jeunes_neet_pct", "emploi_total_milliers"]),
    }


def _recensement_national(donnees):
    """Valeurs nationales du recensement, avec les clés courtes des unités (voir types.ts)."""
    n = donnees["rgph3"]["regions"].attrs["national"]
    cles = {"p": "population", "u": "part_urbaine_pct", "rm": "rapport_masculinite", "d": "densite",
            "m": "menages", "t": "taille_menage", "f": "chef_femme_pct", "tu": "taille_menage_urbain",
            "tr": "taille_menage_rural", "th": "taille_menage_chef_homme", "tf": "taille_menage_chef_femme"}
    return {c: (n[col] if isinstance(n[col], int) else round(float(n[col]), 2)) for c, col in cles.items()}


def generer(donnees):
    DOSSIER.mkdir(parents=True, exist_ok=True)
    niveaux, annees_wp = _niveaux(donnees)
    try:
        collecte = json.loads(brut("journal").read_text(encoding="utf-8"))["fin"][:10]
    except FileNotFoundError:
        collecte = None
    fokontany = niveaux.pop("fokontany")
    tailles = {
        "base.json": _ecrire("base.json", {
            "meta": {"collecte": collecte,
                     "annee_ref": int(donnees["niveaux"]["regions"]["population"]["annee"].max()),
                     "annees_wp": annees_wp, "enquete_dhs": donnees["dhs"].attrs.get("enquete", "DHS"),
                     "noms_dhs": {c: n for c, n in NOMS_DHS.items() if c in donnees["dhs"]},
                     "rgph_total": int(donnees["rgph3"]["regions"]["population"].sum()),
                     "rgph_communes": len(donnees["rgph3"]["communes"]),
                     "annee_wp100": annee_courante_wp100(donnees["worldpop_100m"]),
                     "nb_fokontany": len(fokontany["unites"]),
                     "nb_sante": len(donnees["sante"]),
                     "nb_ecoles": len(donnees["ecoles"]),
                     "osm_ecoles": donnees["ecoles"].attrs.get("instantane"),
                     "rg_national": _recensement_national(donnees)},
            **_national(donnees),
            "enquetes": _enquetes(donnees),
            # Attributs des régions, districts et communes ; leurs contours sont dans contours_<niveau>.json
            "niveaux": {n: d["unites"] for n, d in niveaux.items()},
        }),
        "fokontany.json": _ecrire("fokontany.json", {"unites": fokontany["unites"]}),
        # Points de la carte : [longitude, latitude, type (0 centre, 1 poste, 2 hôpital), nom]
        "sante.json": _ecrire("sante.json", {"points": [
            [round(e.longitude, 4), round(e.latitude, 4), list(TYPES_SANTE.values()).index(e.type), e.nom]
            for e in donnees["sante"].itertuples()]}),
        # Écoles : [longitude, latitude, niveau (indice dans NIVEAUX_ECOLES), nom, statut (0 inconnu, 1 public, 2 privé)]
        "ecoles.json": _ecrire("ecoles.json", {"points": [
            [round(e.longitude, 4), round(e.latitude, 4), NIVEAUX_ECOLES.index(e.niveau), e.universite_publique or e.nom,
             ("inconnu", "public", "privé").index(e.statut)]
            for e in donnees["ecoles"].itertuples()]}),
        "contours_fokontany.json": _ecrire("contours_fokontany.json",
                                           {"echelle": fokontany["echelle"], "anneaux": fokontany["anneaux"]}),
    }
    for niveau, d in niveaux.items():
        tailles[f"contours_{niveau}.json"] = _ecrire(f"contours_{niveau}.json", d["geo"])
    total = sum(tailles.values()) / 1e6
    print(f"  -> sorties/web/donnees/ ({len(tailles)} fichiers, {total:.1f} Mo)")
    telechargements.generer(collecte)
    return DOSSIER
