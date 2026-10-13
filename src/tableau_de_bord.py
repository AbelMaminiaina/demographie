"""Étape 4 : tableau de bord interactif (page HTML autonome, publiée sur GitHub Pages)."""
import json
from datetime import date

from config import DOSSIER_BRUT, DOSSIER_SORTIES, INDICATEURS_DHS, RACINE
from geometrie import simplifier

MODELE = RACINE / "src" / "modele_tableau_de_bord.html"
DOSSIER = DOSSIER_SORTIES / "tableau_de_bord"

# Tolérance de simplification des contours (degrés) : la page doit rester légère.
TOLERANCES = {"regions": 0.004, "districts": 0.003, "communes": 0.0015}

NOMS_DHS = {
    "fecondite_isf": "Enfants par femme (ISF)",
    "age_median_premiere_naissance": "Âge médian à la 1re naissance",
    "contraception_moderne_pct": "Contraception moderne (%)",
    "accouchement_etablissement_pct": "Accouchement en établissement (%)",
    "mortalite_infantile_pour_mille": "Mortalité infantile (‰)",
    "mortalite_moins_5_ans_pour_mille": "Mortalité avant 5 ans (‰)",
    "retard_croissance_pct": "Retard de croissance (%)",
    "alphabetisation_femmes_pct": "Femmes alphabétisées (%)",
}


def _liste(serie, decimales=None):
    return [None if v != v else (round(float(v), decimales) if decimales is not None else int(v))
            for v in serie]


def _national(donnees):
    s = donnees["series"]
    proj = donnees["projections"]
    pyr = donnees["pyramide"]
    groupes = sorted(pyr["groupe_age"].unique(), key=lambda g: int(g.split("-")[0].rstrip("+")))
    large = pyr.pivot_table(index="annee", columns=["sexe", "groupe_age"], values="effectif")
    return {
        "national": {
            "annees": [int(a) for a in s.index],
            "population": _liste(s["population"], 0),
            "croissance": _liste(s["croissance_pct"], 2),
            "isf": _liste(s["fecondite_isf"], 2),
            "esperance": _liste(s["esperance_vie"], 1),
            "urbanisation": _liste(s["urbanisation_pct"], 1),
            "mortalite_infantile": _liste(s["mortalite_infantile_pour_mille"], 1),
        },
        "projections": {
            "annees": [int(a) for a in proj.index],
            "population": _liste(proj["population"], 0),
            "p014": _liste(proj["part_0_14_pct"], 1),
            "p65": _liste(proj["part_65_plus_pct"], 1),
        },
        "pyramide": {
            "annees": [int(a) for a in large.index],
            "groupes": groupes,
            "H": [_liste(large.loc[a, "H"].reindex(groupes), 0) for a in large.index],
            "F": [_liste(large.loc[a, "F"].reindex(groupes), 0) for a in large.index],
        },
    }


def _niveaux(donnees):
    niveaux, wp, dhs = donnees["niveaux"], donnees["worldpop"], donnees["dhs"]
    annees_wp = sorted(int(a) for a in wp["regions"]["annee"].unique())
    index = {n: {p: i for i, p in enumerate(niveaux[n]["unites"]["pcode"])} for n in TOLERANCES}
    dhs_par_cle = dhs.set_index("cle")[[c for c in INDICATEURS_DHS.values() if c in dhs]]

    resultat = {}
    for niveau in TOLERANCES:
        unites = niveaux[niveau]["unites"]
        serie_wp = wp[niveau].pivot(index="cle", columns="annee", values="population")
        lignes, entites = [], []
        for i, u in unites.iterrows():
            ligne = {"n": u["nom"], "p": int(u["population"]), "s": round(float(u["superficie_km2"]), 1),
                     "d": round(float(u["densite"]), 1),
                     "wp": [int(round(v)) for v in serie_wp.loc[u["cle"], annees_wp]]}
            if niveau != "regions":
                ligne["r"] = index["regions"][u["region_pcode"]]
            if niveau == "communes":
                ligne["di"] = index["districts"][u["district_pcode"]]
            if niveau == "regions":
                ligne["dhs"] = {c: (None if v != v else float(v)) for c, v in dhs_par_cle.loc[u["cle"]].items()}
            lignes.append(ligne)
            entites.append({"type": "Feature", "properties": {"i": i},
                            "geometry": simplifier(niveaux[niveau]["contours"][u["cle"]], TOLERANCES[niveau])})
        resultat[niveau] = {"unites": lignes, "geo": {"type": "FeatureCollection", "features": entites}}

    # Fokontany regroupés par commune, du plus peuplé au moins peuplé
    fk = [[] for _ in range(len(niveaux["communes"]["unites"]))]
    for _, f in niveaux["fokontany"]["unites"].iterrows():
        fk[index["communes"][f["commune_pcode"].split("|")[0]]].append(
            [f["nom"], int(f["population"]), round(float(f["densite"]))])
    return resultat, fk, annees_wp


def generer(donnees):
    niveaux, fokontany, annees_wp = _niveaux(donnees)
    try:
        collecte = (DOSSIER_BRUT / "derniere_collecte.txt").read_text(encoding="utf-8").strip()[:10]
    except FileNotFoundError:
        collecte = date.today().isoformat()
    contenu = {
        "meta": {"collecte": collecte, "annee_rgph": int(donnees["niveaux"]["regions"]["population"]["annee"].max()),
                 "annees_wp": annees_wp, "enquete_dhs": donnees["dhs"].attrs.get("enquete", "DHS"),
                 "noms_dhs": {c: n for c, n in NOMS_DHS.items() if c in donnees["dhs"]}},
        **_national(donnees),
        "niveaux": niveaux,
        "fokontany": fokontany,
    }
    texte = json.dumps(contenu, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
    page = MODELE.read_text(encoding="utf-8").replace("/*__DONNEES__*/null", texte)
    DOSSIER.mkdir(parents=True, exist_ok=True)
    chemin = DOSSIER / "index.html"
    chemin.write_text(page, encoding="utf-8")
    print(f"  -> sorties/tableau_de_bord/index.html ({chemin.stat().st_size / 1e6:.1f} Mo)")
    return chemin
