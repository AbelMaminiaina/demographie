"""Étape 4 : tableau de bord interactif (page HTML autonome, publiée sur GitHub Pages)."""
import json
from datetime import date

from config import DOSSIER_SORTIES, INDICATEURS_DHS, RACINE, brut
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


def annee_courante_wp100(wp100):
    annees = sorted(int(c.split("_")[1]) for c in wp100.columns if c.startswith("wp100_"))
    return min(date.today().year, annees[-1])


def _menages(r):
    """Ménages ordinaires du recensement : nombre, taille moyenne, part dirigée par une femme (%),
    taille en milieu urbain et rural, et selon le sexe du chef (régions et districts)."""
    valeurs = {"m": int(r["menages"]), "t": round(float(r["taille_menage"]), 2),
               "f": round(float(r["chef_femme_pct"]), 1)}
    for cle, colonne in (("tu", "taille_menage_urbain"), ("tr", "taille_menage_rural"),
                         ("th", "taille_menage_chef_homme"), ("tf", "taille_menage_chef_femme")):
        if colonne in r and r[colonne] == r[colonne]:
            valeurs[cle] = round(float(r[colonne]), 1)
    return valeurs


def _niveaux(donnees):
    niveaux, wp, dhs = donnees["niveaux"], donnees["worldpop"], donnees["dhs"]
    annees_wp = sorted(int(a) for a in wp["regions"]["annee"].unique())
    index = {n: {p: i for i, p in enumerate(niveaux[n]["unites"]["pcode"])} for n in TOLERANCES}
    dhs_par_cle = dhs.set_index("cle")[[c for c in INDICATEURS_DHS.values() if c in dhs]]
    rgph = donnees["rgph3"]
    rg_par_cle = {n: rgph[n].set_index("cle") for n in ("regions", "districts")}
    rg_communes = rgph["communes"].dropna(subset=["cle_hdx"]).set_index("cle_hdx")

    resultat = {}
    for niveau in TOLERANCES:
        unites = niveaux[niveau]["unites"]
        serie_wp = wp[niveau].pivot(index="cle", columns="annee", values="population")
        lignes, entites = [], []
        for i, u in unites.iterrows():
            ligne = {"n": u["nom"], "pc": u["pcode"], "p": int(u["population"]), "s": round(float(u["superficie_km2"]), 1),
                     "d": round(float(u["densite"]), 1),
                     "wp": [int(round(v)) for v in serie_wp.loc[u["cle"], annees_wp]]}
            if niveau != "regions":
                ligne["r"] = index["regions"][u["region_pcode"]]
            if niveau == "communes":
                ligne["di"] = index["districts"][u["district_pcode"]]
            if niveau in rg_par_cle:
                r = rg_par_cle[niveau].loc[u["cle"]]
                ligne["rg"] = {"p": int(r["population"]), "u": round(float(r["part_urbaine_pct"]), 1),
                               "rm": round(float(r["rapport_masculinite"]), 1), "d": round(float(r["densite"]), 1),
                               "e": round(float(r["ecart_estimation_pct"]), 1), **_menages(r)}
            elif u["cle"] in rg_communes.index:
                r = rg_communes.loc[u["cle"]]
                ligne["rg"] = {"p": int(r["population"]), "u": round(float(r["part_urbaine_pct"]), 1),
                               "c": r["correspondance"], "id": bool(r["decoupage_identique"]), **_menages(r)}
            if niveau == "regions":
                ligne["dhs"] = {c: (None if v != v else float(v)) for c, v in dhs_par_cle.loc[u["cle"]].items()}
            lignes.append(ligne)
            entites.append({"type": "Feature", "properties": {"i": i},
                            "geometry": simplifier(niveaux[niveau]["contours"][u["cle"]], TOLERANCES[niveau])})
        resultat[niveau] = {"unites": lignes, "geo": {"type": "FeatureCollection", "features": entites}}

    # Fokontany : un niveau de carte à part entière. La région et le district se déduisent de
    # la commune (indice « c ») ; les contours sont compressés (voir _encoder_contours).
    cales = donnees["fokontany_cales"].set_index("cle")["population_calee"]
    wp100 = donnees["worldpop_100m"].set_index("cle")
    colonnes_wp100 = [f"wp100_{a}" for a in annees_wp]
    unites_fk = niveaux["fokontany"]["unites"]
    lignes = []
    for _, f in unites_fk.iterrows():
        cale = cales.get(f["cle"])
        lignes.append({"n": f["nom"], "pc": f["pcode"], "c": index["communes"][f["commune_pcode"].split("|")[0]],
                       "p": int(f["population"]), "ca": None if cale != cale else int(cale),
                       "s": round(float(f["superficie_km2"]), 2),
                       "wp": [int(v) for v in wp100.loc[f["cle"], colonnes_wp100]]})
    resultat["fokontany"] = {"unites": lignes, "echelle": PRECISION_FK, "anneaux": [
        _encoder_contours(niveaux["fokontany"]["contours"][c]) for c in unites_fk["cle"]]}
    return resultat, annees_wp


# Contours des fokontany : simplification (degrés) et précision des coordonnées (1/10 000 de degré, environ 11 m)
TOLERANCE_FK, PRECISION_FK = 0.0008, 10_000


def _encoder_contours(geometrie, tolerance=TOLERANCE_FK):
    """Contours simplifiés, en entiers (1/PRECISION_FK de degré), chaque point codé par son écart au précédent.

    Ce codage divise environ par deux la taille des 17 464 contours de fokontany.
    """
    anneaux = []
    for polygone in simplifier(geometrie, tolerance, 4)["coordinates"]:
        plat, px, py = [], 0, 0
        for x, y in polygone[0]:
            ix, iy = round(x * PRECISION_FK), round(y * PRECISION_FK)
            plat += [ix - px, iy - py]
            px, py = ix, iy
        anneaux.append(plat)
    return anneaux


def generer(donnees):
    niveaux, annees_wp = _niveaux(donnees)
    try:
        collecte = json.loads(brut("journal").read_text(encoding="utf-8"))["fin"][:10]
    except FileNotFoundError:
        collecte = date.today().isoformat()
    contenu = {
        "meta": {"collecte": collecte, "annee_ref": int(donnees["niveaux"]["regions"]["population"]["annee"].max()),
                 "annees_wp": annees_wp, "enquete_dhs": donnees["dhs"].attrs.get("enquete", "DHS"),
                 "noms_dhs": {c: n for c, n in NOMS_DHS.items() if c in donnees["dhs"]},
                 "rgph_total": int(donnees["rgph3"]["regions"]["population"].sum()),
                 "rgph_communes": len(donnees["rgph3"]["communes"]),
                 "annee_wp100": annee_courante_wp100(donnees["worldpop_100m"])},
        **_national(donnees),
        "niveaux": niveaux,
    }
    texte = json.dumps(contenu, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
    page = MODELE.read_text(encoding="utf-8").replace("/*__DONNEES__*/null", texte)
    DOSSIER.mkdir(parents=True, exist_ok=True)
    chemin = DOSSIER / "index.html"
    chemin.write_text(page, encoding="utf-8")
    print(f"  -> sorties/tableau_de_bord/index.html ({chemin.stat().st_size / 1e6:.1f} Mo)")
    return chemin
