import { scaleLinear } from "d3-scale";
import { area, line } from "d3-shape";
import { useCallback, useRef, useState, type PointerEvent, type ReactNode } from "react";
import { compact, entier } from "../lib/format";

/** Petite courbe d'évolution, sans axes. */
export function Sparkline({ points, hauteur = 34 }: { points: [number, number][]; hauteur?: number }) {
  if (points.length < 2) return null;
  const L = 160;
  const x = scaleLinear().domain([points[0][0], points[points.length - 1][0]]).range([2, L - 4]);
  const ys = points.map((p) => p[1]);
  const y = scaleLinear().domain([Math.min(...ys), Math.max(...ys)]).range([hauteur - 3, 3]);
  const fin = points[points.length - 1];
  return (
    <svg viewBox={`0 0 ${L} ${hauteur}`} preserveAspectRatio="none" className="block w-full" style={{ height: hauteur }} aria-hidden="true">
      <path d={area<[number, number]>().x((p) => x(p[0])).y0(hauteur).y1((p) => y(p[1]))(points) ?? ""} fill="var(--accent-doux)" />
      <path d={line<[number, number]>().x((p) => x(p[0])).y((p) => y(p[1]))(points) ?? ""} fill="none" stroke="var(--accent)" strokeWidth={1.6} vectorEffect="non-scaling-stroke" />
      <circle cx={x(fin[0])} cy={y(fin[1])} r={2.6} fill="var(--accent)" />
    </svg>
  );
}

export interface Bulle { x: number; y: number; contenu: ReactNode }

/** Infobulle positionnée près du pointeur, sans sortir de la fenêtre. */
export function Infobulle({ bulle }: { bulle: Bulle | null }) {
  if (!bulle) return null;
  const droite = bulle.x > window.innerWidth - 280;
  const bas = bulle.y > window.innerHeight - 140;
  return (
    <div role="status" className="pointer-events-none fixed z-50 max-w-[260px] rounded-lg px-3 py-2 text-[0.82rem] shadow-lg"
      style={{ left: droite ? bulle.x - 14 : bulle.x + 14, top: bas ? bulle.y - 14 : bulle.y + 14,
        transform: `translate(${droite ? "-100%" : "0"}, ${bas ? "-100%" : "0"})`, background: "var(--encre)", color: "var(--fond)" }}>
      {bulle.contenu}
    </div>
  );
}

interface Serie { nom: string; couleur: string; points: [number, number][]; pointille?: boolean }

