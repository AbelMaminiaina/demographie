"""Visuels LinkedIn : images des posts (format 4:5, 1080 × 1350) et carrousel PDF sur l'exemple d'Antsirabe II.

Usage : python linkedin_visuels.py <dossier_donnees> <dossier_exemple_livrable> <dossier_sortie>
Le dossier de l'exemple est celui produit par livrable_microplan.py --public (cartes d'aperçu).
"""
import json
import math
import sys
import textwrap
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager
from matplotlib.backends.backend_pdf import PdfPages
from matplotlib.collections import PolyCollection
from matplotlib.patches import FancyBboxPatch

DONNEES, EXEMPLE, SORTIE = Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3])
SORTIE.mkdir(parents=True, exist_ok=True)

for f in ("segoeui.ttf", "segoeuib.ttf", "seguisb.ttf"):
    chemin = Path("C:/Windows/Fonts") / f
    if chemin.exists():
        font_manager.fontManager.addfont(str(chemin))
plt.rcParams["font.family"] = ["Segoe UI", "DejaVu Sans"]

BLEU, BLEU_FONCE, ENCRE, GRIS, FOND = "#1c5cab", "#0d366b", "#13201d", "#5b6670", "#f4f7fb"
RAMPE_BLEU = ["#cde2fb", "#9ec5f4", "#6da7ec", "#3987e5", "#184f95"]
RAMPE_ORANGE = ["#fde7c8", "#f9c98a", "#f2a54a", "#e07b1a", "#a8520a"]
SITE = "abelmaminiaina.github.io/demographie"
L, H, DPI = 7.2, 9.0, 150   # 1080 × 1350 pixels

base = json.loads((DONNEES / "base.json").read_text(encoding="utf-8"))
NIV = base["niveaux"]
I26, I30 = base["meta"]["annees_wp"].index(2026), base["meta"]["annees_wp"].index(2030)


def nb(v):
    return f"{round(v):,}".replace(",", "\u202f")


def contours(niveau):
    g = json.loads((DONNEES / f"contours_{niveau}.json").read_text(encoding="utf-8"))
    res = {}
    for f in g["features"]:
        geo = f["geometry"]
        polys = geo["coordinates"] if geo["type"] == "MultiPolygon" else [geo["coordinates"]]
        res[f["properties"]["i"]] = [p[0] for p in polys]
    return res


def classe(v, seuils):
    return sum(v >= s for s in seuils)


def carte(fig, rect, formes, couleurs, bord="white", epaisseur=0.15):
    ax = fig.add_axes(rect)
    anneaux, teintes = [], []
    for i, anns in formes.items():
        for a in anns:
            anneaux.append(a)
            teintes.append(couleurs[i])
    ax.add_collection(PolyCollection(anneaux, facecolors=teintes, edgecolors=bord, linewidths=epaisseur))
    ax.set_aspect(1 / math.cos(math.radians(-19)))
    ax.autoscale_view()
    ax.axis("off")
    return ax


def page(fond="white"):
    fig = plt.figure(figsize=(L, H), dpi=DPI)
    fig.patch.set_facecolor(fond)
    return fig


def texte(fig, x, y, s, taille, couleur=ENCRE, gras=False, largeur=None, interligne=1.25, **k):
    if largeur:
        s = "\n".join(textwrap.fill(p, largeur) for p in s.split("\n"))
    fig.text(x, y, s, fontsize=taille, color=couleur, fontweight="bold" if gras else "normal", va="top",
             linespacing=interligne, **k)


def bandeau(fig, sombre=False, numero=None):
    """Pied commun : site et sources, numéro de diapositive pour le carrousel."""
    c = "white" if sombre else GRIS
    fig.text(0.07, 0.035, "Démographie de Madagascar · " + SITE, fontsize=8.5, color=c, fontweight="bold")
    if numero:
        fig.text(0.93, 0.035, numero, fontsize=8.5, color=c, ha="right")


def legende(fig, x, y, rampe, gauche, droite):
    for k, c in enumerate(rampe):
        fig.patches.append(FancyBboxPatch((x + k * 0.045, y), 0.045, 0.012, boxstyle="square,pad=0", fc=c, ec="none",
                                          transform=fig.transFigure, figure=fig))
    fig.text(x, y - 0.008, gauche, fontsize=8, color=GRIS, va="top")
    fig.text(x + len(rampe) * 0.045, y - 0.008, droite, fontsize=8, color=GRIS, va="top", ha="right")


