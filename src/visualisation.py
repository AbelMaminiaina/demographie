"""Étape 3 : graphiques et rapport de synthèse."""
import json

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.colors import BoundaryNorm, ListedColormap
from matplotlib.patches import Polygon

from config import DOSSIER_BRUT, DOSSIER_SORTIES
from nettoyage import cle_region

# Palette de référence (thème clair)
FOND = "#fcfcfb"
ENCRE = "#0b0b0b"
ENCRE_2 = "#52514e"
DISCRET = "#898781"
GRILLE = "#e1e0d9"
BLEU = "#2a78d6"     # hommes / série unique
ORANGE = "#eb6834"   # femmes
RAMPE_BLEUE = ["#cde2fb", "#9ec5f4", "#6da7ec", "#3987e5", "#256abf", "#184f95", "#0d366b"]

plt.rcParams.update({
    "figure.facecolor": FOND, "axes.facecolor": FOND, "savefig.facecolor": FOND,
    "text.color": ENCRE, "axes.labelcolor": ENCRE_2,
    "xtick.color": DISCRET, "ytick.color": DISCRET,
    "axes.edgecolor": GRILLE, "axes.spines.top": False, "axes.spines.right": False,
    "font.size": 10,
})


def _sauver(fig, nom):
    DOSSIER_SORTIES.mkdir(parents=True, exist_ok=True)
    chemin = DOSSIER_SORTIES / nom
    fig.savefig(chemin, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"  -> sorties/{nom}")
    return chemin


def pyramide_ages(pyramide):
    annee = pyramide["annee"].max()
    df = pyramide[pyramide["annee"] == annee].pivot(index="groupe_age", columns="sexe", values="effectif")
    df = df.loc[sorted(df.index, key=lambda g: int(g.split("-")[0].rstrip("+")))] / 1e6
    y = range(len(df))

    fig, ax = plt.subplots(figsize=(8, 6))
    ax.barh(y, -df["H"], height=0.85, color=BLEU, label="Hommes", edgecolor=FOND, linewidth=1)
    ax.barh(y, df["F"], height=0.85, color=ORANGE, label="Femmes", edgecolor=FOND, linewidth=1)
    ax.set_yticks(list(y), df.index)
    lim = df.max().max() * 1.15
    ax.set_xlim(-lim, lim)
    ax.xaxis.set_major_formatter(lambda v, _: f"{abs(v):.1f}")
    ax.set_xlabel("Effectif (millions)")
    ax.axvline(0, color="#c3c2b7", linewidth=1)
    ax.grid(axis="x", color=GRILLE, linewidth=0.6)
    ax.set_axisbelow(True)
    ax.text(-lim * 0.95, len(df) - 1, "Hommes", color=ENCRE_2, va="center", fontweight="bold")
    ax.text(lim * 0.95, len(df) - 1, "Femmes", color=ENCRE_2, va="center", ha="right", fontweight="bold")
    ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.1), ncol=2, frameon=False)
    ax.set_title(f"Pyramide des âges de Madagascar, {annee}", loc="left", fontweight="bold")
    fig.text(0.01, -0.07, "Source : Banque mondiale (WDI), estimations ONU", color=DISCRET, fontsize=8)
    return _sauver(fig, "pyramide_ages.png")


def _anneaux(geometrie):
    polys = geometrie["coordinates"] if geometrie["type"] == "MultiPolygon" else [geometrie["coordinates"]]
    return [poly[0] for poly in polys]  # contour extérieur uniquement


def carte_regions(regions):
    annee = regions["annee"].max()
    pop = regions[regions["annee"] == annee].set_index("cle")
    with open(DOSSIER_BRUT / "regions.geojson", encoding="utf-8") as f:
        geo = json.load(f)

    seuils = [0, 400_000, 600_000, 800_000, 1_000_000, 1_400_000, 2_000_000, 5_000_000]
    cmap = ListedColormap(RAMPE_BLEUE)
    norm = BoundaryNorm(seuils, cmap.N)

    fig, ax = plt.subplots(figsize=(7, 9))
    manquantes = []
    for feat in geo["features"]:
        cle = cle_region(feat["properties"]["shapeName"])
        if cle not in pop.index:
            manquantes.append(feat["properties"]["shapeName"])
            continue
        couleur = cmap(norm(pop.loc[cle, "population"]))
        for anneau in _anneaux(feat["geometry"]):
            ax.add_patch(Polygon(anneau, facecolor=couleur, edgecolor=FOND, linewidth=1))
    if manquantes:
        raise ValueError(f"Régions sans correspondance : {manquantes}")

    ax.autoscale_view()
    ax.set_aspect("equal")
    ax.axis("off")
    sm = plt.cm.ScalarMappable(cmap=cmap, norm=norm)
    cb = fig.colorbar(sm, ax=ax, shrink=0.5, pad=0.02, ticks=seuils[:-1])
    cb.ax.set_yticklabels([f"{s / 1e6:.1f} M" for s in seuils[:-1]])
    cb.outline.set_visible(False)
    cb.set_label("Population")
    ax.set_title(f"Population par région, {annee}", loc="left", fontweight="bold")
    fig.text(0.05, 0.06, "Sources : INSTAT / OCHA (HDX), contours geoBoundaries", color=DISCRET, fontsize=8)
    return _sauver(fig, "carte_population_regions.png")


