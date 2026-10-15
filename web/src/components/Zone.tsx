import { useState } from "react";
import { useLangue } from "../i18n";
import type { Cle } from "../i18n/fr";
import { compact, dateLongue, densite, entier, nombre, pct } from "../lib/format";
import type { Base, Contours, Niveau, Unite } from "../lib/types";
import { telechargerCsv } from "../lib/csv";
import { adresseZone, resumer, type Resume, type Zone } from "../lib/zone";
import { ADRESSE_SITE, BarreImpression, Bloc, Situation, useTitre } from "./FicheTerritoire";
import { EstimationDate } from "./Estimation";
import { AppelDevis } from "./Services";
import { Courbes } from "./Graphiques";

/** Rattachement d'une unité, pour les listes : « district · région », ou le seul parent direct (`court`). */
function rattachement(base: Base, u: Unite, niveau: Niveau, court = false): string {
  const R = base.niveaux.regions, D = base.niveaux.districts, C = base.niveaux.communes;
  const parents = niveau === "regions" ? [] : niveau === "districts" ? [R[u.r!].n]
    : niveau === "communes" ? [D[u.di!].n, R[u.r!].n] : [C[u.c!].n, D[u.di!].n];
  return (court ? parents.slice(0, 1) : parents).join(" · ");
}

/** Population 2018 d'une unité : recensement, ou estimation calée (fokontany), sinon HDX. */
const pop2018 = (u: Unite, niveau: Niveau) => (niveau === "fokontany" ? u.ca ?? u.p : u.rg?.p);

function useNomZone(zone: Zone) {
  const { t } = useLangue();
  return zone.nom.trim() || t("zoneTitre");
}

/** Chiffres clés d'une zone, partagés par le panneau et la fiche imprimable. */
function chiffresZone(t: ReturnType<typeof useLangue>["t"], r: Resume, niveau: Niveau, an: number, fin: number): [string, string][] {
  const fk = niveau === "fokontany";
  const actuelle = r.wp[r.wp.length - 1 - (fin - an)];
  const tuiles: [string, string][] = [
    [entier(r.population2018), fk ? t("zonePop2018Calee") : t("habitantsRecenses")],
    [entier(actuelle), t("estimesEn", { annee: an })],
    [entier(r.wp[r.wp.length - 1]), t("estimesEn", { annee: fin })],
    [pct(r.croissance), t("croissanceDepuis")],
    [densite(actuelle / r.superficie), t("zoneDensite", { annee: an })],
  ];
  // Ménages et milieu : connus par le recensement, donc absents pour les fokontany
  if (!fk) tuiles.splice(3, 0,
    [r.menages != null ? entier(r.menages) : "n.d.", t("ligne.m").toLowerCase()],
    [nombre(r.taille, 1), t("ligne.t").toLowerCase()],
    [r.chefFemme != null ? pct(r.chefFemme, 0) : "n.d.", t("zoneChefFemme")],
    [r.urbain != null ? pct(r.urbain, 0) : "n.d.", t("populationUrbaine")]);
  return tuiles;
}