/** Courbes sur un axe commun, avec réticule et infobulle au survol. */
export function Courbes({ series, hauteur = 260, formatY = compact, minY = 0, repere, libelleFin, infobulle }: {
  series: Serie[]; hauteur?: number; formatY?: (v: number) => string; minY?: number;
  repere?: { x: number; y: number; libelle: string };
  libelleFin?: (s: Serie, p: [number, number]) => string;
  infobulle: (annee: number) => ReactNode;
}) {
  const [survol, setSurvol] = useState<{ annee: number; px: number; py: number } | null>(null);
  // Largeur de dessin : celle du conteneur sous 640 px, pour garder des libellés lisibles sur téléphone ;
  // au-delà, le dessin de 640 px est agrandi comme avant.
  const [L, setL] = useState(640);
  const observateur = useRef<ResizeObserver | null>(null);
  const mesurer = useCallback((el: HTMLDivElement | null) => {
    observateur.current?.disconnect();
    if (!el) return;
    observateur.current = new ResizeObserver(([e]) => setL(Math.max(300, Math.min(640, Math.round(e.contentRect.width)))));
    observateur.current.observe(el);
  }, []);
  const m = { h: 16, d: 24, b: 26, g: 48 };
  const tous = series.flatMap((s) => s.points);
  if (!tous.length) return null;
  const xs = tous.map((p) => p[0]), ys = tous.map((p) => p[1]).concat(repere ? [repere.y] : []);
  const x = scaleLinear().domain([Math.min(...xs), Math.max(...xs)]).range([m.g, L - m.d]);
  const y = scaleLinear().domain([minY, Math.max(...ys) * 1.08]).nice(5).range([hauteur - m.b, m.h]);
  const annees = [...new Set(xs)].sort((a, b) => a - b);
  const pasX = x.ticks(Math.min(L < 480 ? 5 : 8, annees.length)).filter((t) => Number.isInteger(t));
  // Libellés de fin de courbe écartés d'au moins 14 px pour ne pas se chevaucher
  const yLibelles = series.map((s) => y(s.points[s.points.length - 1]?.[1] ?? 0));
  const ordre = yLibelles.map((_, k) => k).sort((a, b) => yLibelles[a] - yLibelles[b]);
  for (let k = 1; k < ordre.length; k++) {
    yLibelles[ordre[k]] = Math.max(yLibelles[ordre[k]], yLibelles[ordre[k - 1]] + 14);
  }

  // Survol à la souris comme au doigt (un appui affiche l'infobulle de l'année la plus proche)
  const survoler = (e: PointerEvent<SVGSVGElement>) => {
    const r = e.currentTarget.getBoundingClientRect();
    const vx = ((e.clientX - r.left) / r.width) * L;
    const a = annees.reduce((p, c) => (Math.abs(c - x.invert(vx)) < Math.abs(p - x.invert(vx)) ? c : p), annees[0]);
    setSurvol({ annee: a, px: e.clientX, py: e.clientY });
  };

  return (
    <div ref={mesurer} className="relative">
      <svg viewBox={`0 0 ${L} ${hauteur}`} className="block h-auto w-full overflow-visible" role="img"
        onPointerMove={survoler} onPointerDown={survoler} onPointerLeave={() => setSurvol(null)}>
        {y.ticks(5).map((t) => (
          <g key={t}>
            <line x1={m.g} x2={L - m.d} y1={y(t)} y2={y(t)} stroke="var(--trait)" />
            <text x={m.g - 6} y={y(t) + 4} textAnchor="end" fontSize={11} fill="var(--discret)" className="chiffre">{formatY(t)}</text>
          </g>
        ))}
        {pasX.map((t) => (
          <text key={t} x={x(t)} y={hauteur - 6} textAnchor="middle" fontSize={11} fill="var(--discret)" className="chiffre">{t}</text>
        ))}
        {series.map((s) => (
          <path key={s.nom} d={line<[number, number]>().x((p) => x(p[0])).y((p) => y(p[1]))(s.points) ?? ""}
            fill="none" stroke={s.couleur} strokeWidth={2} strokeDasharray={s.pointille ? "5 4" : undefined} />
        ))}
        {series.map((s, k) => {
          const p = s.points[s.points.length - 1];
          return p && (
            <g key={`fin-${s.nom}`}>
              <circle cx={x(p[0])} cy={y(p[1])} r={4.5} fill={s.couleur} stroke="var(--surface)" strokeWidth={2} />
              {libelleFin && <text x={x(p[0]) - 8} y={yLibelles[k] - 10} textAnchor="end" fontSize={12} fontWeight={600} fill="var(--encre)">{libelleFin(s, p)}</text>}
            </g>
          );
        })}
        {repere && (
          <g>
            <circle cx={x(repere.x)} cy={y(repere.y)} r={4.5} fill="var(--femme)" stroke="var(--surface)" strokeWidth={2} />
            <text x={x(repere.x) + 7} y={y(repere.y) - 7} fontSize={11} fill="var(--encre-2)">{repere.libelle}</text>
          </g>
        )}
        {survol && <line x1={x(survol.annee)} x2={x(survol.annee)} y1={m.h} y2={hauteur - m.b} stroke="var(--trait-fort)" />}
      </svg>
      <Infobulle bulle={survol && { x: survol.px, y: survol.py, contenu: infobulle(survol.annee) }} />
    </div>
  );
}

export function Legende({ elements }: { elements: { nom: string; couleur: string; pointille?: boolean; carre?: boolean }[] }) {
  return (
    <div className="mt-2 flex flex-wrap gap-x-4 gap-y-1 text-[0.82rem] text-encre-2">
      {elements.map((e) => (
        <span key={e.nom} className="inline-flex items-center gap-1.5">
          {e.carre
            ? <i className="inline-block h-2.5 w-2.5 rounded-sm" style={{ background: e.couleur }} />
            : <i className="inline-block w-5 border-t-2" style={{ borderColor: e.couleur, borderTopStyle: e.pointille ? "dashed" : "solid" }} />}
          {e.nom}
        </span>
      ))}
    </div>
  );
}

export const formatEntier = entier;
