"""Extraction des tableaux du RGPH-3 (recensement de 2018) depuis les PDF officiels de l'INSTAT.

Source : « Résultats globaux du RGPH-3 de 2018 de Madagascar », tome 2, INSTAT, décembre 2020.
- Tableau 8 : population résidente par sexe, densité, poids démographique, rapport de
  masculinité et part des femmes, par région et district (pages en format portrait).
- Tableau 10 : population par milieu (urbain, rural) et sexe, par district et commune
  (pages en format paysage, texte pivoté).
- Tableau 13 : ménages ordinaires par milieu et sexe du chef de ménage, par district et
  commune (texte pivoté, communes dans le même ordre qu'au tableau 10).
- Tableau 14 : taille moyenne des ménages selon le sexe du chef de ménage, par région et
  district (texte pivoté, districts dans l'ordre du tableau 8).
- Tableau 16 : population, nombre et taille moyenne des ménages ordinaires par milieu, par
  district et commune (texte pivoté) ; sert à contrôler les tableaux 10 et 13.

Les noms de régions sont imprimés à la verticale dans le tableau 8 : la région d'un district
est retrouvée plus tard, par rapprochement avec les données administratives.
"""
import re
from collections import defaultdict

import pdfplumber

NOMBRE = re.compile(r"^\d+(?: \d{3})*(?:,\d+)?$|^-$")


def _valeur(texte):
    if texte == "-":
        return 0
    texte = texte.replace(" ", "").replace(",", ".")
    return float(texte) if "." in texte else int(texte)


def _decouper(ligne):
    """Sépare une ligne en (texte de tête, liste de nombres), les nombres étant en fin de ligne."""
    morceaux = [m for m in re.split(r"\s{2,}", ligne.strip()) if m]
    nombres = []
    while morceaux and NOMBRE.match(morceaux[-1]):
        nombres.insert(0, _valeur(morceaux.pop()))
    return " ".join(morceaux).strip(), nombres


def _lignes_pivotees(page):
    """Texte d'une page en paysage : une ligne du tableau = une colonne de caractères pivotés."""
    groupes = defaultdict(list)
    for c in page.chars:
        if not c["upright"]:
            groupes[round(c["x0"] / 2)].append(c)
    lignes = []
    for cle in sorted(groupes):
        texte, precedent = "", None
        for c in sorted(groupes[cle], key=lambda c: -c["top"]):
            if precedent is not None:
                ecart = precedent["top"] - c["bottom"]
                texte += "  " if ecart > 4 else (" " if ecart > 1.5 else "")
            texte += c["text"]
            precedent = c
        lignes.append(texte)
    return lignes


def _lignes_portrait(page):
    """Texte d'une page en portrait, en séparant les colonnes par deux espaces."""
    mots = page.extract_words(keep_blank_chars=False, use_text_flow=False, x_tolerance=1.5)
    rangs = defaultdict(list)
    for m in mots:
        if m["upright"]:
            rangs[round(m["top"])].append(m)
    lignes = []
    for cle in sorted(rangs):
        texte, precedent = "", None
        for m in sorted(rangs[cle], key=lambda m: m["x0"]):
            if precedent is not None:
                texte += "  " if m["x0"] - precedent["x1"] > 4 else " "
            texte += m["text"]
            precedent = m
        lignes.append(texte)
    return lignes


