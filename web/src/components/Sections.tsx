import { scaleBand, scaleLinear } from "d3-scale";
import { useMemo, useState } from "react";
import { useLangue } from "../i18n";
import type { Cle } from "../i18n/fr";
import type { Indicateur } from "../lib/indicateurs";
import { telechargerCsv } from "../lib/csv";
import { compact, entier, nombre, normaliser, pct } from "../lib/format";
import type { Base, Niveau, Selection, Unite } from "../lib/types";
import { Courbes, Infobulle, Legende, Sparkline, type Bulle } from "./Graphiques";

function derniere(serie: (number | null)[]) {
  for (let i = serie.length - 1; i >= 0; i--) if (serie[i] != null) return i;
  return -1;
}

export function Tuiles({ base }: { base: Base }) {
  const { t } = useLangue();
  const N = base.national;
  const defs: [Cle, keyof typeof N, (v: number) => string][] = [
    ["tuile.population", "population", (v) => compact(v)],
    ["tuile.croissance", "croissance", (v) => `${nombre(v, 2)} %`],
    ["tuile.isf", "isf", (v) => nombre(v, 2)],
    ["tuile.esperance", "esperance", (v) => `${nombre(v, 1)} ${t("ans")}`],
    ["tuile.urbanisation", "urbanisation", (v) => `${nombre(v, 1)} %`],
    ["tuile.mortalite", "mortalite_infantile", (v) => `${nombre(v, 1)} ‰`],
  ];
  return (
    <section aria-label="Indicateurs nationaux" className="grid grid-cols-2 gap-3 md:grid-cols-3 xl:grid-cols-6">
      {defs.map(([titre, cle, f]) => {
        const serie = N[cle] as (number | null)[];
        const i = derniere(serie);
        const points = N.annees.map((a, j) => [a, serie[j]] as [number, number | null])
          .filter((p): p is [number, number] => p[1] != null);
        return (
          <div key={cle} className="carte-ui grid gap-0.5 px-4 py-3">
            <span className="etiquette">{t(titre)}</span>
            <span className="chiffre text-[1.35rem] font-medium">{f(serie[i]!)}</span>
            <span className="text-[0.78rem] text-discret">{t("depuis", { annee: N.annees[i], debut: N.annees[0] })}</span>
            <div className="mt-1"><Sparkline points={points} /></div>
          </div>
        );
      })}
    </section>
  );
}

