import { useEffect, type ReactNode } from "react";
import { useLangue } from "../i18n";
import type { Cle } from "../i18n/fr";
import { croissance } from "../lib/indicateurs";
import { compact, dateLongue, densite, entier, nombre, pct } from "../lib/format";
import type { Base, Contours, Niveau, Recensement, Selection, Unite } from "../lib/types";
import { Courbes } from "./Graphiques";

/** Niveaux pour lesquels une fiche imprimable existe. */
export const ADRESSE_SITE = "https://abelmaminiaina.github.io/demographie/";

export const NIVEAUX_FICHE: Niveau[] = ["regions", "districts", "communes"];


/** Colonne du tableau de comparaison : le territoire, ses parents, puis le pays. */
interface Colonne { nom: string; rg?: Recensement; wp: number[]; s: number; p?: number }

export function Bloc({ titre, children }: { titre: string; children: ReactNode }) {
  // Mise en page en blocs (et non en grille) : Chrome découpe mal les grilles entre deux pages
  return (
    <section className="bloc-fiche border-t border-trait pt-3">
      <h2 className="etiquette m-0">{titre}</h2>
      {children}
    </section>
  );
}

const anneaux = (g: GeoJSON.Geometry | undefined): number[][][] =>
  !g ? [] : g.type === "Polygon" ? g.coordinates : g.type === "MultiPolygon" ? g.coordinates.flat() : [];

/** Carte en projection équirectangulaire : `fond` en gris, `cibles` en couleur, cadrée sur `cadre`
 * (par défaut le fond entier), sans bibliothèque cartographique. */
export function Situation({ fond, cibles, cadre, largeur = 150 }: {
  fond: GeoJSON.Feature[]; cibles: (GeoJSON.Feature | undefined)[]; cadre?: GeoJSON.Feature[]; largeur?: number;
}) {
  const points = (cadre ?? fond).flatMap((f) => anneaux(f.geometry)).flat();
  const lon = points.map((c) => c[0]), lat = points.map((c) => c[1]);
  let [x0, x1, y0, y1] = [Math.min(...lon), Math.max(...lon), Math.min(...lat), Math.max(...lat)];
  if (cadre) {   // marge autour d'une zone, pour voir son voisinage
    const m = Math.max(x1 - x0, y1 - y0) * 0.15 + 0.02;
    [x0, x1, y0, y1] = [x0 - m, x1 + m, y0 - m, y1 + m];
  }
  const k = Math.cos((((y0 + y1) / 2) * Math.PI) / 180);
  const L = largeur, H = (L * (y1 - y0)) / ((x1 - x0) * k);
  const dedans = (f: GeoJSON.Feature) => anneaux(f.geometry).some((a) => a.some(([x, y]) => x >= x0 && x <= x1 && y >= y0 && y <= y1));
  const chemin = (g: GeoJSON.Geometry | undefined) => anneaux(g).map((a) => "M" + a.map(
    ([x, y]) => `${((x - x0) / (x1 - x0)) * L},${((y1 - y) / (y1 - y0)) * H}`).join("L") + "Z").join("");
  return (
    <svg viewBox={`0 0 ${L} ${H}`} className="block h-auto w-full overflow-hidden" role="img" aria-hidden="true">
      {fond.filter((f) => !cadre || dedans(f)).map((f, i) => (
        <path key={i} d={chemin(f.geometry)} fill="var(--vide)" stroke="var(--surface)" strokeWidth={cadre ? 0.6 : 0.4} />
      ))}
      {cibles.map((f, i) => f && <path key={`c${i}`} d={chemin(f.geometry)} fill="var(--accent)" stroke="var(--encre)" strokeWidth={0.5} />)}
    </svg>
  );
}

/** Barre au-dessus d'une feuille imprimable (masquée à l'impression). */
export function BarreImpression() {
  const { t } = useLangue();
  return (
    <div className="ecran-seul mx-auto mb-4 flex max-w-[210mm] flex-wrap items-center gap-3 px-4">
      <a href="#" className="rounded-lg px-2 py-1 text-sm text-accent underline underline-offset-2">← {t("ficheRetour")}</a>
      <button type="button" onClick={() => window.print()}
        className="cursor-pointer rounded-lg border-0 px-4 py-2 text-sm font-semibold text-white" style={{ background: "var(--accent)" }}>
        {t("ficheEnregistrer")}
      </button>
      <span className="text-[0.82rem] text-discret">{t("ficheAideImpression")}</span>
    </div>
  );
}

/** Titre de la page (nom proposé pour le PDF), rétabli à la fermeture. */
export function useTitre(titre: string) {
  useEffect(() => {
    const avant = document.title;
    document.title = titre;
    window.scrollTo(0, 0);
    return () => { document.title = avant; };
  }, [titre]);
}