def tableau_8(pdf):
    """Districts et totaux régionaux. Renvoie (districts, regions, national)."""
    lignes, en_tableau = [], False
    for page in pdf.pages:
        lignes_page = _lignes_portrait(page)
        if any(l.startswith("Tableau 8.") for l in lignes_page):
            en_tableau = True
        if not en_tableau or not any("Total Région" in l for l in lignes_page):
            continue
        lignes += lignes_page
        if any(l.startswith("MADAGASCAR ") for l in lignes_page):
            break
    districts, regions, national = [], [], None
    nom_en_attente = None
    for ligne in lignes:
        tete, nombres = _decouper(ligne)
        if len(nombres) == 7:
            ligne_valeurs = dict(zip(["hommes", "femmes", "population", "poids_pct", "rapport_masculinite",
                                      "femmes_pct", "densite"], nombres))
            if "Total Région" in tete:
                regions.append(ligne_valeurs)
                nom_en_attente = None
            elif tete == "MADAGASCAR":
                national = ligne_valeurs
            else:
                districts.append({"nom": tete, "region_ordre": len(regions) - 1, **ligne_valeurs})
                nom_en_attente = districts[-1]
        elif (not nombres and nom_en_attente is not None and tete and "DÉCEMBRE" not in tete
              and not tete.startswith(("Répartition", "Source", "Région", "Homme", "Effectif", "RÉSULTATS",
                                       "graphique", "rapport"))):
            # Nom de district coupé sur deux lignes (« Antananarivo » / « Renivohitra »).
            # Les noms de régions imprimés à la verticale sortent à l'envers et sont ignorés
            # plus loin, car ils ne correspondent à aucun district.
            nom_en_attente.setdefault("suite", []).append(tete)
            continue
        else:
            nom_en_attente = None
    for d in districts:
        for morceau in d.pop("suite", []):
            d["nom"] = d["nom"] + morceau if d["nom"].endswith("-") else f"{d['nom']} {morceau}"
    return districts, regions, national


def _apparier(lignes):
    """Recolle les lignes dont le libellé est imprimé à part, juste après les nombres."""
    lues = [_decouper(l) for l in lignes]
    resultat, i = [], 0
    while i < len(lues):
        tete, nombres = lues[i]
        if nombres and not tete and i + 1 < len(lues) and lues[i + 1][0] and not lues[i + 1][1]:
            tete = lues[i + 1][0]
            i += 1
        resultat.append((tete, nombres))
        i += 1
    return resultat


def tableau_10(pdf):
    """Communes : population urbaine, rurale et totale par sexe, regroupées par bloc de district."""
    blocs, en_cours, en_tableau = [], None, False
    for page in pdf.pages:
        lignes = _lignes_pivotees(page)
        entete = " ".join(lignes[:4])
        if "Tableau 10." in entete:
            en_tableau = True
        elif "Tableau 11." in entete:
            break
        if not en_tableau or not any("Commune/Arrondissement" in l for l in lignes[:6]):
            continue
        for tete, nombres in _apparier(lignes):
            if len(nombres) != 9:
                continue
            valeurs = dict(zip(["urbain_hommes", "urbain_femmes", "urbain", "rural_hommes", "rural_femmes",
                                "rural", "hommes", "femmes", "population"], nombres))
            if tete.startswith("Total District"):
                en_cours = {"total": valeurs, "communes": []}
                blocs.append(en_cours)
            elif "MADAGASCAR" in tete:
                return blocs
            elif en_cours is not None:
                en_cours["communes"].append({"nom": tete, **valeurs})
    return blocs


def tableau_13(pdf, debut=0):
    """Communes : ménages ordinaires par milieu et sexe du chef de ménage, par bloc de district.

    Renvoie (blocs, total national). Sur certaines pages, le nom de la commune est imprimé
    sur une ligne et ses nombres sur la suivante.
    """
    blocs, en_cours, en_tableau = [], None, False
    for page in pdf.pages[debut:]:
        lignes = _lignes_pivotees(page)
        entete = " ".join(lignes[:4])
        if "Tableau 13." in entete:
            en_tableau = True
        elif "Tableau 14." in entete:
            break
        if not en_tableau:
            continue
        lues = [_decouper(l) for l in lignes]
        i = 0
        while i < len(lues):
            tete, nombres = lues[i]
            if tete and not nombres and i + 1 < len(lues) and not lues[i + 1][0] and len(lues[i + 1][1]) == 9:
                nombres = lues[i + 1][1]
                i += 1
            i += 1
            if len(nombres) != 9:
                continue
            valeurs = dict(zip(["urbain_chef_homme", "urbain_chef_femme", "menages_urbains", "rural_chef_homme",
                                "rural_chef_femme", "menages_ruraux", "menages_chef_homme", "menages_chef_femme",
                                "menages"], nombres))
            if tete.lower().startswith("total district"):
                en_cours = {"total": valeurs, "communes": []}
                blocs.append(en_cours)
            elif "MADAGASCAR" in tete:
                return blocs, valeurs
            elif en_cours is not None:
                en_cours["communes"].append({"nom": tete, **valeurs})
    return blocs, None


