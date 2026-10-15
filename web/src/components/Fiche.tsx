import { useState } from "react";
import { useLangue } from "../i18n";
import type { Cle } from "../i18n/fr";
import { croissance } from "../lib/indicateurs";
import { compact, densite, entier, nombre, pct } from "../lib/format";
import type { Base, Niveau, Recensement, Selection, Unite } from "../lib/types";
import { EstimationDate } from "./Estimation";
import { MAX_LIEUX } from "../lib/comparaison";
import { NIVEAUX_FICHE } from "./FicheTerritoire";
import { Courbes } from "./Graphiques";
import { AppelDevis } from "./Services";

type Unites = Record<Niveau, Unite[] | null>;

function Chiffres({ elements }: { elements: [string, string][] }) {
  return (
    <div className="grid grid-cols-2 gap-x-4 gap-y-3 sm:grid-cols-3">
      {elements.map(([v, l]) => (
        <div key={l} className="min-w-0">
          <div className="chiffre text-[1.12rem] leading-tight">{v}</div>
          <div className="text-[0.76rem] leading-snug text-discret">{l}</div>
        </div>
      ))}
    </div>
  );
}

function Bloc({ titre, children, actions }: { titre: string; children: React.ReactNode; actions?: React.ReactNode }) {
  return (
    <section className="grid gap-2 border-t border-trait pt-3">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h3 className="etiquette m-0">{titre}</h3>
        {actions}
      </div>
      {children}
    </section>
  );
}

function ListeBarres({ lignes, onChoisir }: { lignes: { cle: string | number; nom: string; valeur: number; titre?: string; repere?: boolean; onClick?: () => void }[]; onChoisir?: boolean }) {
  const max = Math.max(1, ...lignes.map((l) => l.valeur));
  return (
    <ul className="m-0 grid max-h-[300px] list-none gap-0.5 overflow-y-auto p-0">
      {lignes.map((l) => (
        <li key={l.cle}>
          <button type="button" onClick={l.onClick} title={l.titre} disabled={!onChoisir && !l.onClick}
            className={`grid w-full grid-cols-[minmax(0,1fr)_auto] gap-x-3 rounded-md px-2 py-1 text-left text-[0.86rem] ${l.repere ? "bg-accent-doux" : "hover:bg-surface-2"} ${l.onClick ? "cursor-pointer" : "cursor-default"}`}>
            <span className="truncate">{l.nom}</span>
            <span className="chiffre">{entier(l.valeur)}</span>
            <span className="col-span-2 mt-1 block h-1 rounded-full" style={{ width: `${(100 * l.valeur) / max}%`, background: "var(--q3)" }} />
          </button>
        </li>
      ))}
    </ul>
  );
}

/** Ménages ordinaires du recensement : nombre, taille moyenne et ses variations. */
function Menages({ rg }: { rg: Recensement }) {
  const { t } = useLangue();
  return (
    <div className="grid gap-1 text-[0.86rem] text-encre-2">
      <p className="m-0">{t("menagesPhrase", { m: entier(rg.m), t: nombre(rg.t, 1), f: pct(rg.f, 0) })}</p>
      {rg.th != null && rg.tf != null && (
        <p className="m-0">{t("menagesSexeChef", { h: nombre(rg.th, 1), f: nombre(rg.tf, 1) })}</p>
      )}
      {rg.tu != null && rg.tr != null && (
        <p className="m-0">{t("menagesMilieu", { u: nombre(rg.tu, 1), r: nombre(rg.tr, 1) })}</p>
      )}
    </div>
  );
}

