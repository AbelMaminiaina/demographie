"""Étape 3 : graphiques et rapport de synthèse."""
from datetime import date

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.colors import BoundaryNorm, ListedColormap
from matplotlib.patches import Polygon
import pandas as pd

from config import DOSSIER_SORTIES
from geometrie import anneaux

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


SEUILS_DENSITE = [0, 10, 25, 50, 100, 250, 1_000, 1e9]


def _carte(contours, valeurs, seuils, etiquettes, legende, titre, fichier, epaisseur,
          source="Sources : INSTAT / OCHA (HDX), contours geoBoundaries"):
    """Carte choroplèthe : `contours` et `valeurs` sont indexés par la même clé."""
    cmap = ListedColormap(RAMPE_BLEUE[:len(seuils) - 1])
    norm = BoundaryNorm(seuils, cmap.N)

    fig, ax = plt.subplots(figsize=(7, 9))
    for cle, geometrie in contours.items():
        couleur = cmap(norm(valeurs[cle]))
        for anneau in anneaux(geometrie):
            ax.add_patch(Polygon([p[:2] for p in anneau], facecolor=couleur,
                                 edgecolor=FOND, linewidth=epaisseur))
    ax.autoscale_view()
    ax.set_aspect("equal")
    ax.axis("off")
    sm = plt.cm.ScalarMappable(cmap=cmap, norm=norm)
    cb = fig.colorbar(sm, ax=ax, shrink=0.5, pad=0.02, ticks=seuils[:-1])
    cb.ax.set_yticklabels(etiquettes)
    cb.outline.set_visible(False)
    cb.set_label(legende)
    ax.set_title(titre, loc="left", fontweight="bold")
    fig.text(0.05, 0.06, source, color=DISCRET, fontsize=8)
    return _sauver(fig, fichier)


def carte_regions(donnees, annee):
    pop = donnees["unites"].set_index("cle")["population"]
    seuils = [0, 400_000, 600_000, 800_000, 1_000_000, 1_400_000, 2_000_000, 5_000_000]
    return _carte(donnees["contours"], pop, seuils, [f"{s / 1e6:.1f} M" for s in seuils[:-1]],
                  "Population", f"Population par région, {annee}", "carte_population_regions.png", 1)


def carte_densite(niveau, donnees, annee, epaisseur):
    etiquettes = [f"{s:,}".replace(",", " ") for s in SEUILS_DENSITE[:-1]]
    titre = {"districts": "district", "communes": "commune"}[niveau]
    return _carte(donnees["contours"], donnees["unites"].set_index("cle")["densite"], SEUILS_DENSITE,
                  etiquettes, "Habitants par km²", f"Densité de population par {titre}, {annee}",
                  f"carte_densite_{niveau}.png", epaisseur)


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


def projections(series, proj):
    """Population observée puis projetée (ONU), et structure par âge."""
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(10, 4))
    observee = series["population"].dropna() / 1e6
    futur = proj.loc[proj.index >= observee.index.max(), "population"] / 1e6
    ax1.plot(observee.index, observee.values, color=BLEU, linewidth=2, label="Estimations")
    ax1.plot(futur.index, futur.values, color=BLEU, linewidth=2, linestyle=(0, (4, 3)), label="Projection ONU")
    for annee in (observee.index.max(), futur.index.max()):
        v = (observee if annee in observee.index else futur)[annee]
        ax1.plot(annee, v, "o", color=BLEU, markersize=6, markeredgecolor=FOND, markeredgewidth=2)
        ax1.annotate(f"{v:.1f} M ({annee})", (annee, v), xytext=(-10, 10), textcoords="offset points",
                     ha="right", fontweight="bold", bbox={"facecolor": FOND, "edgecolor": "none", "pad": 1})
    ax1.set_title("Population (millions)", loc="left", fontsize=10)
    ax1.legend(frameon=False, loc="upper left")

    for col, couleur, nom in (("part_0_14_pct", BLEU, "0-14 ans"), ("part_65_plus_pct", ORANGE, "65 ans et plus")):
        v = proj[col].dropna()
        ax2.plot(v.index, v.values, color=couleur, linewidth=2, label=nom)
        ax2.annotate(f"{nom} : {v.iloc[-1]:.0f} %", (v.index[-1], v.iloc[-1]), xytext=(-4, 8),
                     textcoords="offset points", ha="right", color=ENCRE_2)
    ax2.axvline(observee.index.max(), color=GRILLE, linewidth=1)
    ax2.set_ylim(0, None)
    ax2.set_title("Part de la population (%)", loc="left", fontsize=10)
    ax2.legend(frameon=False, loc="center left")
    for ax in (ax1, ax2):
        ax.grid(axis="y", color=GRILLE, linewidth=0.6)
        ax.set_axisbelow(True)
    fig.suptitle("Projections démographiques jusqu'en 2050", x=0.01, ha="left", fontweight="bold")
    fig.text(0.01, -0.03, "Source : ONU, World Population Prospects (via Banque mondiale)",
             color=DISCRET, fontsize=8)
    fig.tight_layout()
    return _sauver(fig, "projections.png")


