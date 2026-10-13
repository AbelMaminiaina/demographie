"""Étape 3 : graphiques et rapport de synthèse."""
import io
from datetime import date

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.colors import BoundaryNorm, ListedColormap
from matplotlib.patches import Polygon
import pandas as pd
from PIL import Image

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
# Palette divergente (bleu <-> rouge, gris neutre au centre)
DIVERGENTE = ["#1c5cab", "#5598e7", "#b7d3f6", "#f0efec", "#f3b9b8", "#e46e6d", "#b92f2f"]
RAMPE_BLEUE = ["#cde2fb", "#9ec5f4", "#6da7ec", "#3987e5", "#256abf", "#184f95", "#0d366b"]

plt.rcParams.update({
    "figure.facecolor": FOND, "axes.facecolor": FOND, "savefig.facecolor": FOND,
    "text.color": ENCRE, "axes.labelcolor": ENCRE_2,
    "xtick.color": DISCRET, "ytick.color": DISCRET,
    "axes.edgecolor": GRILLE, "axes.spines.top": False, "axes.spines.right": False,
    "font.size": 10,
})


def _memes_pixels(chemin, tampon):
    with Image.open(chemin) as ancien, Image.open(tampon) as nouveau:
        return ancien.size == nouveau.size and ancien.convert("RGBA").tobytes() == nouveau.convert("RGBA").tobytes()


def _sauver(fig, nom):
    """Enregistre le graphique, sauf si l'image existante a exactement les mêmes pixels.

    La compression PNG diffère légèrement entre Windows et Linux : sans cette vérification,
    chaque exécution sur une autre machine produirait de faux changements dans git.
    """
    DOSSIER_SORTIES.mkdir(parents=True, exist_ok=True)
    chemin = DOSSIER_SORTIES / nom
    tampon = io.BytesIO()
    fig.savefig(tampon, format="png", dpi=150, bbox_inches="tight")
    plt.close(fig)
    tampon.seek(0)
    if chemin.exists() and _memes_pixels(chemin, tampon):
        print(f"  = sorties/{nom} (inchangé)")
        return chemin
    chemin.write_bytes(tampon.getvalue())
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
          source="Sources : estimations INSTAT/BNGRC 2018 (OCHA, HDX), contours geoBoundaries", couleurs=None):
    """Carte choroplèthe : `contours` et `valeurs` sont indexés par la même clé."""
    cmap = ListedColormap((couleurs or RAMPE_BLEUE)[:len(seuils) - 1])
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


def carte_regions(rgph_regions, contours):
    pop = rgph_regions.set_index("cle")["population"]
    seuils = [0, 400_000, 600_000, 800_000, 1_000_000, 1_400_000, 2_000_000, 5_000_000]
    return _carte(contours, pop, seuils, [f"{s / 1e6:.1f} M" for s in seuils[:-1]],
                  "Population", "Population par région, recensement de 2018", "carte_population_regions.png", 1,
                  source="Source : INSTAT, recensement RGPH-3 (2018), contours geoBoundaries")


def carte_densite(niveau, contours, densites, titre, epaisseur, source):
    etiquettes = [f"{s:,}".replace(",", " ") for s in SEUILS_DENSITE[:-1]]
    return _carte(contours, densites, SEUILS_DENSITE, etiquettes, "Habitants par km²", titre,
                  f"carte_densite_{niveau}.png", epaisseur, source=source)


def carte_ecart(rgph_districts, contours):
    """Écart entre l'estimation 2018 diffusée sur HDX et le recensement, par district."""
    seuils = [-100, -15, -7.5, -2.5, 2.5, 7.5, 15, 100]
    etiquettes = ["", "−15 %", "−7,5 %", "−2,5 %", "+2,5 %", "+7,5 %", "+15 %"]
    cmap_vals = rgph_districts.set_index("cle")["ecart_estimation_pct"]
    return _carte(contours, cmap_vals, seuils, etiquettes, "Estimation HDX par rapport au recensement",
                  "Écart entre l'estimation de 2018 et le recensement, par district",
                  "carte_ecart_estimation_districts.png", 0.4,
                  source="Sources : INSTAT/BNGRC via OCHA (HDX) et INSTAT, RGPH-3 (2018)", couleurs=DIVERGENTE)


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


