/** Amène une section sous l'en-tête collant (sa hauteur varie avec la largeur), puis place le curseur dans un champ. */
export function defilerVers(section: string, champ?: string) {
  const el = document.getElementById(section);
  if (!el) return;
  // L'en-tête n'est collant qu'à partir des tablettes : sur téléphone, il ne masque rien
  const h = document.querySelector("header");
  const entete = h && getComputedStyle(h).position === "sticky" ? h.getBoundingClientRect().height : 0;
  window.scrollTo({ top: el.getBoundingClientRect().top + window.scrollY - entete - 12, behavior: "smooth" });
  if (champ) setTimeout(() => document.getElementById(champ)?.focus({ preventScroll: true }), 400);
}
