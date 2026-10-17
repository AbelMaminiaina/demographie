import { Map as CarteMapLibre, NavigationControl, Popup, setWorkerUrl, type ExpressionSpecification, type StyleSpecification } from "maplibre-gl";
// Le calcul des tuiles se fait dans un « worker » : Vite le compile et en donne l'adresse
import adresseWorker from "maplibre-gl/dist/maplibre-gl-worker.mjs?worker&url";

setWorkerUrl(adresseWorker);
import { useEffect, useRef, useState } from "react";
import { useLangue } from "../i18n";
import type { Cle } from "../i18n/fr";
import { boite, type CoucheId, type PointCarte } from "../lib/donnees";
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

/** Couches de points : couleur par catégorie (jetons CSS) et légende, reprise sous la carte. */
export const COUCHES: Record<CoucheId, { couleurs: string[]; legende: { couleur: string; cle: Cle }[]; libelle: string;
  rayon: [number, number, number, number]; gros: ExpressionSpecification }> = {
  // Santé : centre, poste, hôpital ; les hôpitaux sont plus gros
  sante: { couleurs: ["--serie-3", "--serie-4", "--femme"], libelle: "sante.type.", rayon: [2.4, 4, 6, 9], gros: ["==", ["get", "t"], 2],
    legende: [{ couleur: "--serie-3", cle: "sante.type.0" }, { couleur: "--serie-4", cle: "sante.type.1" }, { couleur: "--femme", cle: "sante.type.2" }] },
  // Écoles : primaire, collège, lycée, supérieur, préscolaire, niveau non précisé
  // (sans bleu, couleur des découpages, ni les couleurs de la santé)
  // Les universités publiques (supérieur et public) sont plus grosses
  ecoles: { couleurs: ["--serie-5", "--d7", "--d7", "--encre", "--serie-5", "--discret"], libelle: "ecole.niveau.", rayon: [2, 5, 5, 11],
    gros: ["all", ["==", ["get", "t"], 3], ["==", ["get", "s"], 1]],
    legende: [{ couleur: "--serie-5", cle: "ecole.legende.0" }, { couleur: "--d7", cle: "ecole.legende.1" },
              { couleur: "--encre", cle: "ecole.legende.2" }, { couleur: "--discret", cle: "ecole.legende.3" }] },
};
export interface Couche { points: PointCarte[] | null; visible: boolean; publiquesSeules?: boolean }

