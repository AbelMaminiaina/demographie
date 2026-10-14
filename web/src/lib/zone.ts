// Zone d'intervention : un ensemble d'unités d'un même découpage, choisies par l'utilisateur.
// Un seul découpage par zone, pour ne jamais compter deux fois les mêmes habitants.
import type { Base, Meta, Niveau, Unite } from "./types";
import { NIVEAUX } from "./types";

export interface Zone { niveau: Niveau; indices: number[]; nom: string }

/** Zone lue dans une adresse : #zone?n=communes&u=1,5,9&t=Nom (ou #fiche-zone?…). */
export function zoneDepuisAdresse(hash: string, prefixe: "zone" | "fiche-zone"): Zone | null {
  if (!hash.startsWith(`#${prefixe}?`)) return null;
  const p = new URLSearchParams(hash.slice(prefixe.length + 2));
  const niveau = p.get("n") as Niveau;
  const indices = (p.get("u") ?? "").split(",").filter(Boolean).map(Number).filter(Number.isInteger);
  if (!NIVEAUX.includes(niveau) || !indices.length) return null;
  return { niveau, indices: [...new Set(indices)], nom: p.get("t") ?? "" };
}

export function adresseZone(zone: Zone, prefixe: "zone" | "fiche-zone"): string {
  const p = new URLSearchParams({ n: zone.niveau, u: zone.indices.join(",") });
  if (zone.nom) p.set("t", zone.nom);
  return `#${prefixe}?${p.toString().replaceAll("%2C", ",")}`;
}

const CLE_STOCKAGE = "mdg-zone";

export function zoneMemorisee(): Zone | null {
  try {
    const z = JSON.parse(localStorage.getItem(CLE_STOCKAGE) ?? "null");
    return z && NIVEAUX.includes(z.niveau) && Array.isArray(z.indices) ? z : null;
  } catch { return null; }
}

export function memoriserZone(zone: Zone | null) {
  try {
    if (zone?.indices.length) localStorage.setItem(CLE_STOCKAGE, JSON.stringify(zone));
    else localStorage.removeItem(CLE_STOCKAGE);
  } catch { /* stockage indisponible */ }
}

export interface Resume {
  unites: Unite[];
  n: number;
  recenses: number;            // unités reliées au recensement (ou calées, pour les fokontany)
  population2018: number;      // recensement ; pour les fokontany, estimation calée (sinon HDX)
  menages: number | null;
  taille: number | null;       // personnes par ménage, sur les unités où les deux sont connus
  chefFemme: number | null;    // % des ménages
  urbain: number | null;       // % de la population recensée
  superficie: number;
  wp: number[];                // somme WorldPop, une valeur par année de meta.annees_wp
  croissance: number | null;   // % par an entre l'année de référence et l'année courante
  regions: number[];
  districts: number[];
}

export function resumer(base: Base, unitesNiveau: Unite[], zone: Zone, annee: number): Resume {
  const meta: Meta = base.meta;
  const unites = zone.indices.map((i) => unitesNiveau[i]).filter(Boolean);
  const fk = zone.niveau === "fokontany";
  const somme = (f: (u: Unite) => number | null | undefined) => unites.reduce((s, u) => s + (f(u) ?? 0), 0);
  const avecRg = unites.filter((u) => u.rg);
  const avecMenages = avecRg.filter((u) => u.rg!.m != null);
  const menages = avecMenages.reduce((s, u) => s + u.rg!.m!, 0);
  const popMenages = avecMenages.reduce((s, u) => s + u.rg!.p, 0);
  const popRg = avecRg.reduce((s, u) => s + u.rg!.p, 0);
  const wp = meta.annees_wp.map((_, j) => somme((u) => u.wp[j]));
  const a = wp[meta.annees_wp.indexOf(meta.annee_ref)], b = wp[meta.annees_wp.indexOf(annee)];
  const districts = zone.niveau === "regions" ? [] : zone.niveau === "districts" ? zone.indices : unites.map((u) => u.di!);
  return {
    unites, n: unites.length,
    recenses: fk ? unites.filter((u) => u.ca != null).length : avecRg.length,
    population2018: fk ? somme((u) => u.ca ?? u.p) : popRg,
    menages: avecMenages.length ? menages : null,
    taille: menages ? popMenages / menages : null,
    chefFemme: menages ? (100 * avecMenages.reduce((s, u) => s + (u.rg!.m! * (u.rg!.f ?? 0)) / 100, 0)) / menages : null,
    urbain: popRg ? (100 * avecRg.reduce((s, u) => s + (u.rg!.p * u.rg!.u) / 100, 0)) / popRg : null,
    superficie: somme((u) => u.s),
    wp,
    croissance: a && b && annee > meta.annee_ref ? (Math.pow(b / a, 1 / (annee - meta.annee_ref)) - 1) * 100 : null,
    regions: [...new Set(zone.niveau === "regions" ? zone.indices : unites.map((u) => u.r!))],
    districts: [...new Set(districts)],
  };
}

/** Téléchargement d'un tableau en CSV (séparateur « ; » et BOM, pour Excel en français). */
export function telechargerCsv(nomFichier: string, lignes: (string | number | null | undefined)[][]) {
  const champ = (v: string | number | null | undefined) => {
    if (v == null) return "";
    const s = typeof v === "number" ? String(v).replace(".", ",") : v;
    return /[;"\n]/.test(s) ? `"${s.replaceAll('"', '""')}"` : s;
  };
  const texte = "﻿" + lignes.map((l) => l.map(champ).join(";")).join("\r\n");
  const lien = document.createElement("a");
  lien.href = URL.createObjectURL(new Blob([texte], { type: "text/csv;charset=utf-8" }));
  lien.download = nomFichier;
  lien.click();
  setTimeout(() => URL.revokeObjectURL(lien.href), 1000);
}
