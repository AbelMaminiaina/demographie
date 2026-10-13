// Mise en forme des nombres : espace insécable fine pour les milliers, virgule décimale
// (convention utilisée en français comme en malgache).
const formats = new Map<number, Intl.NumberFormat>();

export function nombre(v: number | null | undefined, decimales = 0): string {
  if (v == null || Number.isNaN(v) || !Number.isFinite(v)) return "n.d.";
  let f = formats.get(decimales);
  if (!f) {
    f = new Intl.NumberFormat("fr-FR", { minimumFractionDigits: decimales, maximumFractionDigits: decimales });
    formats.set(decimales, f);
  }
  return f.format(v);
}

export const entier = (v: number | null | undefined) => nombre(v, 0);
export const pct = (v: number | null | undefined, d = 1) => (v == null ? "n.d." : `${nombre(v, d)} %`);
export const densite = (v: number | null | undefined) => nombre(v, v != null && v < 10 ? 1 : 0);

export function compact(v: number | null | undefined): string {
  if (v == null) return "n.d.";
  if (Math.abs(v) >= 1e6) return `${nombre(v / 1e6, 1)} M`;
  if (Math.abs(v) >= 1e4) return `${nombre(v / 1e3, 0)} k`;
  return entier(v);
}

/** Clé de recherche : sans accents ni ponctuation, en minuscules. */
export function normaliser(s: string): string {
  return (s || "").normalize("NFD").replace(/[̀-ͯ]/g, "").toLowerCase().replace(/[^a-z0-9]+/g, " ").trim();
}
