export type Niveau = "regions" | "districts" | "communes" | "fokontany";
export const NIVEAUX: Niveau[] = ["regions", "districts", "communes", "fokontany"];

/** Résultats du recensement RGPH-3 rattachés à une unité. */
export interface Recensement {
  p: number;   // population recensée
  u: number;   // part urbaine (%)
  rm?: number; // hommes pour 100 femmes
  d?: number;  // densité (hab/km²)
  e?: number;  // écart de l'estimation HDX au recensement (%)
  c?: string;  // correspondance de la commune : exacte ou approchée
  id?: boolean; // découpage communal identique dans le district
  m?: number;   // ménages ordinaires
  t?: number;   // personnes par ménage
  f?: number;   // ménages dirigés par une femme (%)
  tu?: number;  // personnes par ménage, milieu urbain
  tr?: number;  // personnes par ménage, milieu rural
  th?: number;  // personnes par ménage dirigé par un homme (régions et districts)
  tf?: number;  // personnes par ménage dirigé par une femme (régions et districts)
}

export interface Unite {
  n: string;            // nom
  pc?: string;          // P-code (code administratif OCHA/INSTAT)
  p: number;            // estimation HDX 2018
  s: number;            // superficie (km²)
  d?: number | null;    // densité HDX
  wp: number[];         // WorldPop, une valeur par année de meta.annees_wp
  r?: number;           // indice de la région
  di?: number;          // indice du district
  c?: number;           // indice de la commune (fokontany)
  ca?: number | null;   // estimation 2018 calée sur le recensement (fokontany)
  rg?: Recensement;
  dhs?: Record<string, number | null>;
  es?: [number, number, number];   // établissements de santé publics : centres, postes, hôpitaux (liste 2019)
  ec?: number[];        // écoles cartographiées dans OpenStreetMap, par niveau (même ordre que les points, voir donnees.ts)
  ecp?: number[];       // dont écoles identifiées comme publiques, par niveau
  up?: string[];        // universités publiques situées dans l'unité
}

export interface Meta {
  collecte: string | null;
  annee_ref: number;
  annees_wp: number[];
  enquete_dhs: string;
  noms_dhs: Record<string, string>;
  rgph_total: number;
  rgph_communes: number;
  annee_wp100: number;
  nb_fokontany: number;
  nb_sante: number;
  nb_ecoles: number;
  osm_ecoles: string | null;   // date de l'instantané OpenStreetMap
  rg_national: Recensement;
}

export interface Base {
  meta: Meta;
  national: {
    annees: number[];
    population: (number | null)[];
    croissance: (number | null)[];
    isf: (number | null)[];
    esperance: (number | null)[];
    urbanisation: (number | null)[];
    mortalite_infantile: (number | null)[];
  };
  projections: { annees: number[]; population: (number | null)[]; p014: (number | null)[]; p65: (number | null)[] };
  pyramide: { annees: number[]; groupes: string[]; H: number[][]; F: number[][] };
  enquetes: {
    pauvrete: Record<string, number | string | null>[];
    emploi: Record<string, number | string | boolean | null>[];
  };
  niveaux: Record<"regions" | "districts" | "communes", Unite[]>;
}

export type Contours = GeoJSON.FeatureCollection<GeoJSON.MultiPolygon | GeoJSON.Polygon>;

export interface Selection {
  niveau: Niveau;
  i: number;
}
