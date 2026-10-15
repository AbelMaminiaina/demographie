import { useMemo, useRef, useState } from "react";
import { useLangue } from "../i18n";
import type { Cle } from "../i18n/fr";
import { normaliser } from "../lib/format";
import type { Base, Niveau, Selection, Unite } from "../lib/types";

interface Entree { niveau: Niveau; i: number; n: string; cle: string; detail: string }
const ORDRE: Record<Niveau, number> = { regions: 0, districts: 1, communes: 2, fokontany: 3 };

export function Recherche({ base, fokontany, onDemanderFokontany, onChoisir, id = "recherche", effacer = false }: {
  base: Base; fokontany: Unite[] | null; onDemanderFokontany: () => void;
  onChoisir: (s: Selection, nom: string) => void;
  id?: string;        // identifiant du champ, à changer quand la recherche apparaît plusieurs fois
  effacer?: boolean;  // vider le champ après un choix (ajout de lieux successifs)
}) {
  const { t } = useLangue();
  const [texte, setTexte] = useState("");
  const [ouvert, setOuvert] = useState(false);
  const [actif, setActif] = useState(0);
  const champ = useRef<HTMLInputElement>(null);

  const index = useMemo(() => {
    const R = base.niveaux.regions, D = base.niveaux.districts, C = base.niveaux.communes;
    const e: Entree[] = [];
    R.forEach((u, i) => e.push({ niveau: "regions", i, n: u.n, cle: normaliser(u.n), detail: t("unite.regions") }));
    D.forEach((u, i) => e.push({ niveau: "districts", i, n: u.n, cle: normaliser(u.n), detail: `${t("unite.districts")} · ${R[u.r!].n}` }));
    C.forEach((u, i) => e.push({ niveau: "communes", i, n: u.n, cle: normaliser(u.n), detail: `${t("unite.communes")} · ${D[u.di!].n}` }));
    fokontany?.forEach((u, i) => e.push({ niveau: "fokontany", i, n: u.n, cle: normaliser(u.n), detail: `${t("unite.fokontany")} · ${C[u.c!].n}` }));
    return e;
  }, [base, fokontany, t]);

  const q = normaliser(texte);
  const resultats = q.length < 2 ? [] : index.filter((e) => e.cle.includes(q))
    // Nom exact d'abord, puis noms qui commencent par la recherche, puis par niveau (région avant fokontany)
    .sort((a, b) => Number(b.cle === q) - Number(a.cle === q) || Number(b.cle.startsWith(q)) - Number(a.cle.startsWith(q))
      || ORDRE[a.niveau] - ORDRE[b.niveau] || a.n.localeCompare(b.n, "fr"))
    .slice(0, 12);

  const valider = (e: Entree) => {
    setTexte(effacer ? "" : e.n);
    setOuvert(false);
    onChoisir({ niveau: e.niveau, i: e.i }, e.n);
    champ.current?.blur();
  };

  return (
    <div className="relative w-full max-w-md" role="combobox" aria-expanded={ouvert && q.length >= 2} aria-haspopup="listbox" aria-owns={`${id}-suggestions`}>
      <label htmlFor={id} className="sr-only">{t("rechercher")}</label>
      <svg aria-hidden="true" viewBox="0 0 20 20" className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-discret">
        <circle cx="8.5" cy="8.5" r="5.5" fill="none" stroke="currentColor" strokeWidth="1.8" /><path d="m13 13 4 4" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" />
      </svg>
      <input id={id} ref={champ} type="search" autoComplete="off" value={texte} placeholder={t("rechercherAide")}
        aria-controls={`${id}-suggestions`} aria-activedescendant={ouvert && resultats[actif] ? `${id}-suggestion-${actif}` : undefined}
        className="w-full rounded-xl border border-trait-fort bg-surface py-2 pl-9 pr-3 text-[0.92rem] text-encre placeholder:text-discret"
        onFocus={() => { setOuvert(true); onDemanderFokontany(); }}
        onBlur={() => setTimeout(() => setOuvert(false), 120)}
        onChange={(e) => { setTexte(e.target.value); setActif(0); setOuvert(true); onDemanderFokontany(); }}
        onKeyDown={(e) => {
          if (!resultats.length) return;
          if (e.key === "ArrowDown") { setActif((actif + 1) % resultats.length); e.preventDefault(); }
          else if (e.key === "ArrowUp") { setActif((actif - 1 + resultats.length) % resultats.length); e.preventDefault(); }
          else if (e.key === "Enter") { valider(resultats[actif]); e.preventDefault(); }
          else if (e.key === "Escape") setOuvert(false);
        }} />
      {ouvert && q.length >= 2 && (
        <ul id={`${id}-suggestions`} role="listbox" className="carte-ui absolute left-0 right-0 top-[calc(100%+6px)] z-40 m-0 max-h-80 list-none overflow-y-auto p-1">
          {resultats.length === 0 && <li className="px-3 py-2 text-sm text-discret">{t("aucunResultat")}</li>}
          {resultats.map((e, k) => (
            <li key={`${e.niveau}-${e.i}`} id={`${id}-suggestion-${k}`} role="option" aria-selected={k === actif}
              onMouseDown={(ev) => { ev.preventDefault(); valider(e); }} onMouseEnter={() => setActif(k)}
              className={`flex cursor-pointer justify-between gap-3 rounded-lg px-3 py-1.5 text-sm ${k === actif ? "bg-accent-doux" : ""}`}>
              <span className="truncate">{e.n}</span>
              <small className="shrink-0 text-discret">{e.detail}</small>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

export const libelleNiveau = (t: (c: Cle) => string, n: Niveau) => t(`niveau.${n}` as Cle);