def carte_fecondite(dhs, contours):
    seuils = [0, 3, 3.5, 4, 4.5, 5, 6, 10]
    return _carte(contours, dhs.set_index("cle")["fecondite_isf"], seuils,
                  [f"{s:g}".replace(".", ",") for s in seuils[:-1]], "Enfants par femme",
                  f"Indice synthétique de fécondité par région ({dhs.attrs['enquete']})",
                  "carte_fecondite_regions.png", 1, source="Source : enquête DHS, contours geoBoundaries")


def croissance_worldpop(estimations, debut, fin):
    """Croissance annuelle moyenne entre deux années, par unité."""
    large = estimations.pivot(index="cle", columns="annee", values="population")
    return ((large[fin] / large[debut]) ** (1 / (fin - debut)) - 1) * 100


def carte_croissance(estimations, contours, debut, fin):
    seuils = [-100, 0, 1, 2, 2.5, 3, 4, 100]
    etiquettes = ["< 0"] + [f"{s:g}".replace(".", ",") for s in seuils[1:-1]]
    return _carte(contours, croissance_worldpop(estimations, debut, fin), seuils, etiquettes,
                  "% par an", f"Croissance démographique estimée par district, {debut}-{fin}",
                  "carte_croissance_districts.png", 0.4,
                  source="Source : estimations WorldPop (grille 1 km), contours geoBoundaries")


