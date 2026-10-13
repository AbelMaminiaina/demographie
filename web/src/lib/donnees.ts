import type { Base, Contours, Niveau, Unite } from "./types";

const URL_DONNEES = `${import.meta.env.BASE_URL}donnees/`;

async function lire<T>(fichier: string): Promise<T> {
  const r = await fetch(URL_DONNEES + fichier);
  if (!r.ok) throw new Error(`${fichier} : ${r.status} ${r.statusText}`);
  return r.json() as Promise<T>;
}

export function chargerBase(): Promise<Base> {
  return lire<Base>("base.json");
}

/** Attributs des fokontany ; la région et le district se déduisent de la commune. */
export async function chargerFokontany(communes: Unite[]): Promise<Unite[]> {
  const { unites } = await lire<{ unites: Unite[] }>("fokontany.json");
  for (const u of unites) {
    const c = communes[u.c!];
    u.di = c.di;
    u.r = c.r;
    u.d = u.s > 0 ? u.p / u.s : null;
  }
  return unites;
}

/** Contours d'un niveau. Ceux des fokontany sont compressés : entiers, écarts entre points successifs. */
export async function chargerContours(niveau: Niveau): Promise<Contours> {
  if (niveau !== "fokontany") {
    const geo = await lire<Contours>(`contours_${niveau}.json`);
    geo.features.forEach((f, i) => { f.id = i; });
    return geo;
  }
  const { echelle, anneaux } = await lire<{ echelle: number; anneaux: number[][][] }>("contours_fokontany.json");
  return {
    type: "FeatureCollection",
    features: anneaux.map((polygones, i) => ({
      type: "Feature",
      id: i,
      properties: { i },
      geometry: {
        type: "MultiPolygon",
        coordinates: polygones.map((plat) => {
          const pts: [number, number][] = [];
          let x = 0, y = 0;
          for (let k = 0; k < plat.length; k += 2) {
            x += plat[k];
            y += plat[k + 1];
            pts.push([x / echelle, y / echelle]);
          }
          return [pts];
        }),
      },
    })),
  };
}

/** Rectangle englobant d'un contour, pour centrer la carte dessus. */
export function boite(f: GeoJSON.Feature<GeoJSON.MultiPolygon | GeoJSON.Polygon>): [[number, number], [number, number]] {
  let x0 = Infinity, y0 = Infinity, x1 = -Infinity, y1 = -Infinity;
  const polygones = f.geometry.type === "Polygon" ? [f.geometry.coordinates] : f.geometry.coordinates;
  for (const poly of polygones) for (const [x, y] of poly[0]) {
    if (x < x0) x0 = x; if (x > x1) x1 = x; if (y < y0) y0 = y; if (y > y1) y1 = y;
  }
  return [[x0, y0], [x1, y1]];
}