def chiffre(fig, x, y, valeur, libelle, couleur=BLEU, taille=30, clair=False):
    fig.text(x, y, valeur, fontsize=taille, color="white" if clair else couleur, fontweight="bold", va="top")
    fig.text(x, y - taille / 520, textwrap.fill(libelle, 24), fontsize=10.5, color="white" if clair else GRIS,
             va="top", linespacing=1.2)


# ---------- Image du post 1 : la population par commune ----------
def post_population():
    fig = page()
    communes = NIV["communes"]
    dens = {i: c["wp"][I26] / c["s"] if c.get("s") else 0 for i, c in enumerate(communes)}
    seuils = [10, 25, 50, 100]
    couleurs = {i: RAMPE_BLEU[classe(v, seuils)] for i, v in dens.items()}
    carte(fig, [0.30, 0.08, 0.66, 0.74], contours("communes"), couleurs, epaisseur=0.08)
    total = sum(r["wp"][I26] for r in NIV["regions"])
    texte(fig, 0.07, 0.94, "MADAGASCAR · 2026", 11, BLEU, gras=True)
    texte(fig, 0.07, 0.905, f"{round(total / 1e6)} millions d'habitants.\nMais combien dans votre fokontany ?",
          24, gras=True, interligne=1.15)
    chiffre(fig, 0.07, 0.72, nb(len(communes)), "communes")
    chiffre(fig, 0.07, 0.6, nb(base["meta"]["nb_fokontany"]), "fokontany")
    chiffre(fig, 0.07, 0.48, "2015–2030", "population année par année", taille=22)
    legende(fig, 0.07, 0.2, RAMPE_BLEU, "< 10", "> 100 hab./km²")
    texte(fig, 0.07, 0.17, "Densité par commune, 2026", 8.5, GRIS)
    texte(fig, 0.07, 0.135, "Sources : RGPH-3 (INSTAT), WorldPop", 7.5, GRIS)
    bandeau(fig)
    fig.savefig(SORTIE / "post1_population_communes.png", dpi=DPI)
    plt.close(fig)


# ---------- Image du post 2 : la croissance par région ----------
def post_croissance():
    fig = page()
    regions = NIV["regions"]
    croiss = {i: 100 * (r["wp"][I30] / r["wp"][I26] - 1) for i, r in enumerate(regions)}
    seuils = [8, 10, 12, 13]
    formes = contours("regions")
    ax = carte(fig, [0.36, 0.07, 0.62, 0.72], formes, {i: RAMPE_ORANGE[classe(v, seuils)] for i, v in croiss.items()},
               bord="white", epaisseur=0.8)
    premieres = sorted(croiss, key=lambda i: -croiss[i])[:3]
    for i in premieres:
        a = max(formes[i], key=len)
        x, y = sum(p[0] for p in a) / len(a), sum(p[1] for p in a) / len(a)
        ax.text(x, y, f"{regions[i]['n']}\n+{croiss[i]:.1f} %".replace(".", ","), fontsize=8, ha="center", va="center",
                fontweight="bold", color=ENCRE, bbox=dict(boxstyle="round,pad=0.25", fc="white", ec="none", alpha=0.85))
    t26 = sum(r["wp"][I26] for r in regions)
    t30 = sum(r["wp"][I30] for r in regions)
    texte(fig, 0.07, 0.94, "PROJECTION 2026 → 2030", 11, "#c0650f", gras=True)
    texte(fig, 0.07, 0.905, f"+{(t30 - t26) / 1e6:.1f} millions d'habitants\nen quatre ans".replace(".", ","), 24, gras=True,
          interligne=1.15)
    texte(fig, 0.07, 0.74, "La croissance n'est pas la même partout. Les régions qui grandissent le plus vite :", 11, GRIS,
          largeur=34)
    for k, i in enumerate(premieres):
        chiffre(fig, 0.07, 0.62 - k * 0.12, f"+{croiss[i]:.1f} %".replace(".", ","), regions[i]["n"], couleur="#c0650f", taille=24)
    legende(fig, 0.07, 0.2, RAMPE_ORANGE, "< 8 %", "> 13 %")
    texte(fig, 0.07, 0.17, "Croissance de la population 2026-2030", 8.5, GRIS)
    texte(fig, 0.07, 0.135, "Source : projections WorldPop", 7.5, GRIS)
    bandeau(fig)
    fig.savefig(SORTIE / "post2_croissance_regions.png", dpi=DPI)
    plt.close(fig)