def rapport(donnees, annee, annee_courante):
    series, niveaux = donnees["series"], donnees["niveaux"]
    def val(col, fmt):
        """Dernière valeur disponible de l'indicateur, avec son année."""
        v = series[col].dropna()
        return "n.d. | – " if v.empty else f"{fmt.format(v.iloc[-1])} | {v.index[-1]}"

    def nombre(x):
        return f"{x:,.0f}".replace(",", " ")

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
        f"## Population par région ({annee}, RGPH-3)", "",
        "| Région | Population | Part | Densité (hab/km²) |", "|---|---:|---:|---:|",
    ]
    reg = niveaux["regions"]["unites"]
    for _, r in reg.iterrows():
        lignes.append(f"| {r['nom']} | {nombre(r['population'])} | "
                      f"{r['population'] / reg['population'].sum():.1%} | {nombre(r['densite'])} |")

    def tableau(titre, df, colonnes):
        lignes.extend(["", f"### {titre}", "",
                       "| " + " | ".join(colonnes.values()) + " | Population | Densité (hab/km²) |",
                       "|" + "---|" * len(colonnes) + "---:|---:|"])
        for _, r in df.iterrows():
            lignes.append("| " + " | ".join(str(r[c]) for c in colonnes)
                          + f" | {nombre(r['population'])} | {nombre(r['densite'])} |")

    dist = niveaux["districts"]["unites"]
    lignes += ["", f"## Districts ({annee}, {len(dist)} districts)", "",
               "Antananarivo Renivohitra est découpé en ses 6 arrondissements. "
               "Tableau complet : `data/traite/districts.csv`."]
    colonnes = {"nom": "District", "region": "Région"}
    tableau("Les 10 plus peuplés", dist.head(10), colonnes)
    tableau("Les 10 plus denses", dist.nlargest(10, "densite"), colonnes)

    com = niveaux["communes"]["unites"]
    classes = (com.groupby(pd.cut(com["densite"], SEUILS_DENSITE, right=False), observed=False)
               .agg(communes=("pcode", "size"), population=("population", "sum")))
    lignes += ["", f"## Communes ({annee}, {len(com)} communes)", "",
               f"Population médiane : {nombre(com['population'].median())} habitants. "
               "Tableau complet : `data/traite/communes.csv`.", "",
               "### Répartition par densité", "",
               "| Habitants par km² | Communes | Population | Part de la population |",
               "|---|---:|---:|---:|"]
    for intervalle, r in classes.iterrows():
        borne = (f"{nombre(intervalle.left)} et plus" if intervalle.right > 1e8
                 else f"{nombre(intervalle.left)} à {nombre(intervalle.right)}")
        lignes.append(f"| {borne} | {r['communes']} | {nombre(r['population'])} "
                      f"| {r['population'] / com['population'].sum():.1%} |")
    colonnes = {"nom": "Commune", "district": "District", "region": "Région"}
    tableau("Les 10 plus peuplées", com.head(10), colonnes)
    tableau("Les 10 plus denses", com.nlargest(10, "densite"), colonnes)
    tableau("Les 10 moins denses", com.nsmallest(10, "densite"), colonnes)

    fk = niveaux["fokontany"]["unites"]
    lignes += ["", f"## Fokontany ({annee}, {len(fk)} fokontany)", "",
               f"Population médiane : {nombre(fk['population'].median())} habitants ; "
               f"{(fk['population'] < 500).sum()} fokontany comptent moins de 500 habitants. "
               "Tableau complet : `data/traite/fokontany.csv`."]
    colonnes = {"nom": "Fokontany", "commune": "Commune", "district": "District"}
    tableau("Les 10 plus peuplés", fk.head(10), colonnes)

    # Projections ONU
    proj = donnees["projections"]
    lignes += ["", "## Projections de l'ONU", "",
               "| Année | Population | 0-14 ans | 65 ans et plus |", "|---|---:|---:|---:|"]
    for a in (annee_courante, 2030, 2040, 2050):
        if a in proj.index:
            r = proj.loc[a]
            lignes.append(f"| {a} | {nombre(r['population'])} | {r['part_0_14_pct']:.1f} % "
                          f"| {r['part_65_plus_pct']:.1f} % |")

    # Enquête DHS
    dhs = donnees["dhs"]
    noms = {"fecondite_isf": "ISF", "mortalite_infantile_pour_mille": "Mortalité infantile (‰)",
            "contraception_moderne_pct": "Contraception moderne (%)",
            "accouchement_etablissement_pct": "Accouchement en établissement (%)",
            "retard_croissance_pct": "Retard de croissance (%)",
            "alphabetisation_femmes_pct": "Femmes alphabétisées (%)"}
    noms = {c: n for c, n in noms.items() if c in dhs}
    lignes += ["", f"## Santé et fécondité par région ({dhs.attrs['enquete']})", "",
               "Mortalité infantile : décès avant 1 an pour 1 000 naissances (10 ans précédant l'enquête). "
               "Tableau complet : `data/traite/dhs_regions.csv`.", "",
               "| Région | " + " | ".join(noms.values()) + " |", "|---|" + "---:|" * len(noms)]
    for _, r in dhs.sort_values("fecondite_isf", ascending=False).iterrows():
        lignes.append(f"| {r['nom']} | " + " | ".join(f"{r[c]:g}".replace(".", ",") for c in noms) + " |")

    # WorldPop
    wp = donnees["worldpop"]
    large = wp["regions"].pivot(index="cle", columns="annee", values="population")
    croissance = croissance_worldpop(wp["regions"], annee, annee_courante)
    lignes += ["", f"## Estimations WorldPop par région ({annee}-2030)", "",
               "Estimations modélisées sur une grille de 1 km (images satellite, bâti), ajustées aux "
               "totaux nationaux de l'ONU. Elles complètent le recensement de 2018 pour les années "
               "récentes, avec une incertitude plus forte à l'échelle des communes. Tableaux complets : "
               "`data/traite/worldpop_*.csv`.", "",
               f"| Région | RGPH {annee} | WorldPop {annee} | WorldPop {annee_courante} | WorldPop 2030 "
               f"| Croissance {annee}-{annee_courante} |", "|---|---:|---:|---:|---:|---:|"]
    for _, r in reg.iterrows():
        lignes.append(f"| {r['nom']} | {nombre(r['population'])} | {nombre(large.loc[r['cle'], annee])} "
                      f"| {nombre(large.loc[r['cle'], annee_courante])} | {nombre(large.loc[r['cle'], 2030])} "
                      f"| {croissance[r['cle']]:.1f} %/an |")

    lignes += ["", "![Pyramide des âges](pyramide_ages.png)", "",
               "![Carte des régions](carte_population_regions.png)", "",
               "![Carte des districts](carte_densite_districts.png)", "",
               "![Carte des communes](carte_densite_communes.png)", "",
               "![Fécondité par région](carte_fecondite_regions.png)", "",
               "![Croissance par district](carte_croissance_districts.png)", "",
               "![Tendances](tendances.png)", "",
               "![Projections](projections.png)", ""]
    chemin = DOSSIER_SORTIES / "rapport.md"
    chemin.write_text("\n".join(lignes), encoding="utf-8")
    print("  -> sorties/rapport.md")
    return chemin


def tout_visualiser(donnees):
    niveaux = donnees["niveaux"]
    annee = niveaux["regions"]["population"]["annee"].max()
    annee_courante = min(date.today().year, int(donnees["worldpop"]["regions"]["annee"].max()))
    pyramide_ages(donnees["pyramide"])
    carte_regions(niveaux["regions"], annee)
    carte_densite("districts", niveaux["districts"], annee, epaisseur=0.4)
    carte_densite("communes", niveaux["communes"], annee, epaisseur=0.1)
    carte_fecondite(donnees["dhs"], niveaux["regions"]["contours"])
    carte_croissance(donnees["worldpop"]["districts"], niveaux["districts"]["contours"], annee, annee_courante)
    tendances(donnees["series"])
    projections(donnees["series"], donnees["projections"])
    rapport(donnees, annee, annee_courante)
