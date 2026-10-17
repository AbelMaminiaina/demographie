// Mise en forme des nombres : espace insécable fine pour les milliers, virgule décimale
// (convention utilisée en français comme en malgache) ; virgule et point décimal en anglais.
type LangueFormat = "fr" | "mg" | "en";
const formats = new Map<number, Intl.NumberFormat>();
let localeNombres = "fr-FR";

/** Appelé par le fournisseur de langue avant l'affichage. */
export function choisirLangueNombres(langue: LangueFormat) {
  const l = langue === "en" ? "en-GB" : "fr-FR";
  if (l !== localeNombres) { localeNombres = l; formats.clear(); }
}

export function nombre(v: number | null | undefined, decimales = 0): string {
  if (v == null || Number.isNaN(v) || !Number.isFinite(v)) return "n.d.";
  let f = formats.get(decimales);
  if (!f) {
    f = new Intl.NumberFormat(localeNombres, { minimumFractionDigits: decimales, maximumFractionDigits: decimales });
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

// Les navigateurs ne connaissent pas les noms de mois malgaches : on les fournit
const MOIS_MG = ["Janoary", "Febroary", "Martsa", "Aprily", "Mey", "Jona", "Jolay", "Aogositra", "Septambra", "Oktobra", "Novambra", "Desambra"];

/** Date en toutes lettres (« 14 octobre 2026 », « 14 Oktobra 2026 », « 14 October 2026 »). */
export function dateLongue(jour: Date, langue: LangueFormat): string {
  return langue === "mg"
    ? `${jour.getDate()} ${MOIS_MG[jour.getMonth()]} ${jour.getFullYear()}`
    : jour.toLocaleDateString(langue === "en" ? "en-GB" : "fr-FR", { day: "numeric", month: "long", year: "numeric" });
}

/** Clé de recherche : sans accents ni ponctuation, en minuscules. */
export function normaliser(s: string): string {
  return (s || "").normalize("NFD").replace(/[̀-ͯ]/g, "").toLowerCase().replace(/[^a-z0-9]+/g, " ").trim();
}