export function Fiche({ base, unites, selection, fokontanyParCommune, onChoisir, onReinitialiser, fkRepere, comparaison, onComparer }: {
  base: Base; unites: Unites; selection: Selection | null; fokontanyParCommune: number[][] | null;
  onChoisir: (s: Selection, centrer?: boolean) => void; onReinitialiser: () => void; fkRepere: string | null;
  comparaison: { niveau: Niveau; i: number }[]; onComparer: (s: Selection) => void;
}) {
  const { t } = useLangue();
  const meta = base.meta;
  const AN = Math.min(new Date().getFullYear(), meta.annees_wp[meta.annees_wp.length - 1]);
  const iAn = meta.annees_wp.indexOf(AN);
  const [vueFk, setVueFk] = useState<"2018" | "wp">("2018");
  const [anneeEst, setAnneeEst] = useState(AN);

  if (!selection || !unites[selection.niveau]) {
    const regions = base.niveaux.regions;
    const top = regions.map((u, i) => ({ u, i })).sort((a, b) => (b.u.rg?.p ?? 0) - (a.u.rg?.p ?? 0)).slice(0, 5);
    return (
      <div className="grid gap-4">
        <div>
          <p className="etiquette m-0">{t("vueEnsemble")}</p>
          <h2 className="m-0 text-2xl font-bold">Madagascar</h2>
        </div>
        <Chiffres elements={[
          [entier(meta.rgph_total), t("habitantsRecenses")],
          [entier(regions.reduce((s, r) => s + r.wp[iAn], 0)), t("estimesEn", { annee: AN })],
          [entier(meta.rgph_total / regions.reduce((s, r) => s + r.s, 0)), t("habKm2En2018")],
          [String(regions.length), t("nbRegions")],
          [entier(meta.rgph_communes), t("nbCommunesRecensement")],
          [entier(meta.nb_fokontany), t("nbFokontany")],
        ]} />
        <Bloc titre={t("plusPeuplees")}>
          <ListeBarres onChoisir lignes={top.map(({ u, i }) => ({
            cle: i, nom: u.n, valeur: u.rg?.p ?? 0, onClick: () => onChoisir({ niveau: "regions", i }, true) }))} />
        </Bloc>
        <p className="m-0 text-[0.82rem] text-discret">{t("aideFiche")}</p>
      </div>
    );
  }

  const { niveau, i } = selection;
  const u = unites[niveau]![i];
  const R = base.niveaux.regions, Dt = base.niveaux.districts, C = base.niveaux.communes;
  const region = niveau === "regions" ? u : R[u.r!];
  const fil: { nom: string; s: Selection | null }[] = [{ nom: "Madagascar", s: null }];
  if (niveau !== "regions") fil.push({ nom: R[u.r!].n, s: { niveau: "regions", i: u.r! } });
  if (niveau === "communes" || niveau === "fokontany") fil.push({ nom: Dt[u.di!].n, s: { niveau: "districts", i: u.di! } });
  if (niveau === "fokontany") fil.push({ nom: C[u.c!].n, s: { niveau: "communes", i: u.c! } });

  const recense = (niveau === "regions" || niveau === "districts") && u.rg;
  const densiteWp = u.s > 0 ? u.wp[iAn] / u.s : null;
  const cr = croissance(u, AN, meta);
  const chiffres: [string, string][] = niveau === "fokontany"
    ? [[entier(u.wp[iAn]), t("estimesEn100", { annee: AN })], [densite(densiteWp), t("habKm2Wp")],
       [nombre(u.s, u.s < 10 ? 1 : 0), t("km2")], [u.ca != null ? entier(u.ca) : "n.d.", t("caleeRecensement")],
       [entier(u.p), t("estimationHdx2018")], [pct(cr), t("croissanceDepuis")]]
    : recense
      ? [[entier(u.rg!.p), t("habitantsRecenses")], [densite(u.rg!.d), t("habKm2Recensement")],
         [pct(u.rg!.u), t("populationUrbaine")], [nombre(u.rg!.rm, 1), t("hommesPour100")],
         [entier(u.s), t("km2")], [entier(u.wp[iAn]), t("estimesEn", { annee: AN })]]
      : [[entier(u.p), t("habitantsHdx")], [densite(u.d), t("habKm2")], [entier(u.s), t("km2")],
         [entier(u.wp[iAn]), t("estimesEn", { annee: AN })], [pct(cr), t("croissanceDepuis")],
         [entier(fokontanyParCommune?.[i]?.length ?? null), t("nbFokontany")]];

  // Point de référence 2018 : recensement si l'unité y est reliée, sinon estimation calée, sinon HDX
  const ref = u.rg ? u.rg.p : u.ca ?? u.p;
  const refNom = u.rg ? t("pointRecensement") : u.ca != null ? t("pointCalee") : t("pointHdx");
  const points = meta.annees_wp.map((a, j) => [a, u.wp[j]] as [number, number]);

  return (
    <div className="grid gap-4">
      <nav aria-label="Rattachement" className="flex flex-wrap items-center gap-1 text-[0.82rem] text-discret">
        {fil.map((f, k) => (
          <span key={f.nom + k} className="inline-flex items-center gap-1">
            {k > 0 && <span aria-hidden="true">›</span>}
            <button type="button" className="cursor-pointer border-0 bg-transparent p-0 text-accent underline underline-offset-2"
              onClick={() => (f.s ? onChoisir(f.s, true) : onReinitialiser())}>{f.nom}</button>
          </span>
        ))}
      </nav>
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <p className="etiquette m-0">{t(`unite.${niveau}` as Cle)}</p>
          <h2 className="m-0 text-2xl font-bold leading-tight">{u.n}</h2>
        </div>
        <div className="flex shrink-0 flex-col items-end gap-1.5">
          {NIVEAUX_FICHE.includes(niveau) && (
            <a href={`#fiche/${niveau}/${i}`} title={t("ficheOuvrirAide")}
              className="rounded-lg border border-trait-fort px-3 py-1.5 text-sm font-semibold text-accent no-underline hover:bg-accent-doux">
              {t("ficheOuvrir")}
            </a>
          )}
          {(() => {
            const dedans = comparaison.some((l) => l.niveau === niveau && l.i === i);
            const plein = comparaison.length >= MAX_LIEUX;
            return (
              <button type="button" disabled={dedans || plein} onClick={() => onComparer({ niveau, i })}
                title={plein && !dedans ? t("compPlein", { n: MAX_LIEUX }) : t("compAjouterAide")}
                className="cursor-pointer rounded-lg border border-trait-fort bg-surface px-3 py-1.5 text-sm font-semibold text-accent hover:bg-accent-doux disabled:cursor-default disabled:opacity-60">
                {dedans ? t("compDejaAjoute") : t("compAjouter")}
              </button>
            );
          })()}
        </div>
      </div>
      <Chiffres elements={chiffres} />
      {niveau === "fokontany" && <p className="m-0 text-[0.82rem] text-discret">{t("troisEstimations")}</p>}
      {recense && u.rg!.m != null && <Menages rg={u.rg!} />}
      {recense && u.rg!.e != null && (
        <p className="m-0 text-[0.82rem] text-discret">
          {t("ecartHdx", { p: entier(u.p), e: `${u.rg!.e > 0 ? "+" : ""}${nombre(u.rg!.e, 1)} %` })}
        </p>
      )}
      {niveau === "communes" && (
        <Bloc titre={t("recensementBloc")}>
          {u.rg ? (
            <>
              <p className="m-0">{t("recensementCommune", { p: entier(u.rg.p), u: pct(u.rg.u, 0) })}</p>
              {u.rg.m != null && <Menages rg={u.rg} />}
              {!u.rg.id && <p className="m-0 text-[0.82rem] text-discret">{t("decoupageChange")}</p>}
            </>
          ) : <p className="m-0 text-[0.82rem] text-discret">{t("pasDeCorrespondance")}</p>}
        </Bloc>
      )}
      <Bloc titre={t("estTitre")}>
        <EstimationDate base={base} unites={[u]} niveau={niveau} annee={anneeEst} onAnnee={setAnneeEst} />
      </Bloc>
      <Bloc titre={t("evolution", { debut: meta.annees_wp[0], fin: meta.annees_wp[meta.annees_wp.length - 1] })}>
        <Courbes hauteur={170} series={[{ nom: "wp", couleur: "var(--accent)", points }]} repere={{ x: meta.annee_ref, y: ref, libelle: refNom }}
          infobulle={(a) => (
            <><strong className="block">{a}</strong>{entier(u.wp[meta.annees_wp.indexOf(a)])} {t("habitantsWorldPop")}</>
          )} formatY={compact} />
      </Bloc>
      {region.dhs && (
        <Bloc titre={niveau === "regions" ? meta.enquete_dhs : t("dhsRegion", { enquete: meta.enquete_dhs, region: region.n })}>
          <dl className="m-0 grid gap-2">
            {Object.keys(meta.noms_dhs).map((cle) => {
              const v = region.dhs?.[cle];
              if (v == null) return null;
              const valeurs = R.map((r) => r.dhs?.[cle]).filter((x): x is number => x != null);
              const mn = Math.min(...valeurs), mx = Math.max(...valeurs);
              return (
                <div key={cle} className="grid grid-cols-[minmax(0,1fr)_56px] items-center gap-x-3 gap-y-1">
                  <dt className="text-[0.84rem] text-encre-2">{t(`dhs.${cle}` as Cle)}</dt>
                  <dd className="chiffre m-0 text-right">{nombre(v, Number.isInteger(v) ? 0 : 1)}</dd>
                  <span className="relative col-span-2 h-1.5 rounded-full" style={{ background: "var(--vide)" }}>
                    <i className="absolute -top-[3px] h-3 w-1 -translate-x-1/2 rounded-sm"
                      style={{ left: `${mx > mn ? (100 * (v - mn)) / (mx - mn) : 50}%`, background: "var(--accent)" }} />
                  </span>
                </div>
              );
            })}
          </dl>
          <p className="m-0 text-[0.78rem] text-discret">{t("repereDhs")}</p>
        </Bloc>
      )}
      {niveau === "communes" && fokontanyParCommune && unites.fokontany && (() => {
        const F = unites.fokontany!;
        const liste = (fokontanyParCommune[i] ?? []).map((j) => ({ j, f: F[j] }));
        const calee = liste.length > 0 && liste[0].f.ca != null;
        const valeur = (f: Unite) => (vueFk === "wp" ? f.wp[iAn] : calee ? f.ca! : f.p);
        const i18 = meta.annees_wp.indexOf(2018), i30 = meta.annees_wp.length - 1;
        return (
          <Bloc titre={t("listeFokontany", { n: liste.length })} actions={
            <div className="segments" role="group">
              <button type="button" aria-pressed={vueFk === "2018"} onClick={() => setVueFk("2018")}>{t("vue2018")}</button>
              <button type="button" aria-pressed={vueFk === "wp"} onClick={() => setVueFk("wp")}>{t("vueWp", { annee: AN })}</button>
            </div>}>
            <p className="m-0 text-[0.78rem] text-discret">
              {vueFk === "wp" ? t("listeWp", { annee: AN }) : calee ? t("listeCalee") : t("listeHdx")}
            </p>
            <ListeBarres lignes={liste.sort((a, b) => valeur(b.f) - valeur(a.f)).map(({ j, f }) => ({
              cle: j, nom: f.n, valeur: valeur(f), repere: f.n === fkRepere,
              titre: `HDX ${meta.annee_ref} : ${entier(f.p)}${f.ca != null ? ` · ${entier(f.ca)}` : ""} · WorldPop 2018 : ${entier(f.wp[i18])}, ${AN} : ${entier(f.wp[iAn])}, 2030 : ${entier(f.wp[i30])}`,
              onClick: () => onChoisir({ niveau: "fokontany", i: j }, true),
            }))} />
            <p className="m-0 text-[0.78rem] text-discret">
              {vueFk === "wp" ? t("noteListeWp") : calee ? t("noteListeCalee") : t("noteListeHdx")}
            </p>
          </Bloc>
        );
      })()}
      <AppelDevis texte={t("devisLieu", { nom: u.n })}
        lieux={[`${t(`unite.${niveau}` as Cle)} ${u.n}`, ...fil.slice(1).map((f) => f.nom).reverse()].join(", ")}
        lien={NIVEAUX_FICHE.includes(niveau) ? `${window.location.href.split("#")[0]}#fiche/${niveau}/${i}` : ""} />
    </div>
  );
}