AQUA = "#1baf7a"   # troisième série


def enquetes(pauvrete, emploi):
    """Pauvreté par enquête auprès des ménages, et structure de l'emploi par enquête nationale."""
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(11, 4.2), gridspec_kw={"width_ratios": [1.2, 1]})

    for colonne, couleur_serie, nom in (("pauvrete_3_00_dollars_pct", BLEU, "Moins de 3,00 $ par jour"),
                                        ("pauvrete_4_20_dollars_pct", ORANGE, "Moins de 4,20 $ par jour")):
        ax1.plot(pauvrete["annee"], pauvrete[colonne], color=couleur_serie, linewidth=2, marker="o", markersize=6,
                 markeredgecolor=FOND, markeredgewidth=2, label=nom)
        fin = pauvrete.iloc[-1]
        ax1.annotate(f"{fin[colonne]:.0f} %".replace(".", ","), (fin["annee"], fin[colonne]), xytext=(6, 0),
                     textcoords="offset points", va="center", color=ENCRE, fontweight="bold")
    ax1.set_ylim(0, 100)
    ax1.set_xlim(pauvrete["annee"].min() - 2, pauvrete["annee"].max() + 6)
    ax1.set_title("Population pauvre (%), par enquête", loc="left", fontsize=10)
    ax1.legend(frameon=False, loc="lower left")

    nationales = emploi[emploi["enquete"].str.match(r"ENEMPSI|ENESI|EPM 20(1[5-9]|2)")]
    series = (("taux_activite_pct", BLEU, "Taux d'activité"), ("emploi_informel_pct", ORANGE, "Emploi informel"),
              ("part_agriculture_pct", AQUA, "Emploi agricole"))
    largeur = 0.26
    for k, (colonne, couleur_serie, nom) in enumerate(series):
        x = [i + (k - 1) * largeur for i in range(len(nationales))]
        ax2.bar(x, nationales[colonne], width=largeur, color=couleur_serie, label=nom, edgecolor=FOND, linewidth=1)
    ax2.set_xticks(range(len(nationales)), nationales["enquete"])
    ax2.set_ylim(0, 115)
    ax2.set_yticks(range(0, 101, 25))
    for i, rupture in enumerate(nationales["rupture_de_serie"]):
        if rupture and nationales.iloc[i]["annee"] > nationales["annee"].min():
            ax2.annotate("méthode révisée", (i, 103), ha="center", fontsize=8, color=ENCRE_2)
    ax2.set_title("Emploi (% des 15 ans et plus ou des actifs occupés)", loc="left", fontsize=10)
    ax2.legend(frameon=False, loc="upper left", bbox_to_anchor=(0, -0.08), ncol=3)
    for ax in (ax1, ax2):
        ax.grid(axis="y", color=GRILLE, linewidth=0.6)
        ax.set_axisbelow(True)
    fig.suptitle("Pauvreté et emploi d'après les enquêtes auprès des ménages", x=0.01, ha="left", fontweight="bold")
    fig.text(0.01, -0.07, "Sources : Banque mondiale, Poverty and Inequality Platform (EPM ; seuils en dollars PPA 2021) ; "
             "OIT, ILOSTAT (ENEMPSI 2012, ENESI 2015, EPM 2022)", color=DISCRET, fontsize=8)
    fig.tight_layout()
    return _sauver(fig, "enquetes_pauvrete_emploi.png")


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
        "## Recensement RGPH-3 de 2018 par région", "",
        "Population résidente recensée par l'INSTAT (résultats globaux, décembre 2020). La dernière colonne "
        "compare l'estimation 2018 diffusée sur HDX, calculée à partir des données de 2009, au recensement.", "",
        "| Région | Population | Part | Urbaine | Hommes pour 100 femmes | Densité (hab/km²) "
        "| Estimation HDX | Écart |", "|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    rg = donnees["rgph3"]
    reg = rg["regions"].sort_values("population", ascending=False)
    for _, r in reg.iterrows():
        lignes.append(f"| {r['nom']} | {nombre(r['population'])} | {r['population'] / reg['population'].sum():.1%} "
                      f"| {r['part_urbaine_pct']:.1f} % | {r['rapport_masculinite']:.1f} | {nombre(r['densite_officielle'])} "
                      f"| {nombre(r['estimation_hdx_2018'])} | {r['ecart_estimation_pct']:+.1f} % |")
    lignes.append(f"| **Madagascar** | **{nombre(reg['population'].sum())}** | 100 % "
                  f"| {100 * reg['urbain'].sum() / reg['population'].sum():.1f} % "
                  f"| {100 * reg['hommes'].sum() / reg['femmes'].sum():.1f} | | "
                  f"{nombre(reg['estimation_hdx_2018'].sum())} "
                  f"| {100 * (reg['estimation_hdx_2018'].sum() / reg['population'].sum() - 1):+.1f} % |")

    def tableau(titre, df, colonnes):
        lignes.extend(["", f"### {titre}", "",
                       "| " + " | ".join(colonnes.values()) + " | Population | Densité (hab/km²) |",
                       "|" + "---|" * len(colonnes) + "---:|---:|"])
        for _, r in df.iterrows():
            lignes.append("| " + " | ".join(str(r[c]) for c in colonnes)
                          + f" | {nombre(r['population'])} | {nombre(r['densite'])} |")

    dist = niveaux["districts"]["unites"]
    dist = rg["districts"].sort_values("population", ascending=False)
    lignes += ["", f"## Districts ({annee}, recensement RGPH-3)", "",
               "Antananarivo Renivohitra est détaillé par arrondissement. Tableau complet : "
               "`data/traite/recensement/rgph3_districts.csv`."]
    colonnes = {"nom": "District", "region": "Région"}
    tableau("Les 10 plus peuplés", dist.head(10), colonnes)
    tableau("Les 10 plus denses", dist.nlargest(10, "densite"), colonnes)
    ecarts = dist.reindex(dist["ecart_estimation_pct"].abs().sort_values(ascending=False).index).head(10)
    lignes += ["", "### Les 10 plus grands écarts entre estimation HDX et recensement", "",
               "| District | Région | Recensement | Estimation HDX | Écart |", "|---|---|---:|---:|---:|"]
    for _, r in ecarts.iterrows():
        lignes.append(f"| {r['nom']} | {r['region']} | {nombre(r['population'])} | "
                      f"{nombre(r['estimation_hdx_2018'])} | {r['ecart_estimation_pct']:+.1f} % |")

    dist = niveaux["districts"]["unites"]
    lignes += ["", f"## Districts ({annee}, estimations INSTAT/BNGRC diffusées sur HDX)", "",
               "Antananarivo Renivohitra est découpé en ses 6 arrondissements. "
               "Tableau complet : `data/traite/territoires/districts.csv`."]
    colonnes = {"nom": "District", "region": "Région"}
    tableau("Les 10 plus peuplés", dist.head(10), colonnes)
    tableau("Les 10 plus denses", dist.nlargest(10, "densite"), colonnes)

    rc = rg["communes"]
    reliees = rc["correspondance"].value_counts()
    lignes += ["", f"## Communes au recensement RGPH-3 ({len(rc)} communes et arrondissements)", "",
               f"Le recensement compte {len(rc)} communes, contre {len(niveaux['communes']['unites'])} dans le "
               f"découpage HDX utilisé pour les cartes. {reliees.get('exacte', 0)} communes sont reliées par leur nom, "
               f"{reliees.get('approchée', 0)} par un nom proche (variante d'orthographe) et "
               f"{reliees.get('aucune', 0)} n'ont pas de correspondance, le plus souvent parce qu'elles ont été "
               f"créées depuis. Tableau complet : `data/traite/recensement/rgph3_communes.csv`.", "",
               "### Les 10 plus peuplées", "",
               "| Commune | District | Population | Urbaine |", "|---|---|---:|---:|"]
    for _, r in rc.nlargest(10, "population").iterrows():
        lignes.append(f"| {r['nom']} | {r['district_rgph']} | {nombre(r['population'])} | {r['part_urbaine_pct']:.0f} % |")

    com = niveaux["communes"]["unites"]
    lignes += ["", f"## Communes ({annee}, estimations INSTAT/BNGRC diffusées sur HDX)"]
    classes = (com.groupby(pd.cut(com["densite"], SEUILS_DENSITE, right=False), observed=False)
               .agg(communes=("pcode", "size"), population=("population", "sum")))
    lignes += ["",
               f"Population médiane : {nombre(com['population'].median())} habitants. "
               "Tableau complet : `data/traite/territoires/communes.csv`.", "",
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
               "Tableau complet : `data/traite/territoires/fokontany.csv`."]
    colonnes = {"nom": "Fokontany", "commune": "Commune", "district": "District"}
    tableau("Les 10 plus peuplés", fk.head(10), colonnes)

    cales = donnees["fokontany_cales"]
    ok = cales.dropna(subset=["population_calee"])
    lignes += ["", "## Fokontany : estimation 2018 calée sur le recensement", "",
               "Le RGPH-3 n'est pas publié par fokontany. Pour chaque commune reliée au recensement, sa population "
               "recensée est répartie entre ses fokontany au prorata de leur poids dans l'estimation HDX. Les totaux "
               "communaux sont donc exacts, mais la répartition entre fokontany reste celle des données de 2009. "
               "Tableau complet : `data/traite/recensement/fokontany_estimation_calee_rgph3.csv`.", "",
               f"- {nombre(len(ok))} fokontany sur {nombre(len(cales))} sont calés, soit "
               f"{nombre(ok['population_calee'].sum())} habitants ({ok['population_calee'].sum() / rg['regions']['population'].sum():.1%} "
               "de la population recensée).",
               f"- {nombre(len(cales) - len(ok))} fokontany ne le sont pas : leur commune n'a pas d'équivalent dans le recensement.",
               f"- {nombre((ok['decoupage_identique'] == True).sum())} fokontany calés sont dans un district dont le découpage "
               "communal est identique dans les deux sources ; pour les autres, la commune du recensement peut ne pas "
               "couvrir exactement le même territoire.",
               f"- Population médiane d'un fokontany calé : {nombre(ok['population_calee'].median())} habitants.", "",
               "### Les 10 plus peuplés (estimation calée)", "",
               "| Fokontany | Commune | District | Estimation calée | Estimation HDX |", "|---|---|---|---:|---:|"]
    for _, r in ok.nlargest(10, "population_calee").iterrows():
        lignes.append(f"| {r['nom']} | {r['commune']} | {r['district']} | {nombre(r['population_calee'])} "
                      f"| {nombre(r['estimation_hdx_2018'])} |")

    # WorldPop 100 m par fokontany
    wp100 = donnees["worldpop_100m"]
    annees_100m = sorted(int(c.split("_")[1]) for c in wp100.columns if c.startswith("wp100_"))
    an = min(annee_courante, annees_100m[-1])
    wp100 = wp100.assign(croissance=((wp100[f"wp100_{an}"] / wp100["wp100_2018"].clip(lower=1)) ** (1 / (an - 2018)) - 1) * 100)
    lignes += ["", f"## Fokontany : estimations WorldPop à 100 m ({annees_100m[0]}-{annees_100m[-1]})", "",
               "Grilles WorldPop à 100 m (R2025A), sommées par fokontany : chaque carré de 100 m est affecté au "
               "fokontany qui contient son centre. Ce sont des estimations modélisées, à utiliser avec prudence pour "
               "les petits fokontany. Tableau complet : `data/traite/estimations/worldpop_100m_fokontany.csv`.", "",
               f"- Population estimée en {an} : {nombre(wp100[f'wp100_{an}'].sum())} habitants ; "
               f"médiane par fokontany : {nombre(wp100[f'wp100_{an}'].median())}.",
               f"- En 2030 : {nombre(wp100['wp100_2030'].sum())} habitants.",
               f"- {(wp100[f'wp100_{an}'] == 0).sum()} fokontany, trop petits pour contenir le centre d'un carré de 100 m, ont 0 habitant.", "",
               f"### Les 10 plus peuplés en {an}", "",
               f"| Fokontany | Commune | District | 2018 | {an} | 2030 | Croissance 2018-{an} |",
               "|---|---|---|---:|---:|---:|---:|"]
    for _, r in wp100.nlargest(10, f"wp100_{an}").iterrows():
        lignes.append(f"| {r['nom']} | {r['commune']} | {r['district']} | {nombre(r['wp100_2018'])} | "
                      f"{nombre(r[f'wp100_{an}'])} | {nombre(r['wp100_2030'])} | {r['croissance']:+.1f} %/an |")

    # Pauvreté (EPM) et emploi (ENEMPSI, ENESI, EPM)
    pauv = donnees["pauvrete"]
    lignes += ["", "## Pauvreté d'après les enquêtes auprès des ménages", "",
               "Estimations de la Banque mondiale (Poverty and Inequality Platform) calculées sur la consommation "
               "mesurée par les enquêtes de l'INSTAT. Seuils internationaux en dollars par jour et par personne, "
               "en parité de pouvoir d'achat 2021. Tableau complet : `data/traite/enquetes/pauvrete_epm.csv`.", "",
               "| Année | Enquête | Moins de 3,00 $ | Moins de 4,20 $ | Moins de 8,30 $ | Indice de Gini |",
               "|---|---|---:|---:|---:|---:|"]
    for _, r in pauv.iterrows():
        lignes.append(f"| {r['annee']} | {r['enquete']} | {r['pauvrete_3_00_dollars_pct']:.1f} % | "
                      f"{r['pauvrete_4_20_dollars_pct']:.1f} % | {r['pauvrete_8_30_dollars_pct']:.1f} % | {r['gini']:.3f} |")
    emp = donnees["emploi"]
    nationales = emp[emp["enquete"].str.match(r"ENEMPSI|ENESI|EPM 20(1[5-9]|2)")]

    def pct(v):
        return "–" if v != v or v is None else f"{v:.1f} %"

    lignes += ["", "## Emploi d'après les enquêtes nationales", "",
               "Indicateurs calculés par l'OIT à partir des microdonnées des enquêtes de l'INSTAT, pour les 15 ans et plus. "
               "**L'OIT signale une rupture de série pour l'EPM 2022 (méthode révisée)** : le passage aux normes "
               "internationales de 2013, qui ne comptent plus la production pour sa propre consommation comme un emploi, "
               "explique probablement la baisse du taux d'activité et la hausse de la part des salariés. Les chiffres de "
               "2022 ne sont donc pas directement comparables à ceux de 2012 et 2015. "
               "Tableaux complets : `data/traite/enquetes/emploi_synthese.csv` et `emploi_oit.csv`.", "",
               "| Enquête | Activité | Emploi | Chômage | Emploi informel | Emploi agricole | Salariés | Jeunes NEET | Actifs occupés |",
               "|---|---:|---:|---:|---:|---:|---:|---:|---:|"]
    for _, r in nationales.iterrows():
        total = "–" if r["emploi_total_milliers"] != r["emploi_total_milliers"] else f"{nombre(r['emploi_total_milliers'] * 1000)}"
        lignes.append(f"| {r['enquete']}{' (rupture)' if r['rupture_de_serie'] and r['annee'] > nationales['annee'].min() else ''} "
                      f"| {pct(r['taux_activite_pct'])} | {pct(r['taux_emploi_pct'])} | {pct(r['taux_chomage_pct'])} "
                      f"| {pct(r['emploi_informel_pct'])} | {pct(r['part_agriculture_pct'])} | {pct(r['part_salaries_pct'])} "
                      f"| {pct(r['jeunes_neet_pct'])} | {total} |")
    lignes += ["", "Jeunes NEET : jeunes ni en emploi, ni en études, ni en formation."]

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
               "Tableau complet : `data/traite/sante/dhs_regions.csv`.", "",
               "| Région | " + " | ".join(noms.values()) + " |", "|---|" + "---:|" * len(noms)]
    for _, r in dhs.sort_values("fecondite_isf", ascending=False).iterrows():
        lignes.append(f"| {r['nom']} | " + " | ".join(f"{r[c]:g}".replace(".", ",") for c in noms) + " |")

    # WorldPop
    wp = donnees["worldpop"]
    large = wp["regions"].pivot(index="cle", columns="annee", values="population")
    croissance = croissance_worldpop(wp["regions"], annee, annee_courante)
    lignes += ["", f"## Estimations WorldPop par région ({annee}-2030)", "",
               "Estimations modélisées sur une grille de 1 km (images satellite, bâti), ajustées aux "
               "totaux nationaux de l'ONU. Elles complètent les estimations officielles de 2018 pour les années "
               "récentes, avec une incertitude plus forte à l'échelle des communes. Tableaux complets : "
               "`data/traite/estimations/worldpop_*.csv`.", "",
               f"| Région | INSTAT {annee} | WorldPop {annee} | WorldPop {annee_courante} | WorldPop 2030 "
               f"| Croissance {annee}-{annee_courante} |", "|---|---:|---:|---:|---:|---:|"]
    for _, r in reg.iterrows():
        lignes.append(f"| {r['nom']} | {nombre(r['population'])} | {nombre(large.loc[r['cle'], annee])} "
                      f"| {nombre(large.loc[r['cle'], annee_courante])} | {nombre(large.loc[r['cle'], 2030])} "
                      f"| {croissance[r['cle']]:.1f} %/an |")

    lignes += ["", "![Pyramide des âges](pyramide_ages.png)", "",
               "![Carte des régions](carte_population_regions.png)", "",
               "![Carte des districts](carte_densite_districts.png)", "",
               "![Écart estimation / recensement](carte_ecart_estimation_districts.png)", "",
               "![Carte des communes](carte_densite_communes.png)", "",
               "![Fécondité par région](carte_fecondite_regions.png)", "",
               "![Croissance par district](carte_croissance_districts.png)", "",
               "![Tendances](tendances.png)", "",
               "![Projections](projections.png)", "",
               "![Pauvreté et emploi](enquetes_pauvrete_emploi.png)", ""]
    chemin = DOSSIER_SORTIES / "rapport.md"
    chemin.write_text("\n".join(lignes), encoding="utf-8")
    print("  -> sorties/rapport.md")
    return chemin


