# Automatisations – Données démographiques de Madagascar

Pipeline qui télécharge, nettoie et visualise les données démographiques de Madagascar.

## Tableau de bord interactif

**https://abelmaminiaina.github.io/demographie/**

Une carte de Madagascar à trois niveaux (régions, districts, communes) avec 12 indicateurs : population, densité, estimations et croissance WorldPop année par année, et indicateurs de santé DHS. Le tableau de bord propose aussi :

- une recherche jusqu'au fokontany ;
- une fiche par lieu (évolution 2015-2030, indicateurs DHS de la région, liste des fokontany d'une commune) ;
- la population de 1960 à 2050 ;
- une pyramide des âges année par année ;
- un classement triable.

La page est un fichier HTML autonome (`sorties/tableau_de_bord/index.html`), régénéré par le pipeline et republié chaque mois sur GitHub Pages. Elle s'ouvre aussi directement depuis le disque.

**Activation (une seule fois) :** dans **Settings**, puis **Pages**, choisir **Source : GitHub Actions**.

## Aperçu

![Évolution démographique de Madagascar](sorties/tendances.png)

| Population par région | Densité par district |
|---|---|
| ![Population par région](sorties/carte_population_regions.png) | ![Densité par district](sorties/carte_densite_districts.png) |

| Densité par commune | Pyramide des âges |
|---|---|
| ![Densité par commune](sorties/carte_densite_communes.png) | ![Pyramide des âges](sorties/pyramide_ages.png) |

| Fécondité par région (DHS) | Croissance estimée par district (WorldPop) |
|---|---|
| ![Fécondité par région](sorties/carte_fecondite_regions.png) | ![Croissance par district](sorties/carte_croissance_districts.png) |

![Projections jusqu'en 2050](sorties/projections.png)

Les graphiques sont régénérés à chaque exécution du pipeline.

## Installation

```bash
pip install -r requirements.txt
```

## Utilisation

```bash
python src/pipeline.py                  # collecte + nettoyage + graphiques
python src/pipeline.py --sans-collecte  # réutilise les données déjà téléchargées
```

## Étapes

| Étape | Module | Sorties |
|---|---|---|
| 1. Collecte | `src/collecte.py` | `data/brut/` |
| 2. Nettoyage et contrôles qualité | `src/nettoyage.py` | `data/traite/*.csv` |
| 3. Graphiques et rapport | `src/visualisation.py` | `sorties/` |
| 4. Tableau de bord | `src/tableau_de_bord.py`, `src/modele_tableau_de_bord.html` | `sorties/tableau_de_bord/` |

## Sources

| Source | Contenu | Accès |
|---|---|---|
| **Banque mondiale** (WDI + Santé/Population) | Séries nationales depuis 1960, effectifs par âge et sexe | API publique |
| **ONU, World Population Prospects** | Projections jusqu'en 2050 (population, structure par âge) | Via la Banque mondiale (base 40) : l'API de l'ONU exige un jeton |
| **HDX / OCHA** (`cod-ps-mdg`) | Population 2018 (RGPH-3) des 22 régions, 119 districts, 1 579 communes et 17 465 fokontany | API CKAN |
| **geoBoundaries** | Contours des quatre niveaux, qui servent aussi au calcul des superficies et des densités | API publique |
| **DHS Program** | Dernière enquête (2021) par région : fécondité, mortalité infantile, contraception, accouchements, malnutrition, alphabétisation | API publique, sans clé |
| **WorldPop** (R2025A) | Estimations annuelles 2015-2030 sur grille de 1 km, agrégées par commune, district et région | API publique |

Les années 2009-2017 des fichiers HDX ne sont pas des observations : elles sont rétropolées depuis 2018 avec un taux national unique (2,72 %/an). Pour l'évolution récente par territoire, il faut utiliser les estimations WorldPop. Ce sont des modèles, moins fiables à l'échelle d'une commune qu'à celle d'un district ou d'une région.

**INSTAT** (instat.mg) n'est pas collecté automatiquement. En octobre 2026, sa page d'accueil contenait des liens cachés vers des sites de jeux d'argent, signe d'une compromission du site. Un script ne doit pas suivre ces liens.

## Harmonisation des noms

Les sources écrivent les noms différemment (« Haute Matsiatra » / « Matsiatra Ambony », « Amoron I Mania » / « Amoron'i Mania »).
`nettoyage.cle_nom()` normalise les noms en gardant les chiffres, ce qui distingue « 2e Arrondissement » de « 3e Arrondissement ». Une nouvelle variante s'ajoute dans `ALIAS_NOMS`.

Beaucoup de communes portent le même nom dans des districts différents, et les contours geoBoundaries n'indiquent pas le district. `nettoyage.rattacher_contours()` le retrouve en cherchant le district qui contient un point intérieur de chaque commune (`src/geometrie.py`), puis relie la commune par le couple (district, nom).

Les fokontany sont rattachés à leur commune de la même façon. Deux fokontany homonymes d'une même commune ne peuvent pas être distingués dans les contours. Ils sont donc fusionnés, et leurs P-codes sont joints par `|`.

Le pipeline s'arrête si une unité reste sans contour, si la somme d'un niveau ne redonne pas la population du niveau supérieur, si une région DHS n'est pas reconnue, ou si le total WorldPop s'écarte de plus de 5 % du total de l'ONU.

Les sources régionales utilisent encore le découpage en 22 régions, où Vatovavy-Fitovinany forme une seule région. La séparation en Vatovavy et Fitovinany (2021) n'y apparaît pas encore.

## Exécution automatique

Le workflow `.github/workflows/mise-a-jour-mensuelle.yml` exécute le pipeline le 1er de chaque mois :

- les graphiques sont recommités seulement s'ils ont changé ;
- chaque requête est retentée jusqu'à 5 fois en cas de coupure réseau ;
- les données et le rapport complet sont téléchargeables 90 jours dans l'onglet **Actions** (artefact `donnees-…`) ;
- un échec (source indisponible, contrôle qualité échoué) déclenche un email de GitHub.

Lancement manuel : onglet **Actions**, puis **Mise à jour mensuelle**, puis **Run workflow**.

## Pistes suivantes

- Extraction des tableaux PDF de l'INSTAT, une fois son site sécurisé.
- Base de données (DuckDB/PostgreSQL) pour interroger les séries.