# ---------- Image du post 3 et carrousel : l'exemple d'Antsirabe II ----------
CHIFFRES = [("95\u202f138", "enfants de 0 à 59 mois ciblés"), ("226", "équipes sur 4 jours"),
            ("104\u202f727", "doses, perte comprise"), ("95", "fokontany à vérifier sur place")]


def image(fig, rect, fichier):
    ax = fig.add_axes(rect)
    ax.imshow(plt.imread(EXEMPLE / fichier))
    ax.axis("off")
    return ax


def post_antsirabe():
    fig = page()
    image(fig, [0.42, 0.07, 0.56, 0.78], "apercu_district.png")
    texte(fig, 0.07, 0.94, "EXEMPLE DE MICROPLANIFICATION", 11, BLEU, gras=True)
    texte(fig, 0.07, 0.905, "Vacciner les enfants\nd'un district :\ncombien d'équipes ?", 24, gras=True, interligne=1.15)
    for k, (v, l) in enumerate(CHIFFRES):
        chiffre(fig, 0.07, 0.66 - k * 0.12, v, l, taille=24)
    texte(fig, 0.07, 0.17, "District d'Antsirabe II · 20 communes · 204 fokontany\nExemple sur données publiques, normes indicatives",
          8, GRIS)
    bandeau(fig)
    fig.savefig(SORTIE / "post3_microplan_antsirabe.png", dpi=DPI)
    plt.close(fig)