export function PanneauZone({ base, unitesNiveau, zone, niveauCarte, annee, onRetirer, onVider, onNom, onNiveau, onQuitter }: {
  base: Base; unitesNiveau: Unite[] | null; zone: Zone; niveauCarte: Niveau; annee: number;
  onRetirer: (i: number) => void; onVider: () => void; onNom: (nom: string) => void;
  onNiveau: (n: Niveau) => void; onQuitter: () => void;
}) {
  const { t } = useLangue();
  const [copie, setCopie] = useState(false);
  const [anneeEst, setAnneeEst] = useState(annee);
  const meta = base.meta;
  const FIN = meta.annees_wp[meta.annees_wp.length - 1];
  const unitesNom = t(`niveau.${zone.niveau}` as Cle).toLowerCase();
  const nom = useNomZone(zone);
  const vide = zone.indices.length === 0;
  const r = !vide && unitesNiveau ? resumer(base, unitesNiveau, zone, annee) : null;
  const iAn = meta.annees_wp.indexOf(annee);

  const exporter = () => {
    if (!r || !unitesNiveau) return;
    const fk = zone.niveau === "fokontany";
    const lignes = zone.indices.map((i) => unitesNiveau[i]).map((u) => [
      u.n, rattachement(base, u, zone.niveau), pop2018(u, zone.niveau) ?? null,
      fk ? null : u.rg?.m ?? null, fk ? null : u.rg?.t ?? null, fk ? null : u.rg?.f ?? null,
      u.s, u.wp[iAn], u.wp[u.wp.length - 1],
    ]);
    telechargerCsv(`${nom.replace(/[\\/:*?"<>|]+/g, "_")}.csv`, [
      [t("col.nom"), t("zoneRattachement"), fk ? t("col.calee") : t("col.recense"), t("col.menages"), t("col.taille"),
       t("ligne.f"), t("km2"), t("col.estime", { annee }), t("col.estime", { annee: FIN })],
      ...lignes,
      [t("zoneTotal"), "", r.population2018, r.menages, r.taille != null ? Math.round(r.taille * 100) / 100 : null,
       r.chefFemme != null ? Math.round(r.chefFemme * 10) / 10 : null, Math.round(r.superficie * 10) / 10,
       r.wp[iAn], r.wp[r.wp.length - 1]],
      [],
      [t("zoneSourcesCsv", { date: meta.collecte ?? "" })],
    ]);
  };

  const copier = async () => {
    const lien = window.location.href.split("#")[0] + adresseZone(zone, "zone");
    try { await navigator.clipboard.writeText(lien); setCopie(true); setTimeout(() => setCopie(false), 2000); }
    catch { window.prompt(t("zoneCopierLien"), lien); }
  };

  const bouton = "cursor-pointer rounded-lg border border-trait-fort bg-surface px-3 py-1.5 text-sm font-semibold text-accent hover:bg-accent-doux disabled:cursor-default disabled:opacity-50";
  return (
    <div className="grid gap-4">
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0 flex-1">
          <p className="etiquette m-0">{t("zoneTitre")}</p>
          <input value={zone.nom} onChange={(e) => onNom(e.target.value)} placeholder={t("zoneNomAide")} aria-label={t("zoneNomAide")}
            className="mt-1 w-full rounded-lg border border-trait bg-surface px-2 py-1 text-xl font-bold text-encre" />
        </div>
        <button type="button" onClick={onQuitter} className="shrink-0 cursor-pointer rounded-lg border-0 bg-transparent px-2 py-1 text-sm text-accent underline underline-offset-2">
          {t("zoneQuitter")}
        </button>
      </div>

      {vide ? (
        <p className="m-0 text-[0.9rem] text-encre-2">{t("zoneAide")}</p>
      ) : (
        <>
          <p className="m-0 text-[0.86rem] text-encre-2">
            {t("zoneComposition", { n: zone.indices.length, unites: unitesNom })}
            {r && r.recenses < r.n && ` ${t(zone.niveau === "fokontany" ? "zoneCouvertureCalee" : "zoneCouverture", { k: r.recenses, n: r.n })}`}
          </p>
          {niveauCarte !== zone.niveau && (
            <p className="m-0 rounded-lg bg-accent-doux px-3 py-2 text-[0.86rem]">
              {t("zoneAutreNiveau", { unites: unitesNom })}{" "}
              <button type="button" onClick={() => onNiveau(zone.niveau)} className="cursor-pointer border-0 bg-transparent p-0 font-semibold text-accent underline">
                {t(`niveau.${zone.niveau}` as Cle)}
              </button>
            </p>
          )}
          {r && (
            <div className="grid grid-cols-2 gap-x-4 gap-y-3 sm:grid-cols-3">
              {chiffresZone(t, r, zone.niveau, annee, FIN).map(([v, l]) => (
                <div key={l} className="min-w-0">
                  <div className="chiffre text-[1.08rem] leading-tight">{v}</div>
                  <div className="text-[0.76rem] leading-snug text-discret">{l}</div>
                </div>
              ))}
            </div>
          )}
          {r && (
            <section className="grid gap-2 border-t border-trait pt-3">
              <h3 className="etiquette m-0">{t("estTitre")}</h3>
              <EstimationDate base={base} unites={r.unites} niveau={zone.niveau} annee={anneeEst} onAnnee={setAnneeEst} />
            </section>
          )}
          <div className="flex flex-wrap gap-2">
            <a href={adresseZone(zone, "fiche-zone")} className={`${bouton} no-underline`}>{t("ficheOuvrir")}</a>
            <button type="button" className={bouton} onClick={exporter}>{t("zoneExporter")}</button>
            <button type="button" className={bouton} onClick={copier}>{copie ? t("zoneLienCopie") : t("zoneCopierLien")}</button>
            <button type="button" className={bouton} onClick={onVider}>{t("zoneVider")}</button>
          </div>
          <AppelDevis texte={t("devisZone")}
            lieux={`${nom} (${zone.indices.length} ${unitesNom})${unitesNiveau ? ` : ${zone.indices.slice(0, 12).map((i) => unitesNiveau[i].n).join(", ")}${zone.indices.length > 12 ? "…" : ""}` : ""}`}
            lien={window.location.href.split("#")[0] + adresseZone(zone, "zone")} />
          {unitesNiveau && (
            <section className="grid gap-1 border-t border-trait pt-3">
              <h3 className="etiquette m-0">{t("zoneListe", { n: zone.indices.length })}</h3>
              <ul className="m-0 grid max-h-[320px] list-none gap-0.5 overflow-y-auto p-0">
                {[...zone.indices].sort((a, b) => (pop2018(unitesNiveau[b], zone.niveau) ?? 0) - (pop2018(unitesNiveau[a], zone.niveau) ?? 0)).map((i) => {
                  const u = unitesNiveau[i];
                  return (
                    <li key={i} className="grid grid-cols-[minmax(0,1fr)_auto_auto] items-center gap-x-2 rounded-md px-2 py-1 text-[0.86rem] hover:bg-surface-2">
                      <span className="min-w-0">
                        <span className="block truncate">{u.n}</span>
                        <span className="block truncate text-[0.74rem] text-discret">{rattachement(base, u, zone.niveau)}</span>
                      </span>
                      <span className="chiffre">{entier(pop2018(u, zone.niveau))}</span>
                      <button type="button" onClick={() => onRetirer(i)} aria-label={t("zoneRetirer", { nom: u.n })} title={t("zoneRetirer", { nom: u.n })}
                        className="cursor-pointer rounded border-0 bg-transparent px-1.5 text-lg leading-none text-discret hover:text-encre">×</button>
                    </li>
                  );
                })}
              </ul>
            </section>
          )}
        </>
      )}
    </div>
  );
}

