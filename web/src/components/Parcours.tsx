import { useEffect, useState } from "react";
import { useLangue } from "../i18n";
import type { Cle } from "../i18n/fr";

export type Besoin = "campagne" | "territoire" | "implanter" | "comparer" | "donnees" | "services";
const BESOINS: Besoin[] = ["campagne", "territoire", "implanter", "comparer", "donnees", "services"];
const CLE = "mdg-parcours-ouvert";

function ouvertInitial(): boolean {
  try { return localStorage.getItem(CLE) !== "non"; } catch { return true; }
}

/** Accueil par besoin : chaque carte mène à l'outil qui y répond. */
export function Parcours({ onChoisir }: { onChoisir: (b: Besoin) => void }) {
  const { t } = useLangue();
  const [ouvert, setOuvert] = useState(ouvertInitial);
  useEffect(() => {
    try { localStorage.setItem(CLE, ouvert ? "oui" : "non"); } catch { /* stockage indisponible */ }
  }, [ouvert]);

  return (
    <details open={ouvert} onToggle={(e) => setOuvert(e.currentTarget.open)} className="carte-ui group p-4 sm:p-5">
      <summary className="flex cursor-pointer list-none items-center justify-between gap-3 [&::-webkit-details-marker]:hidden">
        <span className="grid gap-0.5">
          <span className="text-lg font-semibold">{t("parcoursTitre")}</span>
          <span className="text-[0.9rem] text-encre-2">{t("parcoursIntro")}</span>
        </span>
        <span className="shrink-0 text-sm font-semibold text-accent">
          {ouvert ? t("parcoursMasquer") : t("parcoursAfficher")}
        </span>
      </summary>
      <div className="mt-4 grid gap-3 sm:grid-cols-2 lg:grid-cols-3 2xl:grid-cols-6">
        {BESOINS.map((b) => (
          <button key={b} type="button" onClick={() => onChoisir(b)}
            className="grid cursor-pointer content-start gap-1 rounded-xl border border-trait bg-surface-2 px-4 py-3 text-left text-encre hover:border-trait-fort hover:bg-accent-doux sm:p-4">
            {/* Sur téléphone, le titre seul : les six besoins tiennent sur un écran */}
            <span className="flex items-center justify-between gap-2 font-semibold">{t(`parcours.${b}` as Cle)}<span className="text-accent sm:hidden" aria-hidden="true">→</span></span>
            <span className="hidden text-[0.84rem] leading-snug text-encre-2 sm:block">{t(`parcours.${b}.texte` as Cle, { fiche: t("ficheOuvrir") })}</span>
            <span className="mt-1 hidden text-sm font-semibold text-accent sm:block">{t("parcoursCommencer")} →</span>
          </button>
        ))}
      </div>
    </details>
  );
}
