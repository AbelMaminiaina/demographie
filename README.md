# Automatisations – Données démographiques de Madagascar

Pipeline qui télécharge, nettoie et visualise les données démographiques de Madagascar.

## Aperçu

![Évolution démographique de Madagascar](sorties/tendances.png)

| Pyramide des âges | Population par région |
|---|---|
| ![Pyramide des âges](sorties/pyramide_ages.png) | ![Population par région](sorties/carte_population_regions.png) |

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
- **HDX / OCHA** (`cod-ps-mdg`) : population par région 2009-2018, d'après les projections INSTAT et le RGPH-3.
- **geoBoundaries** : contours simplifiés des 22 régions.

## Harmonisation des noms de régions

Les sources écrivent les noms différemment (« Haute Matsiatra » / « Matsiatra Ambony », « Amoron I Mania » / « Amoron'i Mania »).
`nettoyage.cle_region()` normalise les noms. Une nouvelle variante s'ajoute dans `ALIAS_REGIONS`.

Les sources régionales utilisent encore le découpage en 22 régions, où Vatovavy-Fitovinany forme une seule région. La séparation en Vatovavy et Fitovinany (2021) n'y apparaît pas encore.

## Exécution automatique

Le workflow `.github/workflows/mise-a-jour-mensuelle.yml` exécute le pipeline le 1er de chaque mois :

- les graphiques sont recommités seulement s'ils ont changé ;
- les données et le rapport complet sont téléchargeables 90 jours dans l'onglet **Actions** (artefact `donnees-…`) ;
- un échec (source indisponible, contrôle qualité échoué) déclenche un email de GitHub.

Lancement manuel : onglet **Actions**, puis **Mise à jour mensuelle**, puis **Run workflow**.

## Pistes suivantes

- Données par district et par commune (ADM2 à ADM4, déjà disponibles sur HDX).
- Extraction des tableaux PDF de l'INSTAT.
- Base de données (DuckDB/PostgreSQL) et tableau de bord interactif.