export function FicheTerritoire({ base, unites, contours, selection, fokontanyParCommune }: {
  base: Base; unites: Record<Niveau, Unite[] | null>; contours: Partial<Record<Niveau, Contours>>;
  selection: Selection; fokontanyParCommune: number[][] | null;
}) {
  const { t, langue } = useLangue();
  const meta = base.meta;
  const { niveau, i } = selection;
  const u = unites[niveau]![i];
  const R = base.niveaux.regions, D = base.niveaux.districts, C = base.niveaux.communes;
  const AN = Math.min(new Date().getFullYear(), meta.annees_wp[meta.annees_wp.length - 1]);
  const FIN = meta.annees_wp[meta.annees_wp.length - 1];
  const iAn = meta.annees_wp.indexOf(AN);
  const aujourdhui = dateLongue(new Date(), langue);
  const titre = `${t("ficheTitre")} – ${u.n}`;

  useTitre(titre);

  // Colonnes de comparaison : territoire, district et région de rattachement, pays
  const region = niveau === "regions" ? null : R[u.r!];
  const district = niveau === "communes" ? D[u.di!] : null;
  const colonne = (x: Unite): Colonne => ({ nom: x.n, rg: x.rg, wp: x.wp, s: x.s, p: x.p });
  const pays: Colonne = {
    nom: "Madagascar", rg: meta.rg_national, s: R.reduce((a, r) => a + r.s, 0),
    wp: meta.annees_wp.map((_, j) => R.reduce((a, r) => a + r.wp[j], 0)),
  };
  const colonnes = [colonne(u), ...(district ? [colonne(district)] : []), ...(region ? [colonne(region)] : []), pays];
  const cr = (c: Colonne) => {
    const a = c.wp[meta.annees_wp.indexOf(meta.annee_ref)], b = c.wp[iAn];
    return a && b ? (Math.pow(b / a, 1 / (AN - meta.annee_ref)) - 1) * 100 : null;
  };
  const lignes: [string, (c: Colonne) => string, boolean?][] = [
    [t("ligne.p"), (c) => entier(c.rg?.p)],
    [t("ligne.d"), (c) => densite(c.rg?.d ?? (c.rg && c.s > 0 ? c.rg.p / c.s : null))],
    [t("ligne.u"), (c) => pct(c.rg?.u)],
    [t("ligne.rm"), (c) => nombre(c.rg?.rm, 1)],
    [t("ligne.m"), (c) => entier(c.rg?.m)],
    [t("ligne.t"), (c) => nombre(c.rg?.t, 1)],
    [t("ligne.tu"), (c) => nombre(c.rg?.tu, 1), true],
    [t("ligne.tr"), (c) => nombre(c.rg?.tr, 1), true],
    [t("ligne.th"), (c) => nombre(c.rg?.th, 1), true],
    [t("ligne.tf"), (c) => nombre(c.rg?.tf, 1), true],
    [t("ligne.f"), (c) => pct(c.rg?.f)],
    [t("ligne.wp", { annee: AN }), (c) => entier(c.wp[iAn])],
    [t("ligne.wp", { annee: FIN }), (c) => entier(c.wp[c.wp.length - 1])],
    [t("ligne.cr", { annee: AN }), (c) => pct(cr(c))],
  ];
  // Une ligne sans aucune valeur (ex. hommes pour 100 femmes d'une commune) n'est affichée que si elle a du sens ailleurs
  const lignesUtiles = lignes.filter(([, f]) => colonnes.some((c) => f(c) !== "n.d."));

  // Rangs par population recensée
  const freres = niveau === "regions" ? R : niveau === "districts" ? D.filter((d) => d.r === u.r) : C.filter((c) => c.di === u.di);
  const rang = (liste: Unite[]) => {
    const tri = liste.filter((x) => x.rg).sort((a, b) => b.rg!.p - a.rg!.p);
    return { r: tri.indexOf(u) + 1, n: tri.length };
  };
  const unitesNom = t(`niveau.${niveau}` as Cle).toLowerCase();
  const rangs: string[] = [];
  if (u.rg) {
    if (niveau !== "communes") rangs.push(t("ficheRangNational", { ...rang(niveau === "regions" ? R : D), unites: unitesNom }));
    if (niveau !== "regions") rangs.push(t("ficheRangParent", { ...rang(freres), unites: unitesNom,
      parent: `${t(niveau === "communes" ? "unite.districts" : "unite.regions").toLowerCase()} ${(district ?? region)!.n}` }));
  }

  // Sous-unités : districts d'une région, communes d'un district, fokontany d'une commune
  const sousNiveau: Niveau = niveau === "regions" ? "districts" : niveau === "districts" ? "communes" : "fokontany";
  const sous: Unite[] | null = niveau === "regions" ? D.filter((d) => d.r === i)
    : niveau === "districts" ? C.filter((c) => c.di === i)
    : fokontanyParCommune && unites.fokontany ? (fokontanyParCommune[i] ?? []).map((j) => unites.fokontany![j]) : null;
  const sousTries = sous && [...sous].sort((a, b) => (b.rg?.p ?? b.ca ?? b.p) - (a.rg?.p ?? a.ca ?? a.p));

  const cible = contours[niveau]?.features[i];
  const ref = u.rg ? u.rg.p : u.p;
  const chiffres: [string, string][] = [
    [u.rg ? entier(u.rg.p) : entier(u.p), u.rg ? t("habitantsRecenses") : t("habitantsHdx")],
    [entier(u.wp[iAn]), t("estimesEn", { annee: AN })],
    [entier(u.wp[u.wp.length - 1]), t("estimesEn", { annee: FIN })],
    [u.rg?.m != null ? entier(u.rg.m) : "n.d.", t("ligne.m").toLowerCase()],
    [u.rg?.t != null ? nombre(u.rg.t, 1) : "n.d.", t("ligne.t").toLowerCase()],
    [pct(croissance(u, AN, meta)), t("croissanceDepuis")],
  ];

  const cellule = "border-b border-trait px-2 py-1";
  return (
    <div className="papier min-h-screen py-6">
      <BarreImpression />

      <article className="feuille">
        <header className="grid grid-cols-[minmax(0,1fr)_110px] items-start gap-4">
          <div>
            <p className="etiquette m-0">{t("ficheTitre")} · {t(`unite.${niveau}` as Cle)}</p>
            <h1 className="m-0 text-[1.9rem] font-bold leading-tight">{u.n}</h1>
            <p className="m-0 text-encre-2">
              {[district?.n && `${t("unite.districts")} ${district.n}`, region && `${t("unite.regions")} ${region.n}`, "Madagascar"]
                .filter(Boolean).join(" · ")}
            </p>
            <p className="m-0 mt-1 text-[0.8rem] text-discret">
              {t("ficheEdition", { date: aujourdhui, collecte: meta.collecte ? dateLongue(new Date(meta.collecte), langue) : "n.d." })}
            </p>
          </div>
          {contours.regions && <Situation fond={contours.regions.features} cibles={[cible]} />}
        </header>

        <Bloc titre={t("ficheChiffresCles")}>
          <div className="grid grid-cols-3 gap-x-4 gap-y-3">
            {chiffres.map(([v, l]) => (
              <div key={l}>
                <div className="chiffre text-[1.2rem] leading-tight">{v}</div>
                <div className="text-[0.76rem] leading-snug text-discret">{l}</div>
              </div>
            ))}
          </div>
          {rangs.map((r) => <p key={r} className="m-0 text-[0.86rem] text-encre-2">{r}</p>)}
          {!u.rg && <p className="m-0 text-[0.82rem] text-discret">{t("pasDeCorrespondance")}</p>}
          {u.rg?.id === false && <p className="m-0 text-[0.82rem] text-discret">{t("decoupageChange")}</p>}
        </Bloc>

        <Bloc titre={t("ficheComparaison")}>
          <table className="w-full border-collapse text-[0.84rem]">
            <thead>
              <tr>
                <th className={`${cellule} text-left font-semibold`}>{t("ficheIndicateur")}</th>
                {colonnes.map((c, k) => (
                  <th key={c.nom + k} className={`${cellule} text-right font-semibold ${k === 0 ? "text-accent" : ""}`}>{c.nom}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {lignesUtiles.map(([nom, f, retrait]) => (
                <tr key={nom}>
                  <td className={`${cellule} ${retrait ? "pl-5 text-encre-2" : ""}`}>{nom}</td>
                  {colonnes.map((c, k) => (
                    <td key={c.nom + k} className={`${cellule} chiffre text-right ${k === 0 ? "font-semibold" : ""}`}>{f(c)}</td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </Bloc>

        <Bloc titre={t("evolution", { debut: meta.annees_wp[0], fin: FIN })}>
          <Courbes hauteur={190} series={[{ nom: "wp", couleur: "var(--accent)", points: meta.annees_wp.map((a, j) => [a, u.wp[j]]) }]}
            repere={{ x: meta.annee_ref, y: ref, libelle: u.rg ? t("pointRecensement") : t("pointHdx") }}
            infobulle={(a) => <>{entier(u.wp[meta.annees_wp.indexOf(a)])}</>} formatY={compact} />
          <p className="m-0 text-[0.78rem] text-discret">{t("note.wp")}</p>
        </Bloc>

        {(region ?? u).dhs && (
          <Bloc titre={niveau === "regions" ? meta.enquete_dhs : t("dhsRegion", { enquete: meta.enquete_dhs, region: region!.n })}>
            <table className="w-full border-collapse text-[0.84rem]">
              <tbody>
                {Object.keys(meta.noms_dhs).map((cle) => {
                  const v = (region ?? u).dhs?.[cle];
                  const valeurs = R.map((r) => r.dhs?.[cle]).filter((x): x is number => x != null);
                  if (v == null) return null;
                  return (
                    <tr key={cle}>
                      <td className={cellule}>{t(`dhs.${cle}` as Cle)}</td>
                      <td className={`${cellule} chiffre text-right font-semibold`}>{nombre(v, Number.isInteger(v) ? 0 : 1)}</td>
                      <td className={`${cellule} chiffre text-right text-discret`}>
                        {t("ficheEtendue", { min: nombre(Math.min(...valeurs), 1), max: nombre(Math.max(...valeurs), 1) })}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
            <p className="m-0 text-[0.78rem] text-discret">{t("note.dhs", { enquete: meta.enquete_dhs })}</p>
          </Bloc>
        )}

        <Bloc titre={`${t(`niveau.${sousNiveau}` as Cle)} · ${u.n}${sous ? ` (${sous.length})` : ""}`}>
          {!sousTries ? <p className="m-0 text-[0.84rem] text-discret">{t("ficheChargementFokontany")}</p> : (
            <table className="w-full border-collapse text-[0.8rem]">
              <thead>
                <tr>
                  <th className={`${cellule} text-left font-semibold`}>{t("col.nom")}</th>
                  {sousNiveau === "fokontany" ? (
                    <>
                      <th className={`${cellule} text-right font-semibold`}>{t("col.calee")}</th>
                      <th className={`${cellule} text-right font-semibold`}>{t("col.estime", { annee: AN })}</th>
                      <th className={`${cellule} text-right font-semibold`}>{t("km2")}</th>
                    </>
                  ) : (
                    <>
                      <th className={`${cellule} text-right font-semibold`}>{t("col.recense")}</th>
                      <th className={`${cellule} text-right font-semibold`}>{t("col.urbain")}</th>
                      <th className={`${cellule} text-right font-semibold`}>{t("col.menages")}</th>
                      <th className={`${cellule} text-right font-semibold`}>{t("col.taille")}</th>
                      <th className={`${cellule} text-right font-semibold`}>{t("col.estime", { annee: AN })}</th>
                    </>
                  )}
                </tr>
              </thead>
              <tbody>
                {sousTries.map((x, k) => (
                  <tr key={x.n + k}>
                    <td className={cellule}>{x.n}</td>
                    {sousNiveau === "fokontany" ? (
                      <>
                        <td className={`${cellule} chiffre text-right`}>{entier(x.ca ?? x.p)}</td>
                        <td className={`${cellule} chiffre text-right`}>{entier(x.wp[iAn])}</td>
                        <td className={`${cellule} chiffre text-right`}>{nombre(x.s, x.s < 10 ? 1 : 0)}</td>
                      </>
                    ) : (
                      <>
                        <td className={`${cellule} chiffre text-right`}>{entier(x.rg?.p)}</td>
                        <td className={`${cellule} chiffre text-right`}>{pct(x.rg?.u, 0)}</td>
                        <td className={`${cellule} chiffre text-right`}>{entier(x.rg?.m)}</td>
                        <td className={`${cellule} chiffre text-right`}>{nombre(x.rg?.t, 1)}</td>
                        <td className={`${cellule} chiffre text-right`}>{entier(x.wp[iAn])}</td>
                      </>
                    )}
                  </tr>
                ))}
              </tbody>
            </table>
          )}
          {sousNiveau === "fokontany" && <p className="m-0 text-[0.78rem] text-discret">{t("troisEstimations")} {t("note.ca")}</p>}
          {sousNiveau === "communes" && <p className="m-0 text-[0.78rem] text-discret">{t("ficheNoteCommunes")}</p>}
        </Bloc>

        <Bloc titre={t("ficheSources")}>
          <ul className="m-0 grid gap-1 pl-5 text-[0.8rem] text-encre-2">
            <li>{t("ficheSourceRgph")}</li>
            <li>{t("ficheSourceWp")}</li>
            <li>{t("ficheSourceDhs", { enquete: meta.enquete_dhs })}</li>
            {niveau === "communes" && <li>{t("ficheLimiteDensite")}</li>}
          </ul>
          <p className="m-0 text-[0.8rem]">{t("ficheCitation", { titre, date: aujourdhui, url: ADRESSE_SITE })}</p>
        </Bloc>
      </article>
    </div>
  );
}
