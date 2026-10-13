# Automatisations – Données démographiques de Madagascar

Pipeline qui télécharge, nettoie et visualise les données démographiques de Madagascar.

## Aperçu

![Évolution démographique de Madagascar](sorties/tendances.png)

| Population par région | Densité par district |
|---|---|
| ![Population par région](sorties/carte_population_regions.png) | ![Densité par district](sorties/carte_densite_districts.png) |

| Densité par commune | Pyramide des âges |
|---|---|
| ![Densité par commune](sorties/carte_densite_communes.png) | ![Pyramide des âges](sorties/pyramide_ages.png) |

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

## Sources

- **Banque mondiale** (API WDI + Santé/Population) : séries nationales depuis 1960 et effectifs par âge et sexe.
- **HDX / OCHA** (`cod-ps-mdg`) : population par région (22), par district (119, dont les 6 arrondissements d'Antananarivo) et par commune (1 579) d'après le RGPH-3 de 2018.
- **geoBoundaries** : contours simplifiés des régions, des districts et des communes. Ils servent aussi au calcul des superficies et des densités.

Les années 2009-2017 des fichiers HDX ne sont pas des observations : elles sont rétropolées depuis 2018 avec un taux national unique (2,72 %/an). Elles ne permettent donc pas de comparer la croissance entre régions ou districts.

## Harmonisation des noms

Les sources écrivent les noms différemment (« Haute Matsiatra » / « Matsiatra Ambony », « Amoron I Mania » / « Amoron'i Mania »).
`nettoyage.cle_nom()` normalise les noms en gardant les chiffres, ce qui distingue « 2e Arrondissement » de « 3e Arrondissement ». Une nouvelle variante s'ajoute dans `ALIAS_NOMS`.

Beaucoup de communes portent le même nom dans des districts différents, et les contours geoBoundaries n'indiquent pas le district. `nettoyage.rattacher_contours()` le retrouve en cherchant le district qui contient un point intérieur de chaque commune (`src/geometrie.py`), puis relie la commune par le couple (district, nom).

Le pipeline s'arrête si une commune reste sans contour, ou si la somme des communes ne redonne pas la population de leur district.

Les sources régionales utilisent encore le découpage en 22 régions, où Vatovavy-Fitovinany forme une seule région. La séparation en Vatovavy et Fitovinany (2021) n'y apparaît pas encore.

## Exécution automatique

Le workflow `.github/workflows/mise-a-jour-mensuelle.yml` exécute le pipeline le 1er de chaque mois :

- les graphiques sont recommités seulement s'ils ont changé ;
- les données et le rapport complet sont téléchargeables 90 jours dans l'onglet **Actions** (artefact `donnees-…`) ;
- un échec (source indisponible, contrôle qualité échoué) déclenche un email de GitHub.

Lancement manuel : onglet **Actions**, puis **Mise à jour mensuelle**, puis **Run workflow**.

## Pistes suivantes

- Données par fokontany (ADM4, déjà disponibles sur HDX).
- Extraction des tableaux PDF de l'INSTAT.
- Base de données (DuckDB/PostgreSQL) et tableau de bord interactif.