export function Tendances({ base }: { base: Base }) {
  const { t } = useLangue();
  const N = base.national, P = base.projections, PY = base.pyramide;
  const obs = N.annees.map((a, i) => [a, N.population[i]] as [number, number | null]).filter((p): p is [number, number] => p[1] != null);
  const dernier = obs[obs.length - 1][0];
  const proj = P.annees.map((a, i) => [a, P.population[i]] as [number, number | null])
    .filter((p): p is [number, number] => p[1] != null && p[0] >= dernier);
  const [annee, setAnnee] = useState(PY.annees[PY.annees.length - 1]);
  const [bulle, setBulle] = useState<Bulle | null>(null);
  const k = PY.annees.indexOf(annee);
  const max = Math.max(...PY.H.flat(), ...PY.F.flat());
  const L = 440, H = 320, centre = 24;
  const y = scaleBand<string>().domain([...PY.groupes].reverse()).range([6, H - 24]).padding(0.12);
  const xg = scaleLinear().domain([0, max]).range([L / 2 - centre, 6]);
  const xd = scaleLinear().domain([0, max]).range([L / 2 + centre, L - 6]);
  const total = PY.H[k].reduce((s, v) => s + v, 0) + PY.F[k].reduce((s, v) => s + v, 0);

  return (
    <section className="grid gap-4 lg:grid-cols-[minmax(0,1.4fr)_minmax(0,1fr)]">
      <div className="carte-ui min-w-0 p-5">
        <h2 className="m-0 mb-2 text-lg font-semibold">{t("tendancesTitre")}</h2>
        <Courbes series={[
          { nom: t("estimationsOnu"), couleur: "var(--accent)", points: obs },
          { nom: t("projectionOnu"), couleur: "var(--accent)", points: proj, pointille: true },
        ]} formatY={(v) => (v ? `${v / 1e6} M` : "0")}
          libelleFin={(_, p) => t("enAnnee", { v: `${nombre(p[1] / 1e6, 1)} M`, annee: p[0] })}
          infobulle={(a) => {
            const o = obs.find((p) => p[0] === a), j = P.annees.indexOf(a), pr = proj.find((p) => p[0] === a);
            const v = o ?? pr;
            return v && (<>
              <strong className="block">{a}{o ? "" : ` · ${t("projection")}`}</strong>
              {entier(v[1])}
              {pr && j >= 0 && <><br />{t("part014")} : {pct(P.p014[j])} · {t("part65")} : {pct(P.p65[j])}</>}
            </>);
          }} />
        <Legende elements={[{ nom: t("estimationsOnu"), couleur: "var(--accent)" }, { nom: t("projectionOnu"), couleur: "var(--accent)", pointille: true }]} />
      </div>
      <div className="carte-ui min-w-0 p-5">
        <div className="mb-2 flex flex-wrap items-center justify-between gap-3">
          <h2 className="m-0 text-lg font-semibold">{t("pyramideTitre")}</h2>
          <label className="flex items-center gap-2 text-sm">
            <span className="etiquette">{t("annee")}</span>
            <input type="range" min={PY.annees[0]} max={PY.annees[PY.annees.length - 1]} value={annee}
              onChange={(e) => setAnnee(+e.target.value)} className="w-32 accent-[var(--accent)]" />
            <span className="chiffre">{annee}</span>
          </label>
        </div>
        <svg viewBox={`0 0 ${L} ${H}`} className="block h-auto w-full" role="img" aria-label={t("pyramideTitre")}>
          {xd.ticks(3).filter((v) => v > 0).flatMap((v) => [xg(v), xd(v)].map((x, n) => (
            <g key={`${v}-${n}`}>
              <line x1={x} x2={x} y1={6} y2={H - 24} stroke="var(--trait)" />
              <text x={x} y={H - 6} textAnchor="middle" fontSize={11} fill="var(--discret)" className="chiffre">{nombre(v / 1e6, 1)} M</text>
            </g>
          )))}
          {PY.groupes.map((g, i) => {
            const h = PY.H[k][i], f = PY.F[k][i];
            const info = (e: React.MouseEvent) => setBulle({ x: e.clientX, y: e.clientY, contenu: (<>
              <strong className="block">{g} {t("ans")} · {annee}</strong>
              {t("hommes")} : {entier(h)}<br />{t("femmes")} : {entier(f)}<br />{t("partPopulation", { v: pct((100 * (h + f)) / total) })}
            </>) });
            return (
              <g key={g} onMouseMove={info} onMouseLeave={() => setBulle(null)}>
                <rect x={xg(h)} y={y(g)} width={Math.max(0, L / 2 - centre - xg(h))} height={y.bandwidth()} rx={2} fill="var(--homme)" />
                <rect x={xd(0)} y={y(g)} width={Math.max(0, xd(f) - xd(0))} height={y.bandwidth()} rx={2} fill="var(--femme)" />
                {i % 2 === 0 && <text x={L / 2} y={y(g)! + y.bandwidth() / 2 + 4} textAnchor="middle" fontSize={10} fill="var(--discret)" className="chiffre">{g}</text>}
              </g>
            );
          })}
        </svg>
        <Legende elements={[{ nom: t("hommes"), couleur: "var(--homme)", carre: true }, { nom: t("femmes"), couleur: "var(--femme)", carre: true }]} />
        <Infobulle bulle={bulle} />
      </div>
    </section>
  );
}

