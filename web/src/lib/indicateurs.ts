import { scaleQuantile, scaleThreshold } from "d3-scale";
import type { Cle } from "../i18n/fr";
import { compact, densite, entier, nombre } from "./format";
import type { Meta, Niveau, Unite } from "./types";

export interface Indicateur {
  id: string;
  nom: Cle;
  groupe: "recensement" | "estimations" | "sante";
  note: Cle;
  val: (u: Unite, annee: number) => number | null | undefined;
  fmt: (v: number) => string;
  court?: (v: number) => string;
  annee?: boolean;      // dépend de l'année choisie
  divergent?: boolean;  // écart positif ou négatif autour de zéro
  niveaux: Niveau[];    // découpages pour lesquels l'indicateur existe
}

const TOUS: Niveau[] = ["regions", "districts", "communes", "fokontany"];
const REGIONS_DISTRICTS: Niveau[] = ["regions", "districts"];
const JUSQU_AUX_COMMUNES: Niveau[] = ["regions", "districts", "communes"];

export function croissance(u: Unite, annee: number, meta: Meta): number | null {
  const ref = meta.annee_ref;
  if (annee === ref) return 0;
  const a = u.wp[meta.annees_wp.indexOf(ref)], b = u.wp[meta.annees_wp.indexOf(annee)];
  if (!a || b == null) return null;
  return (Math.pow(b / a, 1 / (annee - ref)) - 1) * 100;
}

export function construireIndicateurs(meta: Meta): Indicateur[] {
  const iAn = (annee: number) => meta.annees_wp.indexOf(annee);
  const pourcent = (v: number) => `${nombre(v, 1)} %`;
  return [
    { id: "rg", nom: "ind.rg", groupe: "recensement", note: "note.rg", niveaux: JUSQU_AUX_COMMUNES,
      val: (u) => u.rg?.p, fmt: entier, court: compact },
    { id: "rgd", nom: "ind.rgd", groupe: "recensement", note: "note.rg", niveaux: REGIONS_DISTRICTS,
      val: (u) => u.rg?.d, fmt: densite },
    { id: "rgu", nom: "ind.rgu", groupe: "recensement", note: "note.rg", niveaux: JUSQU_AUX_COMMUNES,
      val: (u) => u.rg?.u, fmt: pourcent },
    { id: "rgt", nom: "ind.rgt", groupe: "recensement", note: "note.rgt", niveaux: JUSQU_AUX_COMMUNES,
      val: (u) => u.rg?.t, fmt: (v) => nombre(v, 1) },
    { id: "rgf", nom: "ind.rgf", groupe: "recensement", note: "note.rgf", niveaux: JUSQU_AUX_COMMUNES,
      val: (u) => u.rg?.f, fmt: pourcent },
    { id: "rgm", nom: "ind.rgm", groupe: "recensement", note: "note.rg", niveaux: REGIONS_DISTRICTS,
      val: (u) => u.rg?.rm, fmt: (v) => nombre(v, 1) },
    { id: "rge", nom: "ind.rge", groupe: "recensement", note: "note.rge", niveaux: REGIONS_DISTRICTS, divergent: true,
      val: (u) => u.rg?.e, fmt: (v) => `${v > 0 ? "+" : ""}${nombre(v, 1)} %` },
    { id: "p", nom: "ind.p", groupe: "estimations", note: "note.p", niveaux: TOUS, val: (u) => u.p, fmt: entier, court: compact },
    { id: "d", nom: "ind.d", groupe: "estimations", note: "note.p", niveaux: TOUS, val: (u) => u.d, fmt: densite },
    { id: "wp", nom: "ind.wp", groupe: "estimations", note: "note.wp", niveaux: TOUS, annee: true,
      val: (u, a) => u.wp[iAn(a)], fmt: entier, court: compact },
    { id: "wpd", nom: "ind.wpd", groupe: "estimations", note: "note.wp", niveaux: TOUS, annee: true,
      val: (u, a) => (u.s > 0 ? u.wp[iAn(a)] / u.s : null), fmt: densite },
    { id: "cr", nom: "ind.cr", groupe: "estimations", note: "note.cr", niveaux: TOUS, annee: true,
      val: (u, a) => croissance(u, a, meta), fmt: pourcent },
    { id: "ca", nom: "ind.ca", groupe: "estimations", note: "note.ca", niveaux: ["fokontany"],
      val: (u) => u.ca, fmt: entier, court: compact },
    ...Object.keys(meta.noms_dhs).map((cle): Indicateur => ({
      id: `dhs:${cle}`, nom: `dhs.${cle}` as Cle, groupe: "sante", note: "note.dhs", niveaux: ["regions"],
      val: (u) => u.dhs?.[cle], fmt: (v) => nombre(v, Number.isInteger(v) ? 0 : 1),
    })),
  ];
}

export const INDICATEUR_PAR_DEFAUT: Record<Niveau, string> = {
  regions: "rg", districts: "rg", communes: "p", fokontany: "wpd",
};

const SEUILS_ECART = [-15, -7.5, -2.5, 2.5, 7.5, 15];

export interface Echelle {
  couleur: (v: number | null | undefined) => string;
  classes: { couleur: string; libelle: string }[];
  divergent: boolean;
}

/** Couleurs lues dans les jetons CSS, pour suivre le thème clair ou sombre. */
function jeton(nom: string) {
  return getComputedStyle(document.documentElement).getPropertyValue(nom).trim();
}

export function construireEchelle(ind: Indicateur, valeurs: (number | null | undefined)[]): Echelle {
  const vide = jeton("--vide");
  if (ind.divergent) {
    const couleurs = [1, 2, 3, 4, 5, 6, 7].map((i) => jeton(`--d${i}`));
    const s = scaleThreshold<number, string>().domain(SEUILS_ECART).range(couleurs);
    const libelles = ["< −15", "−15", "−7,5", "−2,5", "+2,5", "+7,5", "+15"];
    return { couleur: (v) => (v == null ? vide : s(v)), classes: couleurs.map((c, i) => ({ couleur: c, libelle: libelles[i] })), divergent: true };
  }
  const v = valeurs.filter((x): x is number => x != null && Number.isFinite(x));
  const rampe = [1, 2, 3, 4, 5, 6, 7].map((i) => jeton(`--q${i}`));
  const n = Math.min(7, new Set(v).size);
  const couleurs = n >= 7 ? rampe : Array.from({ length: Math.max(n, 2) }, (_, i, a) => rampe[Math.round((i / (a.length - 1)) * 6)]);
  const s = scaleQuantile<string>().domain(v).range(couleurs);
  const bornes = [Math.min(...v), ...s.quantiles()];
  const lib = ind.court ?? ind.fmt;
  return {
    couleur: (x) => (x == null || !Number.isFinite(x) ? vide : s(x)),
    classes: couleurs.map((c, i) => ({ couleur: c, libelle: lib(bornes[i]).replace(" %", "") })),
    divergent: false,
  };
}