def tendances(series):
    panneaux = [
        ("population", "Population (millions)", 1e6),
        ("fecondite_isf", "Enfants par femme (ISF)", 1),
        ("esperance_vie", "Espérance de vie (années)", 1),
        ("urbanisation_pct", "Population urbaine (%)", 1),
    ]
    fig, axes = plt.subplots(2, 2, figsize=(10, 6.5))
    for ax, (col, titre, div) in zip(axes.flat, panneaux):
        s = series[col].dropna() / div
        ax.plot(s.index, s.values, color=BLEU, linewidth=2)
        ax.plot(s.index[-1], s.values[-1], "o", color=BLEU, markersize=6,
                markeredgecolor=FOND, markeredgewidth=2)
        ax.annotate(f"{s.values[-1]:.1f} ({s.index[-1]})", (s.index[-1], s.values[-1]),
                    xytext=(-10, 10), textcoords="offset points", ha="right", color=ENCRE,
                    fontweight="bold", bbox={"facecolor": FOND, "edgecolor": "none", "pad": 1})
        ax.set_title(titre, loc="left", fontsize=10, color=ENCRE)
        ax.grid(axis="y", color=GRILLE, linewidth=0.6)
        ax.set_axisbelow(True)
    fig.suptitle("Évolution démographique de Madagascar", x=0.01, ha="left", fontweight="bold")
    fig.text(0.01, -0.01, "Source : Banque mondiale (WDI)", color=DISCRET, fontsize=8)
    fig.tight_layout()
    return _sauver(fig, "tendances.png")


def rapport(series, regions):
    annee_reg = regions["annee"].max()
    reg = regions[regions["annee"] == annee_reg].sort_values("population", ascending=False)

    def val(col, fmt):
        """Dernière valeur disponible de l'indicateur, avec son année."""
        s = series[col].dropna()
        return "n.d. | – " if s.empty else f"{fmt.format(s.iloc[-1])} | {s.index[-1]}"

    lignes = [
        "# Synthèse démographique de Madagascar", "",
        "## Indicateurs nationaux (dernière valeur disponible)", "",
        "| Indicateur | Valeur | Année |", "|---|---|---|",
        f"| Population | {val('population', '{:,.0f}').replace(',', ' ')} |",
        f"| Croissance annuelle | {val('croissance_pct', '{:.2f} %')} |",
        f"| Indice synthétique de fécondité | {val('fecondite_isf', '{:.2f}')} |",
        f"| Natalité | {val('natalite_pour_mille', '{:.1f} ‰')} |",
        f"| Mortalité | {val('mortalite_pour_mille', '{:.1f} ‰')} |",
        f"| Mortalité infantile | {val('mortalite_infantile_pour_mille', '{:.1f} ‰')} |",
        f"| Espérance de vie | {val('esperance_vie', '{:.1f} ans')} |",
        f"| Population urbaine | {val('urbanisation_pct', '{:.1f} %')} |",
        f"| Ratio de dépendance | {val('ratio_dependance', '{:.1f}')} |", "",
        f"## Population par région ({annee_reg}, RGPH-3)", "",
        "| Région | Population | Part |", "|---|---:|---:|",
    ]
    total = reg["population"].sum()
    for _, r in reg.iterrows():
        lignes.append(f"| {r['region']} | {r['population']:,.0f} | {r['population'] / total:.1%} |"
                      .replace(",", " "))
    lignes += ["", "![Pyramide des âges](pyramide_ages.png)", "",
               "![Carte](carte_population_regions.png)", "", "![Tendances](tendances.png)", ""]
    chemin = DOSSIER_SORTIES / "rapport.md"
    chemin.write_text("\n".join(lignes), encoding="utf-8")
    print("  -> sorties/rapport.md")
    return chemin


def tout_visualiser(series, pyramide, regions):
    pyramide_ages(pyramide)
    carte_regions(regions)
    tendances(series)
    rapport(series, regions)