export function Enquetes({ base }: { base: Base }) {
  const { t } = useLangue();
  const pauvrete = base.enquetes.pauvrete;
  const emploi = base.enquetes.emploi;
  const points = (cle: string) => pauvrete.map((r) => [r.annee as number, r[cle] as number] as [number, number]);
  const series: { cle: string; nom: string; couleur: string }[] = [
    { cle: "taux_activite_pct", nom: t("emploi.taux_activite_pct"), couleur: "var(--homme)" },
    { cle: "emploi_informel_pct", nom: t("emploi.emploi_informel_pct"), couleur: "var(--femme)" },
    { cle: "part_agriculture_pct", nom: t("emploi.part_agriculture_pct"), couleur: "var(--serie-3)" },
  ];
  const L = 520, H = 260, m = { h: 22, b: 30, g: 36 };
  const x = scaleBand<string>().domain(emploi.map((e) => e.enquete as string)).range([m.g, L - 8]).padding(0.22);
  const xs = scaleBand<string>().domain(series.map((s) => s.cle)).range([0, x.bandwidth()]).padding(0.08);
  const y = scaleLinear().domain([0, 100]).range([H - m.b, m.h]);
  const [bulle, setBulle] = useState<Bulle | null>(null);
  const rupture = emploi.some((e, i) => i > 0 && e.rupture_de_serie);

  return (
    <section className="carte-ui grid gap-4 p-5">
      <div>
        <h2 className="m-0 text-lg font-semibold">{t("enquetesTitre")}</h2>
        <p className="m-0 mt-1 max-w-[70ch] text-[0.88rem] text-encre-2">{t("enquetesIntro")}</p>
      </div>
      <div className="grid gap-6 lg:grid-cols-2">
        <div className="min-w-0">
          <h3 className="etiquette m-0 mb-2">{t("pauvreteTitre")}</h3>
          <Courbes hauteur={260} formatY={(v) => `${v} %`} series={[
            { nom: t("seuil3"), couleur: "var(--homme)", points: points("pauvrete_3_00_dollars_pct") },
            { nom: t("seuil42"), couleur: "var(--femme)", points: points("pauvrete_4_20_dollars_pct") },
          ]} libelleFin={(_, p) => `${nombre(p[1], 0)} %`}
            infobulle={(a) => {
              const r = pauvrete.find((p) => p.annee === a);
              return r && (<><strong className="block">{a} · {r.enquete as string}</strong>
                {t("seuil3")} : {pct(r.pauvrete_3_00_dollars_pct as number)}<br />{t("seuil42")} : {pct(r.pauvrete_4_20_dollars_pct as number)}<br />Gini : {nombre(r.gini as number, 3)}</>);
            }} />
          <Legende elements={[{ nom: t("seuil3"), couleur: "var(--homme)" }, { nom: t("seuil42"), couleur: "var(--femme)" }]} />
          <p className="m-0 mt-1 text-[0.78rem] text-discret">{t("seuilsNote")}</p>
        </div>
        <div className="min-w-0">
          <h3 className="etiquette m-0 mb-2">{t("emploiTitre")}</h3>
          <svg viewBox={`0 0 ${L} ${H}`} className="block h-auto w-full" role="img" aria-label={t("emploiTitre")}>
            {[0, 25, 50, 75, 100].map((v) => (
              <g key={v}>
                <line x1={m.g} x2={L - 8} y1={y(v)} y2={y(v)} stroke="var(--trait)" />
                <text x={m.g - 6} y={y(v) + 4} textAnchor="end" fontSize={11} fill="var(--discret)" className="chiffre">{v}</text>
              </g>
            ))}
            {emploi.map((e, i) => (
              <g key={e.enquete as string} transform={`translate(${x(e.enquete as string)},0)`}>
                {series.map((s) => {
                  const v = e[s.cle] as number | null;
                  if (v == null) return null;
                  return (
                    <rect key={s.cle} x={xs(s.cle)} y={y(v)} width={xs.bandwidth()} height={y(0) - y(v)} rx={3} fill={s.couleur}
                      onMouseMove={(ev) => setBulle({ x: ev.clientX, y: ev.clientY, contenu: (<><strong className="block">{e.enquete as string}</strong>{s.nom} : {pct(v)}</>) })}
                      onMouseLeave={() => setBulle(null)} />
                  );
                })}
                <text x={x.bandwidth() / 2} y={H - 10} textAnchor="middle" fontSize={11} fill="var(--encre-2)">{e.enquete as string}{i > 0 && e.rupture_de_serie ? " *" : ""}</text>
              </g>
            ))}
          </svg>
          <Legende elements={series.map((s) => ({ nom: s.nom, couleur: s.couleur, carre: true }))} />
          {rupture && <p className="m-0 mt-1 text-[0.78rem] text-discret">* {t("rupture")}</p>}
          <Infobulle bulle={bulle} />
        </div>
      </div>
    </section>
  );
}