def _lignes_tableau(pdf, debut, numero):
    """Lignes (libellé, nombres) des pages pivotées du tableau `numero`, jusqu'au tableau suivant."""
    lignes, en_tableau = [], False
    for page in pdf.pages[debut:]:
        lues = _lignes_pivotees(page)
        entete = " ".join(lues[:4])
        if f"Tableau {numero}." in entete:
            en_tableau = True
        elif f"Tableau {numero + 1}." in entete:
            break
        if en_tableau:
            lignes += [_decouper(l) for l in lues]
    return lignes


def tableau_14(pdf, debut=0):
    """Régions et districts : ménages ordinaires et leur taille moyenne selon le sexe du chef de ménage.

    Renvoie (districts, regions, national) ; les districts sont dans l'ordre du tableau 8.
    """
    colonnes = ["population_hommes", "population_femmes", "population_menages", "menages_chef_homme",
                "menages_chef_femme", "menages", "taille_chef_homme", "taille_chef_femme", "taille_menage",
                "chef_femme_pct", "poids_menages_pct"]
    districts, regions = [], []
    for tete, nombres in _lignes_tableau(pdf, debut, 14):
        if len(nombres) != len(colonnes):
            continue
        valeurs = dict(zip(colonnes, nombres))
        if tete.startswith("Total Région"):
            regions.append(valeurs)
        elif "MADAGASCAR" in tete:
            return districts, regions, valeurs
        else:
            districts.append({"nom": tete, **valeurs})
    return districts, regions, None


def tableau_16(pdf, debut=0):
    """Communes : population et nombre des ménages ordinaires, taille moyenne, par milieu.

    Renvoie des blocs par district, comme le tableau 10 et dans le même ordre.
    """
    colonnes = ["population_urbaine_menages", "menages_urbains", "taille_urbain", "population_rurale_menages",
                "menages_ruraux", "taille_rural", "population_menages", "menages", "taille_menage"]
    blocs, en_cours = [], None
    for tete, nombres in _lignes_tableau(pdf, debut, 16):
        if len(nombres) == 8:
            # Commune seulement urbaine ou seulement rurale : un des tirets de la colonne vide
            # se perd à la lecture. Le groupe « Ensemble » (3 derniers nombres) dit lequel.
            if nombres[:3] == nombres[-3:]:
                nombres = [*nombres[:3], 0, 0, 0, *nombres[-3:]]
            elif nombres[2:5] == nombres[-3:]:
                nombres = [0, 0, 0, *nombres[-3:], *nombres[-3:]]
        if len(nombres) != len(colonnes):
            continue
        valeurs = dict(zip(colonnes, nombres))
        if "total district" in tete.lower():   # parfois précédé du nom du district
            en_cours = {"total": valeurs, "communes": []}
            blocs.append(en_cours)
        elif "MADAGASCAR" in tete:
            break
        elif en_cours is not None:
            en_cours["communes"].append({"nom": tete, **valeurs})
    return blocs


def extraire(chemin_pdf):
    with pdfplumber.open(chemin_pdf) as pdf:
        districts, regions, national = tableau_8(pdf)
        communes = tableau_10(pdf)
        # Le tableau 13 commence vers la page 100 : on évite de relire les pages précédentes.
        menages, menages_national = tableau_13(pdf, debut=90)
        tailles_districts, tailles_regions, tailles_national = tableau_14(pdf, debut=150)
        controle = tableau_16(pdf, debut=160)
    return {"districts": districts, "regions": regions, "national": national, "blocs_communes": communes,
            "blocs_menages": menages, "menages_national": menages_national,
            "tailles_districts": tailles_districts, "tailles_regions": tailles_regions,
            "tailles_national": tailles_national,
            "blocs_controle": controle}
