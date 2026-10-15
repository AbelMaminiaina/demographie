// Comparateur : de 2 à 5 lieux, chacun avec un emplacement de couleur fixe (la couleur suit le lieu).
import type { Niveau } from "./types";
import { NIVEAUX } from "./types";

export const MAX_LIEUX = 5;
/** Couleurs catégorielles, dans l'ordre (palette vérifiée en clair et en sombre). */
export const COULEURS = ["var(--homme)", "var(--femme)", "var(--serie-3)", "var(--serie-4)", "var(--serie-5)"];

export interface Lieu { niveau: Niveau; i: number; couleur: number }

export function ajouterLieu(lieux: Lieu[], niveau: Niveau, i: number): Lieu[] {
  if (lieux.length >= MAX_LIEUX || lieux.some((l) => l.niveau === niveau && l.i === i)) return lieux;
  const libre = [0, 1, 2, 3, 4].find((c) => !lieux.some((l) => l.couleur === c))!;
  return [...lieux, { niveau, i, couleur: libre }];
}

/** Adresse partageable : #comparer?l=communes.253,districts.5 */
export function adresseComparaison(lieux: Lieu[]): string {
  return `#comparer?l=${lieux.map((l) => `${l.niveau}.${l.i}`).join(",")}`;
}

export function comparaisonDepuisAdresse(hash: string): Lieu[] | null {
  if (!hash.startsWith("#comparer?")) return null;
  const l = new URLSearchParams(hash.slice(10)).get("l") ?? "";
  let lieux: Lieu[] = [];
  for (const morceau of l.split(",")) {
    const [niveau, i] = morceau.split(".");
    if (NIVEAUX.includes(niveau as Niveau) && Number.isInteger(Number(i))) lieux = ajouterLieu(lieux, niveau as Niveau, Number(i));
  }
  return lieux.length ? lieux : null;
}

const CLE = "mdg-comparaison";

export function comparaisonMemorisee(): Lieu[] {
  try {
    const l = JSON.parse(localStorage.getItem(CLE) ?? "[]");
    return Array.isArray(l) ? l.filter((x) => NIVEAUX.includes(x.niveau)).slice(0, MAX_LIEUX) : [];
  } catch { return []; }
}

export function memoriserComparaison(lieux: Lieu[]) {
  try { localStorage.setItem(CLE, JSON.stringify(lieux)); } catch { /* stockage indisponible */ }
}