def carrousel():
    n = 7
    with PdfPages(SORTIE / "carrousel_microplanification_Antsirabe_II.pdf") as pdf:
        def finir(fig, k, sombre=False):
            bandeau(fig, sombre, f"{k}/{n}")
            pdf.savefig(fig)
            plt.close(fig)

        # 1. Couverture
        fig = page(BLEU_FONCE)
        texte(fig, 0.08, 0.86, "MICROPLANIFICATION · EXEMPLE CONCRET", 11, "#9ec5f4", gras=True)
        texte(fig, 0.08, 0.81, "Combien d'équipes\npour vacciner\nles enfants\nd'un district ?", 34, "white", gras=True, interligne=1.1)
        texte(fig, 0.08, 0.43, "Le cas du district d'Antsirabe II,\nfokontany par fokontany.", 15, "#cde2fb")
        texte(fig, 0.08, 0.2, "Faites défiler →", 13, "white", gras=True)
        finir(fig, 1, sombre=True)

        # 2. Le problème
        fig = page(FOND)
        texte(fig, 0.08, 0.86, "LE PROBLÈME", 11, BLEU, gras=True)
        texte(fig, 0.08, 0.81, "Les dénombrements sont anciens.\nLes équipes sont réparties\nau jugé.", 24, gras=True, interligne=1.15)
        for k, s in enumerate(["Des zones sous-couvertes, d'autres où les équipes attendent.",
                               "Des doses commandées sans base fiable.",
                               "Des fokontany oubliés parce qu'ils sont loin."]):
            texte(fig, 0.08, 0.56 - k * 0.11, "—  " + s, 15, ENCRE, largeur=36)
        finir(fig, 2)

        # 3. La méthode
        fig = page()
        texte(fig, 0.08, 0.86, "LA MÉTHODE", 11, BLEU, gras=True)
        texte(fig, 0.08, 0.81, "4 étapes, des données publiques\njusqu'au plan des équipes", 22, gras=True, interligne=1.15)
        etapes = [("Estimer la population", "par fokontany : grille WorldPop de 100 m, calée sur le recensement"),
                  ("Calculer la cible", "enfants de 0 à 59 mois, doses avec taux de perte"),
                  ("Rattacher aux centres de santé", "le plus proche de chaque fokontany, avec la distance"),
                  ("Répartir les équipes", "grands fokontany découpés, petits regroupés, calendrier jour par jour")]
        for k, (t, d) in enumerate(etapes):
            y = 0.64 - k * 0.135
            fig.text(0.08, y, str(k + 1), fontsize=26, color=BLEU, fontweight="bold", va="top")
            texte(fig, 0.18, y, t, 15, gras=True)
            texte(fig, 0.18, y - 0.035, d, 11.5, GRIS, largeur=46)
        finir(fig, 3)

        # 4. Les chiffres
        fig = page(FOND)
        texte(fig, 0.08, 0.86, "LE RÉSULTAT", 11, BLEU, gras=True)
        texte(fig, 0.08, 0.81, "Antsirabe II en 4 chiffres", 24, gras=True)
        for k, (v, l) in enumerate(CHIFFRES):
            chiffre(fig, 0.08 + (k % 2) * 0.44, 0.66 - (k // 2) * 0.24, v, l, taille=34)
        texte(fig, 0.08, 0.2, "95 fokontany sur 204 : pour la même année 2018, le recensement réparti et l'estimation WorldPop "
                              "diffèrent de 30 % ou plus. Ils sont signalés pour être vérifiés avec les chefs fokontany.", 11.5, GRIS, largeur=58)
        finir(fig, 4)

        # 5. La carte du district
        fig = page()
        texte(fig, 0.08, 0.9, "LA CARTE DU DISTRICT", 11, BLEU, gras=True)
        texte(fig, 0.08, 0.865, "Où sont les enfants à vacciner ?", 20, gras=True)
        image(fig, [0.12, 0.13, 0.76, 0.68], "apercu_district.png")
        legende(fig, 0.08, 0.115, RAMPE_BLEU, "peu", "beaucoup d'enfants")
        fig.text(0.42, 0.115, "●", fontsize=11, color="#1baf7a", va="bottom")
        fig.text(0.45, 0.117, "centre de santé", fontsize=8.5, color=GRIS, va="bottom")
        fig.text(0.65, 0.115, "●", fontsize=11, color="#eda100", va="bottom")
        fig.text(0.68, 0.117, "poste de santé", fontsize=8.5, color=GRIS, va="bottom")
        finir(fig, 5)

        # 6. Ce que reçoit le client
        fig = page(FOND)
        texte(fig, 0.08, 0.86, "CE QUE VOUS RECEVEZ", 11, BLEU, gras=True)
        texte(fig, 0.08, 0.81, "Un rapport et un classeur\nprêts pour le terrain", 22, gras=True, interligne=1.15)
        image(fig, [0.52, 0.2, 0.42, 0.5], "apercu_commune.png")
        for k, (t, d) in enumerate([("Rapport de 35 pages", "une carte et un tableau par commune"),
                                    ("Classeur Excel", "communes, fokontany, 226 équipes"),
                                    ("Calendrier", "le programme jour par jour de chaque équipe")]):
            y = 0.64 - k * 0.14
            texte(fig, 0.08, y, t, 14, gras=True, largeur=30)
            texte(fig, 0.08, y - 0.034, d, 11, GRIS, largeur=26)
        texte(fig, 0.52, 0.19, "Page commune : fokontany numérotés\ndu plus au moins peuplé", 8.5, GRIS)
        finir(fig, 6)

        # 7. Appel à l'action
        fig = page(BLEU_FONCE)
        texte(fig, 0.08, 0.86, "ET POUR VOTRE CAMPAGNE ?", 11, "#9ec5f4", gras=True)
        texte(fig, 0.08, 0.81, "Le même travail,\navec vos normes\net vos sites.", 32, "white", gras=True, interligne=1.1)
        texte(fig, 0.08, 0.5, "L'exemple complet est téléchargeable gratuitement sur le site.\n"
                              "Pour un devis : formulaire du site ou message privé.", 13, "#cde2fb", largeur=44)
        fig.patches.append(FancyBboxPatch((0.08, 0.22), 0.84, 0.08, boxstyle="round,pad=0,rounding_size=0.02", fc="white",
                                          ec="none", transform=fig.transFigure, figure=fig))
        fig.text(0.5, 0.26, SITE, fontsize=14, color=BLEU_FONCE, fontweight="bold", ha="center", va="center")
        texte(fig, 0.08, 0.17, "Exemple de démonstration sur données publiques ; normes de campagne indicatives.", 8.5, "#9ec5f4")
        finir(fig, 7, sombre=True)


if __name__ == "__main__":
    post_population()
    post_croissance()
    post_antsirabe()
    carrousel()
    for f in sorted(SORTIE.iterdir()):
        print(f.name)