def tout_visualiser(donnees):
    niveaux = donnees["niveaux"]
    annee = niveaux["regions"]["population"]["annee"].max()
    annee_courante = min(date.today().year, int(donnees["worldpop"]["regions"]["annee"].max()))
    pyramide_ages(donnees["pyramide"])
    rg = donnees["rgph3"]
    carte_regions(rg["regions"], niveaux["regions"]["contours"])
    carte_densite("districts", niveaux["districts"]["contours"], rg["districts"].set_index("cle")["densite"],
                  "Densité de population par district, recensement de 2018", 0.4, "Source : INSTAT, recensement RGPH-3 (2018), contours geoBoundaries")
    carte_densite("communes", niveaux["communes"]["contours"], niveaux["communes"]["unites"].set_index("cle")["densite"],
                  f"Densité de population par commune, estimation {annee}", 0.1,
                  "Source : estimations INSTAT/BNGRC 2018 (OCHA, HDX), contours geoBoundaries")
    carte_ecart(rg["districts"], niveaux["districts"]["contours"])
    carte_fecondite(donnees["dhs"], niveaux["regions"]["contours"])
    carte_croissance(donnees["worldpop"]["districts"], niveaux["districts"]["contours"], annee, annee_courante)
    tendances(donnees["series"])
    projections(donnees["series"], donnees["projections"])
    enquetes(donnees["pauvrete"], donnees["emploi"])
    rapport(donnees, annee, annee_courante)
