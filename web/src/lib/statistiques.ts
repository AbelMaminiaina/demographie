// Mesure d'audience avec GoatCounter : sans cookie ni donnée personnelle, donc sans bandeau de consentement.
// Les pages vues sont comptées par le script ; les actions utiles (devis, téléchargements, fiches) comme événements.
import { GOATCOUNTER } from "../config";

declare global {
  interface Window { goatcounter?: { count: (v: { path: string; title?: string; event?: boolean }) => void } }
}

/** Compte une action, par exemple « devis-envoye/formulaire ». Sans effet si le compteur n'est pas configuré. */
export function compter(evenement: string) {
  try { window.goatcounter?.count({ path: evenement, event: true }); } catch { /* compteur bloqué */ }
}

/** Charge le compteur et suit les téléchargements et les fiches PDF sans toucher aux composants. */
export function demarrerStatistiques() {
  if (!GOATCOUNTER || location.hostname === "localhost") return;
  const script = document.createElement("script");
  script.async = true;
  script.src = "https://gc.zgo.at/count.js";
  script.dataset.goatcounter = GOATCOUNTER;
  document.head.appendChild(script);

  document.addEventListener("click", (e) => {
    const lien = (e.target as Element | null)?.closest?.("a[href*='telechargements/']");
    if (lien) compter(`telechargement/${lien.getAttribute("href")!.split("/").pop()}`);
  });
  const fiche = () => {
    const m = location.hash.match(/^#(fiche-zone|fiche)\b/);
    if (m) compter(m[1] === "fiche" ? "fiche-pdf/lieu" : "fiche-pdf/zone");
  };
  window.addEventListener("hashchange", fiche);
  fiche();
}