export function FicheZone({ base, unitesNiveau, contours, zone }: {
  base: Base; unitesNiveau: Unite[]; contours: Partial<Record<Niveau, Contours>>; zone: Zone;
}) {
  const { t, langue } = useLangue();
  const meta = base.meta;
  const AN = Math.min(new Date().getFullYear(), meta.annees_wp[meta.annees_wp.length - 1]);
  const FIN = meta.annees_wp[meta.annees_wp.length - 1];
  const iAn = meta.annees_wp.indexOf(AN);
  const r = resumer(base, unitesNiveau, zone, AN);
  const nom = useNomZone(zone);
  const aujourdhui = dateLongue(new Date(), langue);
  const titre = `${t("zoneTitre")} – ${nom}`;
  useTitre(titre);
  const [anneeEst, setAnneeEst] = useState(AN);

  const fk = zone.niveau === "fokontany";
  const R = base.niveaux.regions, D = base.niveaux.districts;
  const unitesNom = t(`niveau.${zone.niveau}` as Cle).toLowerCase();
  const geo = contours[zone.niveau];
  const membres = geo ? zone.indices.map((i) => geo.features[i]).filter(Boolean) : [];
  const lignes = [...r.unites].sort((a, b) => (pop2018(b, zone.niveau) ?? 0) - (pop2018(a, zone.niveau) ?? 0));
  const regionsDhs = r.regions.map((i) => R[i]).filter((x) => x.dhs).sort((a, b) => (b.rg?.p ?? 0) - (a.rg?.p ?? 0)).slice(0, 4);
  const cellule = "border-b border-trait px-2 py-1";
  const droite = `${cellule} chiffre text-right`;

  return (
    <div className="papier min-h-screen py-6">
      <BarreImpression />
      <article className="feuille">
        <header className="grid grid-cols-[minmax(0,1fr)_180px] items-start gap-4">
          <div>
            <p className="etiquette m-0">{t("zoneTitre")}</p>
            <h1 className="m-0 text-[1.9rem] font-bold leading-tight">{nom}</h1>
            <p className="m-0 text-encre-2">{t("zoneComposition", { n: r.n, unites: unitesNom })}</p>
            <p className="m-0 text-[0.86rem] text-encre-2">
              {zone.niveau !== "regions" && `${t("niveau.regions")} : ${r.regions.map((i) => R[i].n).join(", ")}`}
              {(zone.niveau === "communes" || fk) && r.districts.length <= 8 && ` · ${t("niveau.districts")} : ${r.districts.map((i) => D[i].n).join(", ")}`}
            </p>
            <p className="m-0 mt-1 text-[0.8rem] text-discret">
              {t("ficheEdition", { date: aujourdhui, collecte: meta.collecte ? dateLongue(new Date(meta.collecte), langue) : "n.d." })}
            </p>
          </div>
          <div className="grid grid-cols-[1fr_2fr] items-end gap-2">
            {contours.regions && <Situation fond={contours.regions.features} cibles={membres} largeur={60} />}
            {geo && <Situation fond={geo.features} cibles={membres} cadre={membres} largeur={120} />}
          </div>
        </header>

        <Bloc titre={t("ficheChiffresCles")}>
          <div className="grid grid-cols-3 gap-x-4 gap-y-3">
            {chiffresZone(t, r, zone.niveau, AN, FIN).map(([v, l]) => (
              <div key={l}>
                <div className="chiffre text-[1.2rem] leading-tight">{v}</div>
                <div className="text-[0.76rem] leading-snug text-discret">{l}</div>
              </div>
            ))}
          </div>
          {r.recenses < r.n && (
            <p className="m-0 text-[0.82rem] text-discret">
              {t(fk ? "zoneCouvertureCalee" : "zoneCouverture", { k: r.recenses, n: r.n })} {t(fk ? "zoneNoteCalee" : "zoneNoteCouverture")}
            </p>
          )}
        </Bloc>

        <Bloc titre={t("estTitre")}>
          <EstimationDate base={base} unites={r.unites} niveau={zone.niveau} annee={anneeEst} onAnnee={setAnneeEst} />
        </Bloc>

        <Bloc titre={t("zoneListe", { n: r.n })}>
          <table className="w-full border-collapse text-[0.78rem]">
            <thead>
              <tr>
                <th className={`${cellule} text-left font-semibold`}>{t("col.nom")}</th>
                {zone.niveau !== "regions" && <th className={`${cellule} text-left font-semibold`}>{t("zoneRattachement")}</th>}
                <th className={`${cellule} text-right font-semibold`}>{fk ? t("col.calee") : t("col.recense")}</th>
                {!fk && <th className={`${cellule} text-right font-semibold`}>{t("col.menages")}</th>}
                {!fk && <th className={`${cellule} text-right font-semibold`}>{t("col.taille")}</th>}
                <th className={`${cellule} text-right font-semibold`}>{t("col.estime", { annee: AN })}</th>
                <th className={`${cellule} text-right font-semibold`}>{t("col.estime", { annee: FIN })}</th>
              </tr>
            </thead>
            <tbody>
              {lignes.map((u, k) => (
                <tr key={u.n + k}>
                  <td className={cellule}>{u.n}</td>
                  {zone.niveau !== "regions" && <td className={`${cellule} text-encre-2`}>{rattachement(base, u, zone.niveau, true)}</td>}
                  <td className={droite}>{entier(pop2018(u, zone.niveau))}</td>
                  {!fk && <td className={droite}>{entier(u.rg?.m)}</td>}
                  {!fk && <td className={droite}>{nombre(u.rg?.t, 1)}</td>}
                  <td className={droite}>{entier(u.wp[iAn])}</td>
                  <td className={droite}>{entier(u.wp[u.wp.length - 1])}</td>
                </tr>
              ))}
              <tr className="font-semibold">
                <td className={cellule}>{t("zoneTotal")}</td>
                {zone.niveau !== "regions" && <td className={cellule} />}
                <td className={droite}>{entier(r.population2018)}</td>
                {!fk && <td className={droite}>{entier(r.menages)}</td>}
                {!fk && <td className={droite}>{nombre(r.taille, 1)}</td>}
                <td className={droite}>{entier(r.wp[iAn])}</td>
                <td className={droite}>{entier(r.wp[r.wp.length - 1])}</td>
              </tr>
            </tbody>
          </table>
        </Bloc>

        <Bloc titre={t("evolution", { debut: meta.annees_wp[0], fin: FIN })}>
          <Courbes hauteur={180} series={[{ nom: "zone", couleur: "var(--accent)", points: meta.annees_wp.map((a, j) => [a, r.wp[j]]) }]}
            repere={r.recenses === r.n ? { x: meta.annee_ref, y: r.population2018, libelle: fk ? t("pointCalee") : t("pointRecensement") } : undefined}
            infobulle={(a) => <>{entier(r.wp[meta.annees_wp.indexOf(a)])}</>} formatY={compact} />
          <p className="m-0 text-[0.78rem] text-discret">{t("note.wp")}</p>
        </Bloc>

        {regionsDhs.length > 0 && (
          <Bloc titre={t("zoneDhs", { enquete: meta.enquete_dhs })}>
            <table className="w-full border-collapse text-[0.8rem]">
              <thead>
                <tr>
                  <th className={`${cellule} text-left font-semibold`}>{t("ficheIndicateur")}</th>
                  {regionsDhs.map((x) => <th key={x.n} className={`${cellule} text-right font-semibold`}>{x.n}</th>)}
                </tr>
              </thead>
              <tbody>
                {Object.keys(meta.noms_dhs).map((cle) => (
                  <tr key={cle}>
                    <td className={cellule}>{t(`dhs.${cle}` as Cle)}</td>
                    {regionsDhs.map((x) => {
                      const v = x.dhs?.[cle];
                      return <td key={x.n} className={droite}>{v == null ? "n.d." : nombre(v, Number.isInteger(v) ? 0 : 1)}</td>;
                    })}
                  </tr>
                ))}
              </tbody>
            </table>
            <p className="m-0 text-[0.78rem] text-discret">
              {t("note.dhs", { enquete: meta.enquete_dhs })}{r.regions.length > regionsDhs.length && ` ${t("zoneDhsLimite", { n: regionsDhs.length })}`}
            </p>
          </Bloc>
        )}

        <Bloc titre={t("ficheSources")}>
          <ul className="m-0 grid gap-1 pl-5 text-[0.8rem] text-encre-2">
            <li>{t("zoneMethode")}</li>
            <li>{t("ficheSourceRgph")}</li>
            <li>{t("ficheSourceWp")}</li>
            {fk && <li>{t("troisEstimations")} {t("note.ca")}</li>}
            <li>{t("ficheSourceDhs", { enquete: meta.enquete_dhs })}</li>
          </ul>
          <p className="m-0 text-[0.8rem]">{t("ficheCitation", { titre, date: aujourdhui, url: ADRESSE_SITE })}</p>
        </Bloc>
      </article>
    </div>
  );
}
