import { useMemo, useState } from "react";
import { useLangue } from "../i18n";
import type { Cle } from "../i18n/fr";
import { telechargerCsv } from "../lib/csv";
import { adresseComparaison, COULEURS, MAX_LIEUX, type Lieu } from "../lib/comparaison";
import type { Indicateur } from "../lib/indicateurs";
import { entier, nombre } from "../lib/format";
import type { Base, Niveau, Selection, Unite } from "../lib/types";
import { Courbes, Legende } from "./Graphiques";
import { Recherche } from "./Recherche";

type Unites = Record<Niveau, Unite[] | null>;

function rattachement(base: Base, u: Unite, niveau: Niveau): string {
  const R = base.niveaux.regions, D = base.niveaux.districts, C = base.niveaux.communes;
  return niveau === "regions" ? "Madagascar" : niveau === "districts" ? R[u.r!].n
    : niveau === "communes" ? `${D[u.di!].n} · ${R[u.r!].n}` : `${C[u.c!].n} · ${D[u.di!].n}`;
}

const bouton = "cursor-pointer rounded-lg border border-trait-fort bg-surface px-3 py-1.5 text-sm font-semibold text-accent hover:bg-accent-doux disabled:cursor-default disabled:opacity-50";

export function Comparateur({ base, unites, fokontany, indicateurs, annee, lieux, onAjouter, onRetirer, onVider, onChoisir, onDemanderFokontany }: {
  base: Base; unites: Unites; fokontany: Unite[] | null; indicateurs: Indicateur[]; annee: number; lieux: Lieu[];
  onAjouter: (s: Selection) => void; onRetirer: (l: Lieu) => void; onVider: () => void;
  onChoisir: (s: Selection) => void; onDemanderFokontany: () => void;
}) {
  const { t } = useLangue();
  const [copie, setCopie] = useState(false);
  const meta = base.meta;
  const R = base.niveaux.regions;
  const presents = lieux.map((l) => ({ ...l, u: unites[l.niveau]?.[l.i] })).filter((l): l is Lieu & { u: Unite } => !!l.u);

  // Lignes : chaque indicateur connu pour au moins un lieu ; la santé vient de la région du lieu
  const lignes: { nom: string; valeurs: string[]; brutes: (number | null)[] }[] = [];
  for (const ind of indicateurs.filter((i) => !i.id.startsWith("dhs:"))) {
    const brutes = presents.map((l) => (ind.niveaux.includes(l.niveau) ? ind.val(l.u, annee) ?? null : null));
    if (brutes.every((v) => v == null)) continue;
    lignes.push({ nom: `${t(ind.nom)}${ind.annee ? ` · ${annee}` : ""}`, brutes,
      valeurs: brutes.map((v) => (v == null || !Number.isFinite(v) ? "n.d." : ind.fmt(v))) });
  }
  const lignesSante = Object.keys(meta.noms_dhs).map((cle) => {
    const brutes = presents.map((l) => (l.niveau === "regions" ? l.u : R[l.u.r!]).dhs?.[cle] ?? null);
    return { nom: `${t(`dhs.${cle}` as Cle)} ${t("compRegion")}`, brutes,
      valeurs: brutes.map((v) => (v == null ? "n.d." : nombre(v, Number.isInteger(v) ? 0 : 1))) };
  });

  const i18 = meta.annees_wp.indexOf(meta.annee_ref);
  const series = presents.map((l) => ({
    nom: l.u.n, couleur: COULEURS[l.couleur],
    points: meta.annees_wp.map((a, j) => [a, l.u.wp[i18] ? (100 * l.u.wp[j]) / l.u.wp[i18] : 0] as [number, number]),
  }));

  const exporter = () => telechargerCsv("comparaison.csv", [
    [t("ficheIndicateur"), ...presents.map((l) => l.u.n)],
    [t("compRattachement"), ...presents.map((l) => rattachement(base, l.u, l.niveau))],
    ...[...lignes, ...lignesSante].map((l) => [l.nom, ...l.brutes.map((v) => (v == null ? null : Math.round(v * 100) / 100))]),
    [], [t("zoneSourcesCsv", { date: meta.collecte ?? "" })],
  ]);
  const copier = async () => {
    const lien = window.location.href.split("#")[0] + adresseComparaison(lieux);
    try { await navigator.clipboard.writeText(lien); setCopie(true); setTimeout(() => setCopie(false), 2000); }
    catch { window.prompt(t("zoneCopierLien"), lien); }
  };

  const cellule = "border-b border-trait px-3 py-1.5";
  return (
    <section className="carte-ui grid gap-4 p-5" id="comparateur">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="grid gap-1">
          <h2 className="m-0 text-lg font-semibold">{t("compTitre")}</h2>
          <p className="m-0 max-w-[75ch] text-[0.9rem] text-encre-2">{t("compIntro", { n: MAX_LIEUX })}</p>
        </div>
        {lieux.length < MAX_LIEUX && (
          <div className="w-full max-w-sm">
            <Recherche base={base} fokontany={fokontany} onDemanderFokontany={onDemanderFokontany} id="recherche-comparer" effacer
              onChoisir={(s) => onAjouter(s)} />
          </div>
        )}
      </div>

      {presents.length === 0 ? <p className="m-0 text-sm text-discret">{t("compVide")}</p> : (
        <>
          <div className="flex flex-wrap items-center gap-2">
            {presents.map((l) => (
              <span key={`${l.niveau}-${l.i}`} className="inline-flex items-center gap-2 rounded-full border border-trait bg-surface-2 py-1 pl-3 pr-1 text-sm">
                <i className="inline-block h-2.5 w-2.5 rounded-full" style={{ background: COULEURS[l.couleur] }} />
                <button type="button" className="cursor-pointer border-0 bg-transparent p-0 text-encre underline-offset-2 hover:underline"
                  onClick={() => onChoisir({ niveau: l.niveau, i: l.i })}>{l.u.n}</button>
                <span className="text-[0.75rem] text-discret">{t(`unite.${l.niveau}` as Cle)}</span>
                <button type="button" onClick={() => onRetirer(l)} aria-label={t("compRetirer", { nom: l.u.n })}
                  className="cursor-pointer rounded-full border-0 bg-transparent px-2 text-lg leading-none text-discret hover:text-encre">×</button>
              </span>
            ))}
            <span className="ml-auto flex flex-wrap gap-2">
              <button type="button" className={bouton} onClick={exporter}>{t("zoneExporter")}</button>
              <button type="button" className={bouton} onClick={copier}>{copie ? t("zoneLienCopie") : t("zoneCopierLien")}</button>
              <button type="button" className={bouton} onClick={onVider}>{t("zoneVider")}</button>
            </span>
          </div>

          <div className="overflow-x-auto rounded-lg border border-trait">
            <table className="w-full border-collapse text-[0.86rem]">
              <thead>
                <tr>
                  <th className={`${cellule} text-left font-semibold`}>{t("ficheIndicateur")}</th>
                  {presents.map((l) => (
                    <th key={`${l.niveau}-${l.i}`} className={`${cellule} min-w-[120px] text-right align-bottom font-semibold`}>
                      <span className="flex items-center justify-end gap-1.5">
                        <i className="inline-block h-2.5 w-2.5 shrink-0 rounded-full" style={{ background: COULEURS[l.couleur] }} />{l.u.n}
                      </span>
                      <span className="block text-[0.72rem] font-normal text-discret">{rattachement(base, l.u, l.niveau)}</span>
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {lignes.map((l) => (
                  <tr key={l.nom}>
                    <td className={cellule}>{l.nom}</td>
                    {l.valeurs.map((v, k) => <td key={k} className={`${cellule} chiffre text-right`}>{v}</td>)}
                  </tr>
                ))}
                <tr><td colSpan={presents.length + 1} className="bg-surface-2 px-3 py-1.5 etiquette">{t("compSante", { enquete: meta.enquete_dhs })}</td></tr>
                {lignesSante.map((l) => (
                  <tr key={l.nom}>
                    <td className={cellule}>{l.nom}</td>
                    {l.valeurs.map((v, k) => <td key={k} className={`${cellule} chiffre text-right`}>{v}</td>)}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          <div className="max-w-[820px]">
            <h3 className="etiquette m-0 mb-2">{t("compCourbes", { ref: meta.annee_ref })}</h3>
            <Courbes series={series} hauteur={240} minY={Math.min(80, ...series.flatMap((s) => s.points.map((p) => p[1])))}
              formatY={(v) => nombre(v, 0)} libelleFin={(s, p) => `${s.nom} ${nombre(p[1], 0)}`}
              infobulle={(a) => (
                <>
                  <strong className="block">{a}</strong>
                  {presents.map((l) => (
                    <span key={`${l.niveau}-${l.i}`} className="block">{l.u.n} : {entier(l.u.wp[meta.annees_wp.indexOf(a)])}</span>
                  ))}
                </>
              )} />
            <Legende elements={series.map((s) => ({ nom: s.nom, couleur: s.couleur }))} />
            <p className="m-0 mt-1 text-[0.78rem] text-discret">{t("compNoteCourbes", { ref: meta.annee_ref })}</p>
          </div>
        </>
      )}
    </section>
  );
}

interface Critere { id: string; min: string; max: string }
const NIVEAUX_CIBLAGE: Niveau[] = ["communes", "districts"];
const MAX_AFFICHES = 100;

/** Étude d'implantation : unités qui remplissent tous les critères, triées par un indicateur. */
export function Ciblage({ base, unites, indicateurs, annee, onChoisir, onZone, onComparer }: {
  base: Base; unites: Unites; indicateurs: Indicateur[]; annee: number;
  onChoisir: (s: Selection) => void; onZone: (niveau: Niveau, indices: number[]) => void; onComparer: (lieux: Selection[]) => void;
}) {
  const { t } = useLangue();
  const [niveau, setNiveau] = useState<Niveau>("communes");
  const [region, setRegion] = useState(-1);
  const [criteres, setCriteres] = useState<Critere[]>([{ id: "rg", min: "20000", max: "" }, { id: "cr", min: "2", max: "" }]);
  const [tri, setTri] = useState("wp");
  const R = base.niveaux.regions, D = base.niveaux.districts;
  const choix = indicateurs.filter((i) => i.niveaux.includes(niveau) && !i.divergent);
  const parId = (id: string) => choix.find((i) => i.id === id);
  const valides = criteres.filter((c) => parId(c.id));
  const indTri = parId(tri) ?? choix[0];

  const resultats = useMemo(() => {
    const liste = unites[niveau] ?? [];
    const nombreOuNul = (s: string) => (s.trim() === "" ? null : Number(s.replace(",", ".")));
    const bornes = valides.map((c) => ({ ind: parId(c.id)!, min: nombreOuNul(c.min), max: nombreOuNul(c.max) }));
    return liste.map((u, i) => ({ u, i }))
      .filter(({ u }) => region < 0 || u.r === region)
      .filter(({ u }) => bornes.every(({ ind, min, max }) => {
        const v = ind.val(u, annee);
        return v != null && Number.isFinite(v) && (min == null || v >= min) && (max == null || v <= max);
      }))
      .sort((a, b) => (indTri.val(b.u, annee) ?? -Infinity) - (indTri.val(a.u, annee) ?? -Infinity));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [unites, niveau, region, criteres, tri, annee, indicateurs]);

  const colonnes = [...new Map([...valides.map((c) => parId(c.id)!), indTri].map((i) => [i.id, i])).values()];
  const exporter = () => telechargerCsv(`selection_${niveau}.csv`, [
    ["P-code", t(`unite.${niveau}` as Cle), t("unite.regions"), ...(niveau === "communes" ? [t("unite.districts")] : []),
     ...colonnes.map((i) => `${t(i.nom)}${i.annee ? ` ${annee}` : ""}`)],
    ...resultats.map(({ u }) => [u.pc ?? "", u.n, R[u.r!].n, ...(niveau === "communes" ? [D[u.di!].n] : []),
      ...colonnes.map((i) => { const v = i.val(u, annee); return v == null ? null : Math.round(v * 100) / 100; })]),
    [], [t("cibCriteresCsv", { criteres: valides.map((c) => `${t(parId(c.id)!.nom)} ${c.min && `≥ ${c.min}`} ${c.max && `≤ ${c.max}`}`).join(" ; ") })],
    [t("zoneSourcesCsv", { date: base.meta.collecte ?? "" })],
  ]);

  const champ = "rounded-lg border border-trait-fort bg-surface px-2 py-1 text-sm text-encre";
  const cellule = "border-b border-trait px-3 py-1.5";
  return (
    <section className="carte-ui grid grid-cols-[minmax(0,1fr)] gap-4 p-5" id="ciblage">
      <div className="grid gap-1">
        <h2 className="m-0 text-lg font-semibold">{t("cibTitre")}</h2>
        <p className="m-0 max-w-[80ch] text-[0.9rem] text-encre-2">{t("cibIntro")}</p>
      </div>

      <div className="flex flex-wrap items-center gap-3">
        <div className="segments" role="group" aria-label={t("cibNiveau")}>
          {NIVEAUX_CIBLAGE.map((n) => (
            <button key={n} type="button" aria-pressed={niveau === n} onClick={() => setNiveau(n)}>{t(`niveau.${n}` as Cle)}</button>
          ))}
        </div>
        <label className="flex items-center gap-2 text-sm">
          <span className="etiquette">{t("unite.regions")}</span>
          <select value={region} onChange={(e) => setRegion(Number(e.target.value))} className={champ}>
            <option value={-1}>{t("cibToutes")}</option>
            {R.map((r, i) => ({ r, i })).sort((a, b) => a.r.n.localeCompare(b.r.n, "fr")).map(({ r, i }) => <option key={i} value={i}>{r.n}</option>)}
          </select>
        </label>
        <label className="flex min-w-0 max-w-full items-center gap-2 text-sm">
          <span className="etiquette">{t("cibTri")}</span>
          <select value={indTri.id} onChange={(e) => setTri(e.target.value)} className={`${champ} min-w-0 max-w-full`}>
            {choix.map((i) => <option key={i.id} value={i.id}>{t(i.nom)}</option>)}
          </select>
        </label>
      </div>

      <div className="grid grid-cols-[minmax(0,1fr)] gap-2">
        <h3 className="etiquette m-0">{t("cibCriteres")}</h3>
        {criteres.map((c, k) => {
          const ind = parId(c.id);
          const maj = (champ: Partial<Critere>) => setCriteres((l) => l.map((x, j) => (j === k ? { ...x, ...champ } : x)));
          return (
            <div key={k} className="flex flex-wrap items-center gap-2">
              <select value={c.id} onChange={(e) => maj({ id: e.target.value })} className={`${champ} min-w-0 max-w-full`} aria-label={t("indicateur")}>
                {!ind && <option value={c.id}>{t("cibIndisponible")}</option>}
                {choix.map((i) => <option key={i.id} value={i.id}>{t(i.nom)}</option>)}
              </select>
              <label className="flex items-center gap-1 text-sm">{t("cibMin")}
                <input inputMode="decimal" value={c.min} onChange={(e) => maj({ min: e.target.value })} className={`${champ} w-24`} />
              </label>
              <label className="flex items-center gap-1 text-sm">{t("cibMax")}
                <input inputMode="decimal" value={c.max} onChange={(e) => maj({ max: e.target.value })} className={`${champ} w-24`} />
              </label>
              <button type="button" onClick={() => setCriteres((l) => l.filter((_, j) => j !== k))} aria-label={t("cibRetirerCritere")}
                className="cursor-pointer rounded border-0 bg-transparent px-1.5 text-lg leading-none text-discret hover:text-encre">×</button>
            </div>
          );
        })}
        <div>
          <button type="button" className={bouton} onClick={() => setCriteres((l) => [...l, { id: choix[0].id, min: "", max: "" }])}>
            {t("cibAjouterCritere")}
          </button>
        </div>
        <p className="m-0 text-[0.78rem] text-discret">{t("cibAideUnites")}</p>
      </div>

      <div className="flex flex-wrap items-center justify-between gap-3">
        <p className="m-0 font-semibold">{t("cibResultats", { n: entier(resultats.length), unites: t(`niveau.${niveau}` as Cle).toLowerCase() })}</p>
        <div className="flex flex-wrap gap-2">
          <button type="button" className={bouton} disabled={!resultats.length} onClick={exporter}>{t("zoneExporter")}</button>
          <button type="button" className={bouton} disabled={!resultats.length}
            onClick={() => onComparer(resultats.slice(0, MAX_LIEUX).map(({ i }) => ({ niveau, i })))}>
            {t("cibComparer", { n: Math.min(MAX_LIEUX, resultats.length) })}
          </button>
          <button type="button" className={bouton} disabled={!resultats.length} onClick={() => onZone(niveau, resultats.map(({ i }) => i))}>
            {t("cibZone")}
          </button>
        </div>
      </div>
      {resultats.length > 0 && (
        <div className="max-h-[420px] overflow-auto rounded-lg border border-trait">
          <table className="w-full border-collapse text-[0.86rem]">
            <thead>
              <tr>
                <th className={`sticky top-0 bg-surface ${cellule} text-right font-semibold`}>{t("rang")}</th>
                <th className={`sticky top-0 bg-surface ${cellule} text-left font-semibold`}>{t(`unite.${niveau}` as Cle)}</th>
                <th className={`sticky top-0 bg-surface ${cellule} text-left font-semibold`}>{t("zoneRattachement")}</th>
                {colonnes.map((i) => (
                  <th key={i.id} className={`sticky top-0 bg-surface ${cellule} text-right font-semibold`}>
                    {t(i.nom).replace(/ \(.*\)$/, "")}{i.id === indTri.id ? " ↓" : ""}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {resultats.slice(0, MAX_AFFICHES).map(({ u, i }, k) => (
                <tr key={i} onClick={() => onChoisir({ niveau, i })} className="cursor-pointer hover:bg-accent-doux">
                  <td className={`${cellule} chiffre text-right`}>{k + 1}</td>
                  <td className={cellule}>{u.n}</td>
                  <td className={`${cellule} text-encre-2`}>{niveau === "communes" ? `${D[u.di!].n} · ${R[u.r!].n}` : R[u.r!].n}</td>
                  {colonnes.map((ind) => {
                    const v = ind.val(u, annee);
                    return <td key={ind.id} className={`${cellule} chiffre text-right`}>{v == null ? "n.d." : ind.fmt(v)}</td>;
                  })}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
      {resultats.length > MAX_AFFICHES && (
        <p className="m-0 text-[0.82rem] text-discret">{t("lignesAffichees", { n: entier(MAX_AFFICHES), total: entier(resultats.length) })}</p>
      )}
    </section>
  );
}
