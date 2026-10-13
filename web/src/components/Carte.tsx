import { Map as CarteMapLibre, NavigationControl, setWorkerUrl, type ExpressionSpecification, type StyleSpecification } from "maplibre-gl";
// Le calcul des tuiles se fait dans un « worker » : Vite le compile et en donne l'adresse
import adresseWorker from "maplibre-gl/dist/maplibre-gl-worker.mjs?worker&url";

setWorkerUrl(adresseWorker);
import { useEffect, useRef, useState } from "react";
import { useLangue } from "../i18n";
import { boite } from "../lib/donnees";
import type { Contours, Niveau, Selection } from "../lib/types";
import { NIVEAUX } from "../lib/types";

// Fonds de carte vectoriels gratuits (CARTO, données OpenStreetMap), sans clé d'accès
const FONDS = {
  clair: "https://basemaps.cartocdn.com/gl/positron-gl-style/style.json",
  sombre: "https://basemaps.cartocdn.com/gl/dark-matter-gl-style/style.json",
};
const MADAGASCAR: [[number, number], [number, number]] = [[42.9, -25.8], [50.8, -11.8]];

const jeton = (nom: string) => getComputedStyle(document.documentElement).getPropertyValue(nom).trim();

function styleVide(): StyleSpecification {
  return { version: 8, sources: {}, layers: [{ id: "fond", type: "background", paint: { "background-color": jeton("--surface-2") } }] };
}

const EPAISSEUR: Record<Niveau, ExpressionSpecification | number> = {
  regions: 1.2,
  districts: 0.7,
  communes: ["interpolate", ["linear"], ["zoom"], 5, 0.15, 9, 0.6],
  fokontany: ["interpolate", ["linear"], ["zoom"], 6, 0, 9, 0.3, 12, 0.8],
};

export interface Survol { niveau: Niveau; i: number; x: number; y: number }