export function Classement({ niveau, unites, indicateur, indicateurs, annee, base, selection, onChoisir }: {
  niveau: Niveau; unites: Unite[] | null; indicateur: Indicateur; indicateurs: Indicateur[]; annee: number; base: Base;
  selection: Selection | null; onChoisir: (s: Selection) => void;
}) {
  const { t } = useLangue();
  // Tous les indicateurs du découpage, une ligne par unité, avec codes et rattachement pour les jointures
  const exporter = () => {
    if (!unites) return;
    const R = base.niveaux.regions, D = base.niveaux.districts, C = base.niveaux.communes;
    const liste = indicateurs.filter((i) => i.niveaux.includes(niveau));
    const parents = (u: Unite): string[] => niveau === "regions" ? [] : niveau === "districts" ? [R[u.r!].n]
      : niveau === "communes" ? [R[u.r!].n, D[u.di!].n] : [R[u.r!].n, D[u.di!].n, C[u.c!].n];
    const entetes = ["P-code", t(`unite.${niveau}` as Cle),
      ...(["regions", "districts", "communes"] as Niveau[]).slice(0, ["regions", "districts", "communes", "fokontany"].indexOf(niveau)).map((n) => t(`unite.${n}` as Cle)),
      ...liste.map((i) => `${t(i.nom)}${i.annee ? ` ${annee}` : ""}`)];
    const valeur = (v: number | null | undefined) => (v == null || !Number.isFinite(v) ? null : Math.round(v * 100) / 100);
    telechargerCsv(`${t(`niveau.${niveau}` as Cle)}_${annee}.csv`.toLowerCase(), [
      entetes,
      ...unites.map((u) => [u.pc ?? "", u.n, ...parents(u), ...liste.map((i) => valeur(i.val(u, annee)))]),
      [],
      [t("zoneSourcesCsv", { date: base.meta.collecte ?? "" })],
    ]);
  };
  const [filtre, setFiltre] = useState("");
  const [tri, setTri] = useState<{ col: "rang" | "n" | "parent" | "v"; sens: 1 | -1 }>({ col: "v", sens: -1 });
  const lignes = useMemo(() => {
    if (!unites) return [];
    const R = base.niveaux.regions, D = base.niveaux.districts, C = base.niveaux.communes;
    const l = unites.map((u, i) => ({ i, n: u.n, v: indicateur.val(u, annee),
      parent: niveau === "districts" ? R[u.r!].n : niveau === "communes" ? D[u.di!].n : niveau === "fokontany" ? C[u.c!].n : "" }))
      .filter((x): x is { i: number; n: string; v: number; parent: string } => x.v != null && Number.isFinite(x.v));
    const rangs = new Map([...l].sort((a, b) => b.v - a.v).map((x, k) => [x.i, k + 1]));
    return l.map((x) => ({ ...x, rang: rangs.get(x.i)! }));
  }, [unites, indicateur, annee, niveau, base]);
  const q = normaliser(filtre);
  const filtrees = (q ? lignes.filter((l) => normaliser(l.n).includes(q) || normaliser(l.parent).includes(q)) : lignes)
    .sort((a, b) => (typeof a[tri.col] === "string" ? String(a[tri.col]).localeCompare(String(b[tri.col]), "fr") : (a[tri.col] as number) - (b[tri.col] as number)) * tri.sens);
  const MAX = 400, visibles = filtrees.slice(0, MAX);
  const parentNom = { regions: "", districts: t("unite.regions"), communes: t("unite.districts"), fokontany: t("unite.communes") }[niveau];
  const colonnes: { col: "rang" | "n" | "parent" | "v"; nom: string; num: boolean }[] = [
    { col: "rang", nom: t("rang"), num: true }, { col: "n", nom: t(`unite.${niveau}` as Cle), num: false },
    ...(niveau !== "regions" ? [{ col: "parent" as const, nom: parentNom, num: false }] : []),
    { col: "v", nom: t(indicateur.nom).replace(/ \(.*\)$/, ""), num: true },
  ];
  return (
    <section className="carte-ui grid gap-3 p-5">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h2 className="m-0 text-lg font-semibold">{t("classementTitre")} · {t(`niveau.${niveau}` as Cle)} · {t(indicateur.nom)}{indicateur.annee ? ` · ${annee}` : ""}</h2>
        <div className="flex flex-wrap items-center gap-2">
          <input type="search" value={filtre} onChange={(e) => setFiltre(e.target.value)} placeholder={t("filtrer")} aria-label={t("filtrer")}
            className="rounded-lg border border-trait-fort bg-surface px-3 py-1.5 text-sm" />
          <button type="button" onClick={exporter} disabled={!unites} title={t("classementExporterAide")}
            className="cursor-pointer rounded-lg border border-trait-fort bg-surface px-3 py-1.5 text-sm font-semibold text-accent hover:bg-accent-doux">
            {t("classementExporter")}
          </button>
        </div>
      </div>
      <div className="max-h-[440px] overflow-auto rounded-lg border border-trait">
        <table className="w-full border-collapse text-[0.88rem]">
          <thead>
            <tr>
              {colonnes.map((c) => (
                <th key={c.col} aria-sort={tri.col === c.col ? (tri.sens > 0 ? "ascending" : "descending") : "none"}
                  className={`sticky top-0 border-b border-trait bg-surface px-3 py-2 font-semibold ${c.num ? "text-right" : "text-left"}`}>
                  <button type="button" className="cursor-pointer border-0 bg-transparent p-0 font-semibold text-encre"
                    onClick={() => setTri({ col: c.col, sens: tri.col === c.col ? (tri.sens === 1 ? -1 : 1) : c.num ? -1 : 1 })}>
                    {c.nom}{tri.col === c.col ? (tri.sens > 0 ? " ↑" : " ↓") : ""}
                  </button>
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {visibles.map((l) => (
              <tr key={l.i} onClick={() => onChoisir({ niveau, i: l.i })}
                className={`cursor-pointer border-b border-trait hover:bg-accent-doux ${selection?.niveau === niveau && selection.i === l.i ? "bg-accent-doux font-semibold" : ""}`}>
                <td className="chiffre px-3 py-1.5 text-right">{l.rang}</td>
                <td className="px-3 py-1.5">{l.n}</td>
                {niveau !== "regions" && <td className="px-3 py-1.5 text-encre-2">{l.parent}</td>}
                <td className="chiffre px-3 py-1.5 text-right">{indicateur.fmt(l.v)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {filtrees.length > MAX && <p className="m-0 text-[0.82rem] text-discret">{t("lignesAffichees", { n: entier(MAX), total: entier(filtrees.length) })}</p>}
    </section>
  );
}
