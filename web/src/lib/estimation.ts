// Population à une date donnée : trois estimations et leur fourchette, puis les groupes d'âge.
import type { Base, Niveau, Unite } from "./types";

/** Groupes d'âge proposés, en indices des tranches de 5 ans de la pyramide nationale. */
export const GROUPES_AGE: { cle: string; tranches: number[]; femmes: boolean }[] = [
  { cle: "0-4", tranches: [0], femmes: false },
  { cle: "5-14", tranches: [1, 2], femmes: false },
  { cle: "15-24", tranches: [3, 4], femmes: false },
  { cle: "15-64", tranches: [3, 4, 5, 6, 7, 8, 9, 10, 11, 12], femmes: false },
  { cle: "65+", tranches: [13, 14, 15, 16], femmes: false },
  { cle: "f15-49", tranches: [3, 4, 5, 6, 7, 8, 9], femmes: true },
];

export interface Estimation {
  annee: number;
  worldpop: number;          // A : estimation WorldPop directe
  locale: number | null;     // B : recensement 2018 × croissance WorldPop de chaque unité
  nationale: number | null;  // C : recensement 2018 × croissance nationale de l'ONU
  centrale: number;          // B si le recensement est connu, sinon A
  min: number;
  max: number;
  avecBase: number;          // unités qui ont une population 2018 de référence
  n: number;
  anneeStructure: number;    // année de la pyramide nationale utilisée pour les âges
  groupes: { cle: string; valeur: number; part: number }[];
}

/** Population 2018 de référence : recensement ; pour un fokontany, estimation calée sur le recensement. */
const base2018 = (u: Unite, niveau: Niveau) => (niveau === "fokontany" ? u.ca ?? null : u.rg?.p ?? null);

export function estimer(base: Base, unites: Unite[], niveau: Niveau, annee: number): Estimation {
  const { meta, projections, pyramide } = base;
  const j = meta.annees_wp.indexOf(annee), j18 = meta.annees_wp.indexOf(meta.annee_ref);
  const onu = (a: number) => projections.population[projections.annees.indexOf(a)] ?? null;
  const croissanceOnu = (onu(annee) ?? 0) / (onu(meta.annee_ref) ?? 1);
  let worldpop = 0, locale = 0, nationale = 0, avecBase = 0;
  for (const u of unites) {
    const b = base2018(u, niveau);
    worldpop += u.wp[j];
    if (b != null && u.wp[j18] > 0) {
      avecBase++;
      locale += b * (u.wp[j] / u.wp[j18]);
      nationale += b * croissanceOnu;
    } else {
      // Sans population de référence, l'unité compte avec WorldPop dans les trois estimations
      locale += u.wp[j];
      nationale += u.wp[j];
    }
  }
  const avecRecensement = avecBase > 0;
  const valeurs = avecRecensement ? [worldpop, locale, nationale] : [worldpop];
  const centrale = avecRecensement ? locale : worldpop;

  // Structure par âge nationale de l'année (ou de la dernière année connue)
  const anneeStructure = Math.min(annee, pyramide.annees[pyramide.annees.length - 1]);
  const k = pyramide.annees.indexOf(anneeStructure);
  const H = pyramide.H[k], F = pyramide.F[k];
  const total = H.reduce((s, v) => s + v, 0) + F.reduce((s, v) => s + v, 0);
  const groupes = GROUPES_AGE.map((g) => {
    const effectif = g.tranches.reduce((s, t) => s + F[t] + (g.femmes ? 0 : H[t]), 0);
    const part = effectif / total;
    return { cle: g.cle, valeur: centrale * part, part: 100 * part };
  });

  return {
    annee, worldpop, locale: avecRecensement ? locale : null, nationale: avecRecensement ? nationale : null,
    centrale, min: Math.min(...valeurs), max: Math.max(...valeurs), avecBase, n: unites.length, anneeStructure, groupes,
  };
}

/** Arrondi à la dizaine, pour ne pas afficher une précision que les estimations n'ont pas. */
export const arrondi = (v: number) => (Math.abs(v) >= 1000 ? Math.round(v / 10) * 10 : Math.round(v));
