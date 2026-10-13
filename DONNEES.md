# Catalogue des données

Ce document indique d'où vient chaque donnée du projet, sous quelle licence elle est diffusée, comment elle est traitée et où elle est rangée.

Les fichiers de `data/` ne sont pas versionnés dans git : ils sont recréés par `python src/pipeline.py`. Le workflow mensuel les archive aussi pendant 90 jours dans l'onglet **Actions** (artefact `donnees-…`).

## Vue d'ensemble

| Source | Producteur | Diffuseur | Contenu | Période | Découpage | Licence |
|---|---|---|---|---|---|---|
| [Indicateurs du développement](#banque-mondiale--indicateurs-nationaux) | ONU (WPP), offices statistiques, Banque mondiale | Banque mondiale | Population, fécondité, mortalité, espérance de vie, urbanisation, effectifs par âge et sexe | 1960-2025 | Pays | CC BY 4.0 |
| [Projections de population](#onu--projections-de-population) | Division de la population de l'ONU (World Population Prospects) | Banque mondiale (base 40) | Population et structure par âge projetées | 1960-2050 | Pays | CC BY 3.0 IGO (ONU) |
| [Recensement RGPH-3](#instat--recensement-rgph-3-2018) | INSTAT | UNFPA Madagascar (copie du PDF officiel) | Population recensée par sexe et milieu (urbain, rural) | 2018 | Régions, districts, communes | Publication officielle, citation obligatoire |
| [Population par unité administrative](#instat--population-par-unité-administrative-2009-2018) | INSTAT et BNGRC | OCHA, sur HDX (`cod-ps-mdg`) | Population des régions, districts, communes et fokontany | 2009-2018 | Régions à fokontany | CC BY 3.0 IGO |
| [Contours administratifs](#geoboundaries--contours-administratifs) | OpenStreetMap (régions) ; BNGRC et OCHA (districts à fokontany) | geoBoundaries (William & Mary) | Limites des 4 niveaux | 2017 (régions), 2020 (autres) | Régions à fokontany | ODbL 1.0 (régions) ; CC BY 3.0 IGO (autres) |
| [Enquête démographique et de santé](#dhs--enquête-démographique-et-de-santé-2021) | INSTAT, avec l'appui d'ICF (programme DHS) | API du programme DHS | 8 indicateurs de santé et de fécondité | 2021 | Régions | Données agrégées publiques, citation obligatoire |
| [Grilles de population](#worldpop--estimations-sur-grille-de-1-km) | WorldPop (université de Southampton) | WorldPop Hub | Habitants par carré de 1 km et de 100 m | 2015-2030 | Grilles, agrégées aux fokontany (100 m) et aux communes, districts et régions (1 km) | CC BY 4.0 |

## Fiches par source

### Banque mondiale : indicateurs nationaux

- **Producteurs :** la Banque mondiale compile les séries à partir des estimations de l'ONU (World Population Prospects) et des offices statistiques nationaux. Les effectifs par âge et sexe sont des estimations de la Banque mondiale fondées sur les répartitions de l'ONU.
- **Bases interrogées :** World Development Indicators (WDI, base 2) et Health Nutrition and Population Statistics (HNP, base 16).
- **Accès :** API publique `https://api.worldbank.org/v2/country/MDG/indicator/<code>`, sans clé.
- **Licence :** Creative Commons Attribution 4.0.
- **Fichier brut :** `data/brut/banque_mondiale/indicateurs_nationaux.json`.

| Code | Indicateur | Colonne |
|---|---|---|
| `SP.POP.TOTL` | Population totale (milieu d'année, résidents de fait) | `population` |
| `SP.POP.GROW` | Croissance annuelle de la population (%) | `croissance_pct` |
| `SP.DYN.TFRT.IN` | Indice synthétique de fécondité (enfants par femme) | `fecondite_isf` |
| `SP.DYN.CBRT.IN` | Taux brut de natalité (‰) | `natalite_pour_mille` |
| `SP.DYN.CDRT.IN` | Taux brut de mortalité (‰) | `mortalite_pour_mille` |
| `SP.DYN.IMRT.IN` | Mortalité infantile (décès avant 1 an pour 1 000 naissances) | `mortalite_infantile_pour_mille` |
| `SP.DYN.LE00.IN` | Espérance de vie à la naissance (années) | `esperance_vie` |
| `SP.URB.TOTL.IN.ZS` | Population urbaine (% du total) | `urbanisation_pct` |
| `SP.POP.DPND` | Rapport de dépendance (moins de 15 ans et 65 ans et plus pour 100 personnes de 15-64 ans) | `ratio_dependance` |
| `SP.POP.0004.FE` … `SP.POP.80UP.MA` | Effectifs par groupe d'âge de 5 ans et par sexe (34 séries) | `pyramide_ages.csv` |

Les dernières années manquent parfois : la Banque mondiale publie certains indicateurs avec un ou deux ans de retard.

### ONU : projections de population

- **Producteur :** Division de la population des Nations unies, *World Population Prospects* (dernière révision reprise par la Banque mondiale).
- **Diffuseur :** base 40 de la Banque mondiale, « Population estimates and projections ». L'API de l'ONU (`population.un.org/dataportalapi`) exige un jeton d'accès ; la Banque mondiale republie les mêmes séries sans jeton.
- **Contenu :** population totale (`SP.POP.TOTL`), part des 0-14 ans (`SP.POP.0014.TO.ZS`) et des 65 ans et plus (`SP.POP.65UP.TO.ZS`), de 1960 à 2050. Après la dernière année observée, ce sont des projections.
- **Licence :** Creative Commons Attribution 3.0 IGO (conditions de l'ONU pour les World Population Prospects).
- **Fichier brut :** `data/brut/onu_wpp/projections_population.json`.

### INSTAT : recensement RGPH-3 (2018)

- **Producteur :** Institut national de la statistique (INSTAT), Commission centrale de l'enquête et du recensement (CCER).
- **Publication :** « Résultats globaux du recensement général de la population et de l'habitation de 2018 de Madagascar (RGPH-3) », tome 2, décembre 2020 (226 pages).
- **Accès :** copie du PDF hébergée par l'UNFPA Madagascar, `https://madagascar.unfpa.org/sites/default/files/pub-pdf/resultat_globaux_rgph3_tome_02.pdf`. Le PNUD en héberge une autre copie. Le site de l'INSTAT, qui publie aussi ce document, est écarté (voir plus bas).
- **Conditions :** publication officielle ; toute réutilisation doit citer l'INSTAT.
- **Fichier brut :** `data/brut/instat_rgph3/resultats_globaux_tome2.pdf`.
- **Tableaux extraits** (`src/rgph3.py`) :
  - tableau 8 : population résidente par sexe, poids démographique, rapport de masculinité, part des femmes et densité, pour les 22 régions et 114 districts ;
  - tableau 10 : population par milieu (urbain, rural) et par sexe, pour les 1 727 communes et arrondissements.
- **Contrôles de l'extraction :**
  - le total national lu doit être 25 674 196 ;
  - les districts des deux tableaux doivent concorder un à un ;
  - chaque district doit être la somme de ses communes ;
  - urbain + rural doit égaler le total sur chaque ligne ;
  - les totaux régionaux recalculés doivent égaler ceux publiés.

  Les totaux urbain (4 942 902) et rural (20 731 294) obtenus sont ceux publiés par l'INSTAT.
- **Correspondance avec les autres sources :**
  - les 114 districts du recensement couvrent exactement les 119 districts HDX. Antananarivo Renivohitra y est détaillé par ses 6 arrondissements, et « Toliara-I » correspond à « Toliary-I » ;
  - les communes sont reliées par leur nom dans chaque district : 1 474 exactement, 39 par un nom proche (variantes d'orthographe) et 214 sans correspondance. Le recensement compte 1 727 communes contre 1 579 dans le découpage HDX ; les communes créées depuis n'ont pas de contour ;
  - dans 99 districts sur 114, le découpage communal diffère. Le chiffre d'une commune reliée peut alors ne pas couvrir exactement le territoire dessiné (colonne `decoupage_identique`).
- **Fokontany :** le recensement n'est pas publié par fokontany (les tomes 1 et 2 s'arrêtent à la commune). Le projet produit donc une **estimation calée** :
  - la population recensée de chaque commune reliée est répartie entre ses fokontany, au prorata de leur poids dans l'estimation HDX ;
  - les arrondis suivent la méthode du plus fort reste, si bien que la somme des fokontany redonne exactement le total de la commune ;
  - 16 651 fokontany sur 17 464 sont calés (23,3 millions d'habitants, 90,8 % de la population recensée). Les 813 autres appartiennent à des communes HDX sans équivalent dans le recensement ;
  - c'est une estimation : la répartition entre les fokontany d'une même commune reste celle des données de 2009.
- **Différence avec les estimations HDX :** au niveau national, l'estimation 2018 diffusée sur HDX dépasse le recensement de 4,0 %. Les écarts vont de −34 % (Morombe) à +47 % (Besalampy) selon les districts.

### INSTAT : population par unité administrative (2009-2018)

- **Producteurs :** Institut national de la statistique (INSTAT) et Bureau national de gestion des risques et des catastrophes (BNGRC).
- **Diffuseur :** OCHA, bureau régional Afrique australe et orientale, jeu de données HDX [`cod-ps-mdg`](https://data.humdata.org/dataset/cod-ps-mdg) (« Madagascar - Subnational Population Statistics », mis à jour le 26 août 2022).
- **Contenu :** population totale par région (22), district (119, dont les 6 arrondissements d'Antananarivo), commune (1 579) et fokontany (17 465), de 2009 à 2018. Les P-codes (`MG11`, `MG11101`…) servent d'identifiants.
- **Licence :** Creative Commons Attribution 3.0 IGO.
- **Fichiers bruts :** `data/brut/instat_hdx/population_adm1_2018.csv` à `population_adm4_2018.csv`.

> **Ce ne sont pas les résultats du recensement de 2018.** HDX donne comme source « INSTAT / BNGRC 2009 population data » et signale que les valeurs de 2010 à 2018 sont obtenues par un calcul de croissance. Toutes les unités suivent le même taux, 2,72 % par an. Le total 2018 de ces fichiers (26,7 millions) dépasse d'environ un million celui du recensement RGPH-3 réalisé la même année (environ 25,7 millions). Les écarts entre territoires reflètent donc la répartition de 2009.

Particularités relevées :
- Deux fokontany de même nom dans une même commune ne peuvent pas être distingués sur les contours. Ils sont fusionnés, et leurs deux P-codes sont joints par `|`. On compte donc 17 464 lignes pour 17 465 fokontany.
- Le fichier regroupe certains quartiers urbains en une seule ligne, par exemple « Tsiroanomandidy Ville (16 fokontany) ».
- Le découpage date d'avant 2021 : Vatovavy et Fitovinany y forment encore une seule région.

### geoBoundaries : contours administratifs

- **Diffuseur :** [geoBoundaries](https://www.geoboundaries.org) (William & Mary, laboratoire geoLab), jeu `gbOpen`, version du 12 décembre 2023, contours simplifiés.
- **Producteurs et licences :**

| Niveau | Producteur | Année représentée | Licence |
|---|---|---|---|
| Régions (ADM1) | OpenStreetMap (extraction Wambacher) | 2017 | Open Data Commons Open Database License 1.0 |
| Districts (ADM2) | BNGRC et OCHA | 2020 | CC BY 3.0 IGO |
| Communes (ADM3) | BNGRC et OCHA | 2020 | CC BY 3.0 IGO |
| Fokontany (ADM4) | BNGRC et OCHA | 2020 | CC BY 3.0 IGO |

- **Fichiers bruts :** `data/brut/geoboundaries/contours_regions.geojson`, `contours_districts.geojson`, `contours_communes.geojson`, `contours_fokontany.geojson`.
- **Limite :** les contours ne portent pas de P-code ni d'unité parente. Le rattachement se fait par le nom et par la position (voir [Traitements](#traitements)).

### DHS : enquête démographique et de santé 2021

- **Producteur :** INSTAT, avec l'appui technique d'ICF dans le cadre du programme DHS (financement USAID).
- **Enquête :** `MD2021DHS`, collecte de mars à juillet 2021, rapport publié en août 2022. Le pipeline prend automatiquement la dernière enquête DHS disponible.
- **Accès :** API publique `https://api.dhsprogram.com/rest/dhs/data`, sans clé. Seuls les indicateurs agrégés sont utilisés ; les données individuelles demandent une inscription au programme DHS.
- **Conditions :** données agrégées publiques ; toute réutilisation doit citer la source (ICF, The DHS Program).
- **Fichier brut :** `data/brut/dhs/indicateurs_regions.json`.

| Code DHS | Indicateur | Colonne |
|---|---|---|
| `FE_FRTR_W_TFR` | Indice synthétique de fécondité, femmes de 15-49 ans | `fecondite_isf` |
| `FE_AAFB_W_M2B` | Âge médian à la première naissance, femmes de 25-49 ans | `age_median_premiere_naissance` |
| `FP_CUSM_W_MOD` | Femmes en union utilisant une méthode contraceptive moderne (%) | `contraception_moderne_pct` |
| `RH_DELP_C_DHF` | Naissances dans un établissement de santé (%, 2 ans précédant l'enquête) | `accouchement_etablissement_pct` |
| `CM_ECMR_C_IMR` | Mortalité infantile (‰, 10 ans précédant l'enquête) | `mortalite_infantile_pour_mille` |
| `CM_ECMR_C_U5M` | Mortalité avant 5 ans (‰, 10 ans précédant l'enquête) | `mortalite_moins_5_ans_pour_mille` |
| `CN_NUTS_C_HA2` | Enfants de moins de 5 ans présentant un retard de croissance (%) | `retard_croissance_pct` |
| `ED_LITR_W_LIT` | Femmes alphabétisées (%) | `alphabetisation_femmes_pct` |

Quand l'API donne plusieurs périodes de référence pour un même indicateur, seule la valeur marquée « préférée » (`IsPreferred = 1`) est gardée.

### WorldPop : estimations sur grilles de 1 km et de 100 m

- **Producteur :** WorldPop, université de Southampton, projet Global Demographic Data (financement Fondation Bill & Melinda Gates).
- **Jeu :** « Constrained estimates of 2015-2030 total number of people per grid square », version R2025A v1, résolution de 30 secondes d'arc (environ 1 km), ajusté aux totaux de l'ONU. DOI [10.5258/SOTON/WP00840](https://doi.org/10.5258/SOTON/WP00840).
- **Méthode :** la population est répartie entre les carrés de la grille par une forêt aléatoire, à partir d'images satellite et de la carte du bâti. « Constrained » signifie que seuls les carrés bâtis reçoivent des habitants.
- **Avertissement du producteur :** R2025A est une version alpha, susceptible d'évoluer.
- **Licence :** Creative Commons Attribution 4.0.
- **Fichiers bruts :** `data/brut/worldpop/population_<année>_1km.tif`, de 2015 à 2030 (GeoTIFF, WGS84).
- **Version à 100 m :** même modèle à une résolution de 3 secondes d'arc (environ 100 m), DOI [10.5258/SOTON/WP00839](https://doi.org/10.5258/SOTON/WP00839).
  - Fichiers : `data/brut/worldpop_100m/population_<année>_100m.tif`, de 2015 à 2030 (environ 55 Mo par année, 16 388 × 8 757 pixels).
  - Ses totaux nationaux sont identiques à ceux de la grille à 1 km.
  - Elle est sommée par fokontany : chaque carré est affecté au fokontany qui contient son centre. 0,08 % de la population tombe hors des contours (littoral).
  - 2 fokontany, plus petits qu'un carré de 100 m, ne reçoivent aucun habitant.
- **Fiabilité :** bonne par région ou par district, plus faible par commune. Pour 2018, le rapport WorldPop / INSTAT varie de 0,2 à 6 selon les communes, alors que la médiane est proche de 1.

### Source écartée : site de l'INSTAT

Le site [instat.mg](https://www.instat.mg) publie les résultats du RGPH-3 en PDF. En octobre 2026, sa page d'accueil contenait des dizaines de liens cachés vers des sites de jeux d'argent, signe d'une compromission. Il n'est pas collecté automatiquement, parce qu'un script ne doit pas suivre ces liens. Le même document officiel est récupéré depuis la copie de l'UNFPA Madagascar.

## Classement des fichiers

Les chemins sont définis à un seul endroit : `BRUT` et `TRAITE` dans `src/config.py`.

```
data/
├── brut/                               Fichiers tels que téléchargés, un dossier par source
│   ├── journal_collecte.json           Trace de chaque téléchargement (voir ci-dessous)
│   ├── banque_mondiale/
│   │   └── indicateurs_nationaux.json
│   ├── onu_wpp/
│   │   └── projections_population.json
│   ├── instat_rgph3/
│   │   └── resultats_globaux_tome2.pdf
│   ├── instat_hdx/
│   │   └── population_adm1_2018.csv … population_adm4_2018.csv
│   ├── geoboundaries/
│   │   └── contours_regions.geojson … contours_fokontany.geojson
│   ├── dhs/
│   │   └── indicateurs_regions.json
│   ├── worldpop/
│   │   └── population_2015_1km.tif … population_2030_1km.tif
│   └── worldpop_100m/
│       └── population_2015_100m.tif … population_2030_100m.tif
└── traite/                             Fichiers CSV prêts à l'emploi, un dossier par thème
    ├── national/                       Séries pour l'ensemble du pays
    │   ├── indicateurs_annuels.csv
    │   ├── pyramide_ages.csv
    │   └── projections_onu.csv
    ├── recensement/                    Résultats du RGPH-3 (2018)
    │   ├── rgph3_regions.csv, rgph3_districts.csv, rgph3_communes.csv
    │   └── fokontany_estimation_calee_rgph3.csv
    ├── territoires/                    Estimations HDX : population et densité par unité administrative
    │   ├── regions.csv, districts.csv, communes.csv, fokontany.csv
    │   └── <niveau>_series_2009_2018.csv
    ├── sante/
    │   └── dhs_regions.csv
    └── estimations/
        ├── worldpop_regions.csv, worldpop_districts.csv, worldpop_communes.csv
        └── worldpop_100m_fokontany.csv

sorties/                                Résultats publiés
├── *.png                               Graphiques (versionnés, affichés dans le README)
├── rapport.md                          Rapport de synthèse
└── tableau_de_bord/index.html          Tableau de bord interactif (publié sur GitHub Pages)
```

### Journal de collecte

`data/brut/journal_collecte.json` indique les heures de début et de fin de la collecte. Pour chaque fichier, il donne :

| Champ | Contenu |
|---|---|
| `fichier` | Chemin dans `data/brut/` |
| `source` | Producteur, jeu de données et, pour les contours, licence |
| `url` | Adresse exacte du téléchargement |
| `date` | Date et heure du téléchargement (UTC) |
| `octets` | Taille du fichier |
| `sha256` | Empreinte du fichier, pour vérifier qu'il n'a pas changé d'une collecte à l'autre |

## Dictionnaire des données traitées

Tous les fichiers sont en CSV, encodés en UTF-8, avec le point comme séparateur décimal. `pcode` est le code administratif officiel (OCHA/INSTAT).

### `national/indicateurs_annuels.csv`
Une ligne par année (1960-2025). Colonnes : `annee` et les 9 indicateurs du [tableau Banque mondiale](#banque-mondiale--indicateurs-nationaux). Une case vide signifie que la valeur n'est pas encore publiée.

### `national/pyramide_ages.csv`
Une ligne par année, groupe d'âge et sexe.

| Colonne | Contenu |
|---|---|
| `annee` | 1960-2025 |
| `groupe_age` | `0-4`, `5-9` … `75-79`, `80+` |
| `sexe` | `H` (hommes) ou `F` (femmes) |
| `effectif` | Nombre de personnes |

### `national/projections_onu.csv`
Une ligne par année (1960-2050) : `annee`, `population`, `part_0_14_pct`, `part_65_plus_pct`.

### `recensement/rgph3_regions.csv` et `recensement/rgph3_districts.csv`
Une ligne par région (22) ou par district (119, Antananarivo Renivohitra étant détaillé par arrondissement).

| Colonne | Contenu |
|---|---|
| `pcode`, `nom` | Code et nom de l'unité (découpage HDX) |
| `region_pcode`, `region` | Région de rattachement (districts) |
| `hommes`, `femmes`, `population` | Population résidente recensée |
| `urbain`, `rural` | Population par milieu de résidence |
| `densite_officielle` | Densité publiée par l'INSTAT (hab/km² ; vide pour les arrondissements) |
| `part_urbaine_pct` | Part de la population urbaine (%) |
| `rapport_masculinite` | Hommes pour 100 femmes |
| `femmes_pct` | Part des femmes (%) |
| `superficie_km2`, `densite` | Superficie calculée à partir des contours, et densité correspondante |
| `estimation_hdx_2018` | Estimation 2018 diffusée sur HDX |
| `ecart_estimation_pct` | Écart de l'estimation HDX par rapport au recensement (%) |

### `recensement/rgph3_communes.csv`
Une ligne par commune ou arrondissement du recensement (1 727).

| Colonne | Contenu |
|---|---|
| `nom`, `district_rgph` | Nom de la commune et de son district, tels qu'imprimés dans le recensement |
| `district_pcode`, `region_pcode`, `region` | Rattachement dans le découpage HDX |
| `hommes`, `femmes`, `population`, `urbain`, `rural` | Population recensée |
| `part_urbaine_pct` | Part de la population urbaine (%) |
| `pcode_hdx` | Code de la commune HDX correspondante, vide si aucune |
| `correspondance` | `exacte`, `approchée` (variante d'orthographe) ou `aucune` |
| `decoupage_identique` | Vrai si le district a exactement les mêmes communes dans les deux sources |

### `recensement/fokontany_estimation_calee_rgph3.csv`
Une ligne par fokontany (17 464). **Estimation**, et non résultat du recensement.

| Colonne | Contenu |
|---|---|
| `pcode`, `nom` | Code et nom du fokontany |
| `commune_pcode`, `commune`, `district_pcode`, `district`, `region_pcode`, `region` | Rattachement |
| `estimation_hdx_2018` | Estimation HDX (base 2009) |
| `population_calee` | Estimation 2018 calée sur la population recensée de la commune ; vide si la commune n'est pas reliée au recensement |
| `part_commune_pct` | Part du fokontany dans la population de sa commune (%) |
| `superficie_km2`, `densite_calee` | Superficie calculée et densité correspondante |
| `population_commune_rgph3` | Population recensée de la commune |
| `correspondance_commune` | Correspondance de la commune avec le recensement : `exacte` ou `approchée` |
| `decoupage_identique` | Vrai si le district a les mêmes communes dans les deux sources |

### `territoires/<niveau>.csv`
Une ligne par unité, pour 2018 (estimation INSTAT/BNGRC).

| Colonne | Contenu | Niveaux |
|---|---|---|
| `pcode`, `nom` | Code et nom de l'unité | tous |
| `region_pcode`, `region` | Région de rattachement | districts, communes, fokontany |
| `district_pcode`, `district` | District de rattachement | communes, fokontany |
| `commune_pcode`, `commune` | Commune de rattachement | fokontany |
| `population` | Habitants en 2018 | tous |
| `superficie_km2` | Superficie calculée à partir des contours | tous |
| `densite` | Habitants par km² | tous |

### `territoires/<niveau>_series_2009_2018.csv`
Mêmes identifiants, plus `annee` (2009-2018) et `population`. Les années 2010 à 2018 sont calculées à partir de 2009 avec un taux uniforme : elles ne permettent pas de comparer la croissance entre territoires.

### `sante/dhs_regions.csv`
Une ligne par région : `pcode`, `nom` et les 8 indicateurs du [tableau DHS](#dhs--enquête-démographique-et-de-santé-2021).

### `estimations/worldpop_<niveau>.csv`
Une ligne par région, district ou commune : `pcode`, `nom`, puis `wp_2015` à `wp_2030` (habitants estimés, arrondis à l'unité).

### `estimations/worldpop_100m_fokontany.csv`
Une ligne par fokontany (17 464) : `pcode`, `nom`, le rattachement (`commune_pcode`, `commune`, `district_pcode`, `district`, `region_pcode`, `region`), `superficie_km2`, puis `wp100_2015` à `wp100_2030` (habitants estimés à partir de la grille à 100 m, arrondis à l'unité).

## Traitements

- **Recensement :** les tableaux sont lus dans le PDF à partir de la position des caractères, car le tableau des communes est imprimé à l'horizontale. Les districts et les communes sont reliés par leur nom (voir la fiche RGPH-3).
- **Noms :** pour relier les sources, les noms sont normalisés : sans accents, apostrophes, tirets ni espaces, avec les chiffres conservés. Les variantes d'orthographe connues sont listées dans `ALIAS_NOMS` (`src/nettoyage.py`), par exemple « Matsiatra Ambony » pour « Haute Matsiatra », ou « Vakinankarata » (orthographe DHS) pour « Vakinankaratra ».
- **Rattachement des contours :** les communes et les fokontany sont rattachés à leur unité parente en cherchant le contour parent qui contient un point intérieur de l'unité (`src/geometrie.py`), puis par le couple (unité parente, nom).
- **Superficies :** calculées sur les contours simplifiés, en projection équirectangulaire locale. La superficie totale obtenue (591 000 km²) est proche de la superficie officielle de Madagascar (587 000 km²).
- **WorldPop 100 m :** chaque carré de 100 m est affecté au fokontany qui contient son centre. Les grilles sont lues par bandes de lignes pour limiter la mémoire.
- **WorldPop :** chaque carré de 1 km est affecté à la commune qui le contient, puis les sommes sont agrégées aux districts et aux régions.
- **Contrôles qualité :** le pipeline s'arrête si l'une de ces conditions n'est pas remplie :
  - le nombre d'unités attendu à chaque niveau ;
  - aucune population manquante ou nulle ;
  - la somme de chaque niveau égale à son niveau parent, à 0,5 % près ;
  - un contour pour chaque unité ;
  - les 22 régions DHS reconnues ;
  - les contrôles d'extraction du recensement (voir la fiche RGPH-3) ;
  - chaque commune calée retrouve exactement sa population recensée dans la somme de ses fokontany ;
  - la pyramide des âges cohérente avec la population totale, à 1 % près ;
  - le total WorldPop proche de celui de l'ONU, à 5 % près, avec moins de 2 % de la population hors des contours ;
  - pour la grille à 100 m : le même total national qu'à 1 km, à 2 % près, et moins de 1 % de la population hors des fokontany.

## Citer ces données

Toute réutilisation des fichiers de ce projet doit mentionner les sources d'origine :

- INSTAT, *Résultats globaux du recensement général de la population et de l'habitation de 2018 de Madagascar (RGPH-3)*, tome 2, décembre 2020.
- Banque mondiale, *World Development Indicators* et *Health Nutrition and Population Statistics* (CC BY 4.0).
- Nations unies, Division de la population, *World Population Prospects* (CC BY 3.0 IGO).
- INSTAT et BNGRC, *Madagascar - Subnational Population Statistics*, diffusé par OCHA sur HDX (CC BY 3.0 IGO).
- geoBoundaries (Runfola et al., 2020) ; régions © contributeurs OpenStreetMap (ODbL 1.0) ; districts, communes et fokontany : BNGRC et OCHA (CC BY 3.0 IGO).
- INSTAT et ICF, *Enquête démographique et de santé de Madagascar 2021* (The DHS Program, API publique).
- Bondarenko M. et al. (2025), *Constrained estimates of 2015-2030 total number of people per grid square*, WorldPop, université de Southampton, R2025A v1, doi:10.5258/SOTON/WP00840 (1 km) et doi:10.5258/SOTON/WP00839 (100 m) (CC BY 4.0).