export function Carte({ niveau, contours, couleurs, selection, centrage, sombre, fondActif, onSurvol, onChoisir }: {
  niveau: Niveau;
  contours: Partial<Record<Niveau, Contours>>;
  couleurs: string[] | null;
  selection: Selection | null;
  centrage: number;               // change à chaque demande de recentrage sur la sélection
  sombre: boolean;
  fondActif: boolean;
  onSurvol: (s: Survol | null) => void;
  onChoisir: (s: Selection) => void;
}) {
  const { t } = useLangue();
  const conteneur = useRef<HTMLDivElement>(null);
  const carte = useRef<CarteMapLibre | null>(null);
  const [styleCharge, setStyleCharge] = useState(0);   // incrémenté à chaque (re)chargement du style
  const [fondEnErreur, setFondEnErreur] = useState(false);
  const etat = useRef({ niveau, onSurvol, onChoisir, survol: null as number | null, choisi: null as Selection | null });
  // Vrai entre l'événement « style.load » et le prochain changement de style. On ne peut pas se fier à
  // isStyleLoaded(), qui reste faux tant que les tuiles du fond de carte se chargent.
  const stylePret = useRef(false);
  etat.current.niveau = niveau;
  etat.current.onSurvol = onSurvol;
  etat.current.onChoisir = onChoisir;

  const styleVoulu = () => (fondActif && !fondEnErreur ? FONDS[sombre ? "sombre" : "clair"] : styleVide());

  // Création de la carte
  useEffect(() => {
    const m = new CarteMapLibre({
      container: conteneur.current!, style: styleVoulu(), bounds: MADAGASCAR, fitBoundsOptions: { padding: 24 },
      attributionControl: { compact: true }, dragRotate: false, pitchWithRotate: false, touchPitch: false,
    });
    m.addControl(new NavigationControl({ showCompass: false }), "top-right");
    m.on("style.load", () => { stylePret.current = true; setStyleCharge((n) => n + 1); });
    m.on("error", (e) => {
      // Erreur avant le chargement du style : fond de carte injoignable, on bascule sur un fond uni
      if (!stylePret.current) setFondEnErreur(true);
      console.warn("Carte :", e.error?.message);
    });
    const premiereCouche = (nom: string) => `fill-${nom}`;
    m.on("mousemove", (e) => {
      const n = etat.current.niveau;
      if (!m.getLayer(premiereCouche(n))) return;
      const f = m.queryRenderedFeatures(e.point, { layers: [premiereCouche(n)] })[0];
      const i = f ? Number(f.id) : null;
      const source = `src-${n}`;
      if (etat.current.survol !== i) {
        if (etat.current.survol != null) m.setFeatureState({ source, id: etat.current.survol }, { survol: false });
        if (i != null) m.setFeatureState({ source, id: i }, { survol: true });
        etat.current.survol = i;
      }
      m.getCanvas().style.cursor = i != null ? "pointer" : "";
      etat.current.onSurvol(i == null ? null : { niveau: n, i, x: e.originalEvent.clientX, y: e.originalEvent.clientY });
    });
    m.on("mouseout", () => etat.current.onSurvol(null));
    m.on("click", (e) => {
      const n = etat.current.niveau;
      if (!m.getLayer(premiereCouche(n))) return;
      const f = m.queryRenderedFeatures(e.point, { layers: [premiereCouche(n)] })[0];
      if (f) etat.current.onChoisir({ niveau: n, i: Number(f.id) });
    });
    carte.current = m;
    return () => { m.remove(); carte.current = null; };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Changement de thème ou de fond : nouveau style, les couches sont ensuite recréées
  useEffect(() => {
    if (!carte.current || !stylePret.current) return;
    stylePret.current = false;
    carte.current.setStyle(styleVoulu(), { diff: false });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [sombre, fondActif, fondEnErreur]);

  // Sources et couches de chaque découpage chargé, sous les noms de lieux du fond de carte
  useEffect(() => {
    const m = carte.current;
    if (!m || !stylePret.current) return;
    const premierSymbole = m.getStyle().layers.find((l) => l.type === "symbol")?.id;
    for (const n of NIVEAUX) {
      const geo = contours[n];
      if (!geo || m.getSource(`src-${n}`)) continue;
      m.addSource(`src-${n}`, { type: "geojson", data: geo, generateId: false });
      m.addLayer({ id: `fill-${n}`, type: "fill", source: `src-${n}`, layout: { visibility: "none" },
        paint: { "fill-color": ["to-color", ["coalesce", ["feature-state", "couleur"], jeton("--vide")]],
                 "fill-opacity": fondActif && !fondEnErreur ? 0.85 : 1 } }, premierSymbole);
      m.addLayer({ id: `ligne-${n}`, type: "line", source: `src-${n}`, layout: { visibility: "none" },
        paint: { "line-color": jeton("--surface"), "line-width": EPAISSEUR[n] } }, premierSymbole);
      m.addLayer({ id: `select-${n}`, type: "line", source: `src-${n}`, layout: { visibility: "none" },
        paint: { "line-color": jeton("--selection"),
                 "line-width": ["case", ["boolean", ["feature-state", "choisi"], false], 2.6,
                                ["boolean", ["feature-state", "survol"], false], 1.6, 0] } });
    }
    if (contours.regions && !m.getLayer("contour-regions")) {
      m.addLayer({ id: "contour-regions", type: "line", source: "src-regions",
        paint: { "line-color": jeton("--encre"), "line-opacity": 0.45, "line-width": 0.9 } }, premierSymbole);
    }
  }, [contours, styleCharge, fondActif, fondEnErreur]);

  // Seul le découpage choisi est visible ; les limites de régions restent en repère
  useEffect(() => {
    const m = carte.current;
    if (!m || !stylePret.current) return;
    for (const n of NIVEAUX) for (const c of ["fill", "ligne", "select"]) {
      if (m.getLayer(`${c}-${n}`)) m.setLayoutProperty(`${c}-${n}`, "visibility", n === niveau ? "visible" : "none");
    }
    if (m.getLayer("contour-regions")) m.setLayoutProperty("contour-regions", "visibility", niveau === "regions" ? "none" : "visible");
  }, [niveau, contours, styleCharge]);

  // Couleurs de l'indicateur, appliquées unité par unité
  useEffect(() => {
    const m = carte.current;
    if (!m || !couleurs || !m.getSource(`src-${niveau}`)) return;
    const source = `src-${niveau}`;
    couleurs.forEach((couleur, i) => m.setFeatureState({ source, id: i }, { couleur }));
  }, [couleurs, niveau, contours, styleCharge]);

  // Unité choisie : contour épais, et recentrage quand il est demandé
  useEffect(() => {
    const m = carte.current;
    if (!m) return;
    const avant = etat.current.choisi;
    if (avant && m.getSource(`src-${avant.niveau}`)) m.setFeatureState({ source: `src-${avant.niveau}`, id: avant.i }, { choisi: false });
    if (selection && m.getSource(`src-${selection.niveau}`)) m.setFeatureState({ source: `src-${selection.niveau}`, id: selection.i }, { choisi: true });
    etat.current.choisi = selection;
  }, [selection, contours, styleCharge]);

  useEffect(() => {
    const m = carte.current;
    if (!m || !centrage) return;
    if (!selection) { m.fitBounds(MADAGASCAR, { padding: 24, duration: 600 }); return; }
    const f = contours[selection.niveau]?.features[selection.i];
    if (f) m.fitBounds(boite(f), { padding: 80, maxZoom: 13, duration: 800 });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [centrage, contours]);

  return (
    <div className="relative h-full w-full">
      {/* Hauteur explicite : MapLibre impose « position: relative » au conteneur, ce qui annulerait un « absolute inset-0 » */}
      <div ref={conteneur} className="h-full w-full" />
      {!contours[niveau] && (
        <div className="absolute inset-0 grid place-items-center text-sm text-encre-2">{t("chargementContours")}</div>
      )}
      {fondEnErreur && fondActif && (
        <p className="absolute bottom-2 left-2 rounded-md bg-surface/90 px-2 py-1 text-xs text-encre-2">{t("fondIndisponible")}</p>
      )}
    </div>
  );
}
