"""Point d'entrée : collecte -> nettoyage -> visualisation.

Usage :
    python src/pipeline.py               # pipeline complet
    python src/pipeline.py --sans-collecte   # réutilise les données brutes déjà téléchargées
"""
import argparse

from collecte import tout_collecter
from nettoyage import tout_nettoyer
from visualisation import tout_visualiser


def main():
    parser = argparse.ArgumentParser(description="Pipeline démographique Madagascar")
    parser.add_argument("--sans-collecte", action="store_true",
                        help="ne pas retélécharger les données brutes")
    args = parser.parse_args()

    if not args.sans_collecte:
        print("[1/3] Collecte")
        tout_collecter()
    print("[2/3] Nettoyage et contrôles")
    series, pyramide, regions, districts = tout_nettoyer()
    print("[3/3] Graphiques et rapport")
    tout_visualiser(series, pyramide, regions, districts)
    print("Terminé.")


if __name__ == "__main__":
    main()