export function Carte({ niveau, contours, couleurs, selection, zone, centrage, sombre, fondActif, couches, onSurvol, onChoisir }: {
  niveau: Niveau;
  contours: Partial<Record<Niveau, Contours>>;
  couleurs: string[] | null;
  selection: Selection | null;
  zone: { niveau: Niveau; indices: number[] } | null;   // unités de la zone d'intervention, surlignées
  centrage: number;               // change à chaque demande de recentrage sur la sélection
  sombre: boolean;
  fondActif: boolean;
  couches: Record<CoucheId, Couche>;   // équipements en points, chargés à la première demande
  onSurvol: (s: Survol | null) => void;
  onChoisir: (s: Selection) => void;
}) {
  const { t } = useLangue();
  const conteneur = useRef<HTMLDivElement>(null);
  const carte = useRef<CarteMapLibre | null>(null);
  const [styleCharge, setStyleCharge] = useState(0);   // incrémenté à chaque (re)chargement du style
  const [fondEnErreur, setFondEnErreur] = useState(false);
  const etat = useRef({ niveau, onSurvol, onChoisir, t, survol: null as number | null, choisi: null as Selection | null,
    zone: null as { niveau: Niveau; indices: number[] } | null });
  // Vrai entre l'événement « style.load » et le prochain changement de style. On ne peut pas se fier à
  // isStyleLoaded(), qui reste faux tant que les tuiles du fond de carte se chargent.
  const stylePret = useRef(false);
  etat.current.niveau = niveau;
  etat.current.onSurvol = onSurvol;
  // L'infobulle suit le pointeur en position fixe : on la retire dès que la page défile
  useEffect(() => {
    const cacher = () => etat.current.onSurvol(null);
    window.addEventListener("scroll", cacher, { passive: true });
    return () => window.removeEventListener("scroll", cacher);
  }, []);
  etat.current.onChoisir = onChoisir;
  etat.current.t = t;

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
      // Écran tactile : pas d'infobulle, elle resterait affichée faute de « sortie » de la souris
      if (matchMedia("(hover: none)").matches) return;
      etat.current.onSurvol(i == null ? null : { niveau: n, i, x: e.originalEvent.clientX, y: e.originalEvent.clientY });
    });
    m.on("mouseout", () => etat.current.onSurvol(null));
    // Équipement survolé : son nom et sa catégorie (texte inséré sans HTML)
    const bulle = new Popup({ closeButton: false, closeOnClick: false, offset: 8 });
    for (const id of Object.keys(COUCHES) as CoucheId[]) {
      m.on("mousemove", `points-${id}`, (e) => {
        const f = e.features?.[0];
        if (!f) return;
        const contenu = document.createElement("div");
        const nom = document.createElement("strong");
        nom.textContent = String(f.properties.n || "—");
        const statut = f.properties.s ? ` · ${etat.current.t(`ecole.statut.${f.properties.s}` as Cle)}` : "";
        contenu.append(nom, document.createElement("br"), etat.current.t(`${COUCHES[id].libelle}${f.properties.t}` as Cle) + statut);
        bulle.setLngLat((f.geometry as GeoJSON.Point).coordinates as [number, number]).setDOMContent(contenu).addTo(m);
      });
      m.on("mouseleave", `points-${id}`, () => bulle.remove());
    }
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
      m.addLayer({ id: `zone-${n}`, type: "line", source: `src-${n}`, layout: { visibility: "none" },
        paint: { "line-color": jeton("--femme"), "line-width": ["case", ["boolean", ["feature-state", "zone"], false], 2.4, 0] } });
    }
    if (contours.regions && !m.getLayer("contour-regions")) {
      m.addLayer({ id: "contour-regions", type: "line", source: "src-regions",
        paint: { "line-color": jeton("--encre"), "line-opacity": 0.45, "line-width": 0.9 } }, premierSymbole);
    }
  }, [contours, styleCharge, fondActif, fondEnErreur]);

  // Équipements : points au-dessus des découpages, une couleur par catégorie
  useEffect(() => {
    const m = carte.current;
    if (!m || !stylePret.current) return;
    for (const id of Object.keys(COUCHES) as CoucheId[]) {
      const { points, visible } = couches[id];
      if (!points || m.getSource(`src-${id}`)) continue;
      const { couleurs: c, rayon: [petit, grand, petitZoom, grandZoom], gros } = COUCHES[id];
      m.addSource(`src-${id}`, { type: "geojson", data: { type: "FeatureCollection", features: points.map(([x, y, t, n, s]) => (
        { type: "Feature", properties: { t, n, s: s ?? 0 }, geometry: { type: "Point", coordinates: [x, y] } })) } });
      // Rayon au zoom 5 puis 11 ; les points « gros » (hôpitaux, universités publiques) ressortent
      const rayon = (base: number, grosRayon: number): ExpressionSpecification => ["case", gros, grosRayon, base];
      m.addLayer({ id: `points-${id}`, type: "circle", source: `src-${id}`, layout: { visibility: visible ? "visible" : "none" },
        paint: {
          "circle-color": ["match", ["get", "t"], ...c.flatMap((j, k) => [k, jeton(j)]), jeton("--discret")] as unknown as ExpressionSpecification,
          "circle-radius": ["interpolate", ["linear"], ["zoom"], 5, rayon(petit, grand), 11, rayon(petitZoom, grandZoom)],
          "circle-stroke-color": jeton("--surface"), "circle-stroke-width": 0.8,
        } });
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [couches.sante.points, couches.ecoles.points, styleCharge]);
  useEffect(() => {
    const m = carte.current;
    for (const id of Object.keys(COUCHES) as CoucheId[]) {
      if (!m?.getLayer(`points-${id}`)) continue;
      m.setLayoutProperty(`points-${id}`, "visibility", couches[id].visible ? "visible" : "none");
      m.setFilter(`points-${id}`, couches[id].publiquesSeules ? ["==", ["get", "s"], 1] : null);
    }
  }, [couches, styleCharge]);

  // Seul le découpage choisi est visible ; les limites de régions restent en repère
  useEffect(() => {
    const m = carte.current;
    if (!m || !stylePret.current) return;
    for (const n of NIVEAUX) for (const c of ["fill", "ligne", "select", "zone"]) {
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

  // Zone d'intervention : contour de couleur sur chacune de ses unités
  useEffect(() => {
    const m = carte.current;
    if (!m) return;
    const marquer = (z: { niveau: Niveau; indices: number[] } | null, valeur: boolean) => {
      if (!z || !m.getSource(`src-${z.niveau}`)) return;
      for (const i of z.indices) m.setFeatureState({ source: `src-${z.niveau}`, id: i }, { zone: valeur });
    };
    marquer(etat.current.zone, false);
    marquer(zone, true);
    etat.current.zone = zone;
  }, [zone, contours, styleCharge]);

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
