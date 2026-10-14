import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { Carte, type Survol } from "./components/Carte";
import { Fiche } from "./components/Fiche";
import { FicheTerritoire, NIVEAUX_FICHE } from "./components/FicheTerritoire";
import { FicheZone, PanneauZone } from "./components/Zone";
import { memoriserZone, zoneDepuisAdresse, zoneMemorisee, type Zone } from "./lib/zone";
import { Infobulle } from "./components/Graphiques";
import { Recherche } from "./components/Recherche";
import { Classement, Enquetes, Tendances, Tuiles } from "./components/Sections";
import { useLangue, type Langue } from "./i18n";
import type { Cle } from "./i18n/fr";
import { chargerBase, chargerContours, chargerFokontany } from "./lib/donnees";
import { dateLongue } from "./lib/format";
import { construireEchelle, construireIndicateurs, INDICATEUR_PAR_DEFAUT, type Indicateur } from "./lib/indicateurs";
import { useTheme, type ModeTheme } from "./lib/theme";
import { NIVEAUX, type Base, type Contours, type Niveau, type Selection, type Unite } from "./lib/types";

const disponible = (ind: Indicateur | undefined, n: Niveau) => !!ind && ind.niveaux.includes(n);

/** Fiche imprimable demandée par l'adresse : #fiche/<niveau>/<indice>. */
function ficheDemandee(): Selection | null {
  const m = window.location.hash.match(/^#fiche\/(\w+)\/(\d+)$/);
  return m && NIVEAUX_FICHE.includes(m[1] as Niveau) ? { niveau: m[1] as Niveau, i: Number(m[2]) } : null;
}

export default function App() {
  const { t, langue, setLangue } = useLangue();
  const theme = useTheme();
  const [base, setBase] = useState<Base | null>(null);
  const [erreur, setErreur] = useState<string | null>(null);
  const [contours, setContours] = useState<Partial<Record<Niveau, Contours>>>({});
  const [fokontany, setFokontany] = useState<Unite[] | null>(null);
  const [niveau, setNiveau] = useState<Niveau>("regions");
  const [indicateurId, setIndicateurId] = useState("rg");
  const [annee, setAnnee] = useState(new Date().getFullYear());
  const [selection, setSelection] = useState<Selection | null>(null);
  const [centrage, setCentrage] = useState(0);
  const [fondActif, setFondActif] = useState(true);
  const [survol, setSurvol] = useState<Survol | null>(null);
  const [fkRepere, setFkRepere] = useState<string | null>(null);
  // Les couleurs de la carte lisent les jetons CSS : on les recalcule une fois le thème appliqué
  const [versionTheme, setVersionTheme] = useState(0);
  useEffect(() => setVersionTheme((v) => v + 1), [theme.sombre]);

  useEffect(() => {
    chargerBase().then((b) => {
      setBase(b);
      setAnnee(Math.min(new Date().getFullYear(), b.meta.annees_wp[b.meta.annees_wp.length - 1]));
    }).catch((e) => setErreur(String(e.message ?? e)));
    chargerContours("regions").then((c) => setContours((p) => ({ ...p, regions: c }))).catch((e) => setErreur(String(e.message ?? e)));
  }, []);

  // Chargements déjà lancés : évite de télécharger deux fois le même fichier
  const enCours = useRef(new Set<string>(["contours-regions"]));
  const chargerNiveau = useCallback((n: Niveau) => {
    const echec = (e: Error) => setErreur(String(e.message ?? e));
    if (!enCours.current.has(`contours-${n}`)) {
      enCours.current.add(`contours-${n}`);
      chargerContours(n).then((c) => setContours((p) => ({ ...p, [n]: c }))).catch(echec);
    }
    if (n === "fokontany" && base && !enCours.current.has("fokontany")) {
      enCours.current.add("fokontany");
      chargerFokontany(base.niveaux.communes).then(setFokontany).catch(echec);
    }
  }, [base]);

  // Zone d'intervention : lue dans un lien partagé (#zone?…), sinon reprise de la dernière visite
  const zoneLien = useMemo(() => zoneDepuisAdresse(window.location.hash, "zone"), []);
  const [zone, setZone] = useState<Zone | null>(() => zoneLien ?? zoneMemorisee());
  const [modeZone, setModeZone] = useState(!!zoneLien);
  useEffect(() => memoriserZone(zone), [zone]);
  // La carte affiche le découpage de la zone ouverte par lien
  const ouvrirZone = useCallback((z: Zone) => {
    setZone(z);
    setModeZone(true);
    setNiveau(z.niveau);
    setIndicateurId((id) => (z.niveau === "fokontany" && !["wp", "wpd", "cr", "ca", "p", "d"].includes(id) ? INDICATEUR_PAR_DEFAUT.fokontany : id));
  }, []);
  useEffect(() => { if (zoneLien) ouvrirZone(zoneLien); }, [zoneLien, ouvrirZone]);

  const [demandeFiche, setDemandeFiche] = useState(ficheDemandee);
  const [demandeFicheZone, setDemandeFicheZone] = useState(() => zoneDepuisAdresse(window.location.hash, "fiche-zone"));
  useEffect(() => {
    const lire = () => {
      setDemandeFiche(ficheDemandee());
      setDemandeFicheZone(zoneDepuisAdresse(window.location.hash, "fiche-zone"));
      const z = zoneDepuisAdresse(window.location.hash, "zone");
      if (z) ouvrirZone(z);
    };
    window.addEventListener("hashchange", lire);
    return () => window.removeEventListener("hashchange", lire);
  }, [ouvrirZone]);
  // Une zone ouverte par lien est reprise dans l'état : l'adresse n'a plus à la porter
  useEffect(() => {
    if (window.location.hash.startsWith("#zone?")) history.replaceState(null, "", window.location.pathname + window.location.search);
  }, [zone]);
  // Contours et fokontany nécessaires à la zone (carte, panneau, fiche)
  const niveauZone = (demandeFicheZone ?? zone)?.niveau;
  useEffect(() => {
    if (!base || !niveauZone) return;
    chargerNiveau(niveauZone);
    if (niveauZone === "fokontany") chargerNiveau("fokontany");
  }, [base, niveauZone, chargerNiveau]);
  // La fiche a besoin des contours de son niveau (carte de situation) et, pour une commune, des fokontany
  useEffect(() => {
    if (!demandeFiche || !base) return;
    chargerNiveau(demandeFiche.niveau);
    if (demandeFiche.niveau === "communes") chargerNiveau("fokontany");
  }, [demandeFiche, base, chargerNiveau]);

  const indicateurs = useMemo(() => (base ? construireIndicateurs(base.meta) : []), [base]);
  const indicateur = indicateurs.find((i) => i.id === indicateurId) ?? indicateurs[0];
  const unites: Record<Niveau, Unite[] | null> = useMemo(() => ({
    regions: base?.niveaux.regions ?? null, districts: base?.niveaux.districts ?? null,
    communes: base?.niveaux.communes ?? null, fokontany,
  }), [base, fokontany]);
  const unitesNiveau = unites[niveau];
  const ficheImprimable = demandeFiche && unites[demandeFiche.niveau]?.[demandeFiche.i] ? demandeFiche : null;

  const echelle = useMemo(() => (indicateur && unitesNiveau ? construireEchelle(indicateur, unitesNiveau.map((u) => indicateur.val(u, annee))) : null),
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [indicateur, unitesNiveau, annee, versionTheme]);
  const couleurs = useMemo(() => (echelle && unitesNiveau && indicateur ? unitesNiveau.map((u) => echelle.couleur(indicateur.val(u, annee))) : null),
    [echelle, unitesNiveau, indicateur, annee]);
  const fokontanyParCommune = useMemo(() => {
    if (!fokontany || !base) return null;
    const p: number[][] = base.niveaux.communes.map(() => []);
    fokontany.forEach((u, i) => p[u.c!].push(i));
    return p;
  }, [fokontany, base]);

  const changerNiveau = (n: Niveau) => {
    setNiveau(n);
    chargerNiveau(n);
    if (!disponible(indicateur, n)) setIndicateurId(INDICATEUR_PAR_DEFAUT[n]);
  };
  const choisir = (s: Selection, centrer = true) => {
    if (s.niveau !== niveau) changerNiveau(s.niveau);
    if (s.niveau === "communes") chargerNiveau("fokontany");
    setSelection(s);
    if (centrer) setCentrage((c) => c + 1);
  };
  // En mode zone, un clic ajoute l'unité à la zone ou l'en retire (un seul découpage par zone)
  const basculerDansZone = (s: Selection, ajouterSeulement = false) => setZone((z) => {
    if (!z || !z.indices.length) return { niveau: s.niveau, indices: [s.i], nom: z?.nom ?? "" };
    if (z.niveau !== s.niveau) return z;
    if (z.indices.includes(s.i)) return ajouterSeulement ? z : { ...z, indices: z.indices.filter((i) => i !== s.i) };
    return { ...z, indices: [...z.indices, s.i] };
  });
  const zoneAccepte = (n: Niveau) => !zone?.indices.length || zone.niveau === n;

  if (erreur) return <p className="p-8 text-encre">{t("erreurChargement", { erreur })}</p>;
  if (!base || !indicateur) return <p className="p-8 text-encre-2">{t("chargement")}</p>;

  const survolUnite = survol && unites[survol.niveau]?.[survol.i];
  const parent = (u: Unite, n: Niveau) => n === "regions" ? "" : n === "districts" ? base.niveaux.regions[u.r!].n
    : n === "communes" ? `${base.niveaux.districts[u.di!].n} · ${base.niveaux.regions[u.r!].n}`
    : `${base.niveaux.communes[u.c!].n} · ${base.niveaux.districts[u.di!].n}`;
  const groupes: { cle: Cle; liste: Indicateur[]; params?: Record<string, string> }[] = [
    { cle: "groupeRecensement", liste: indicateurs.filter((i) => i.groupe === "recensement") },
    { cle: "groupeEstimations", liste: indicateurs.filter((i) => i.groupe === "estimations") },
    { cle: "groupeSante", liste: indicateurs.filter((i) => i.groupe === "sante"), params: { enquete: base.meta.enquete_dhs } },
  ];
  const dateCollecte = base.meta.collecte ? dateLongue(new Date(base.meta.collecte), langue) : "";

  if (demandeFicheZone) {
    const u = unites[demandeFicheZone.niveau];
    return u ? <FicheZone base={base} unitesNiveau={u} contours={contours} zone={demandeFicheZone} />
      : <p className="p-8 text-encre-2">{t("chargement")}</p>;
  }
  if (ficheImprimable) {
    return <FicheTerritoire base={base} unites={unites} contours={contours} selection={ficheImprimable}
      fokontanyParCommune={fokontanyParCommune} />;
  }

  return (
    <div className="min-h-screen">
      <header className="sticky top-0 z-30 border-b border-trait backdrop-blur" style={{ background: "color-mix(in srgb, var(--fond) 85%, transparent)" }}>
        <div className="mx-auto flex max-w-[1440px] flex-wrap items-center gap-x-6 gap-y-3 px-4 py-3 sm:px-6">
          <div className="min-w-0">
            <p className="etiquette m-0">{t("surtitre")}</p>
            <h1 className="m-0 text-xl font-bold leading-tight sm:text-2xl">{t("titre")}</h1>
          </div>
          <div className="order-3 w-full sm:order-none sm:w-auto sm:flex-1 sm:justify-center sm:flex">
            <Recherche base={base} fokontany={fokontany} onDemanderFokontany={() => chargerNiveau("fokontany")}
              onChoisir={(s, nom) => {
                setFkRepere(s.niveau === "fokontany" ? nom : null);
                if (modeZone && zoneAccepte(s.niveau)) basculerDansZone(s, true);
                choisir(s);
              }} />
          </div>
          <div className="ml-auto flex flex-wrap items-center gap-2">
            <div className="segments" role="group" aria-label={t("langue")}>
              {(["fr", "mg"] as Langue[]).map((l) => (
                <button key={l} type="button" lang={l} aria-pressed={langue === l} onClick={() => setLangue(l)}>{l === "fr" ? "Français" : "Malagasy"}</button>
              ))}
            </div>
            <div className="segments" role="group" aria-label={t("theme")}>
              {([["auto", "themeAuto"], ["clair", "themeClair"], ["sombre", "themeSombre"]] as [ModeTheme, Cle][]).map(([m, c]) => (
                <button key={m} type="button" aria-pressed={theme.mode === m} onClick={() => theme.setMode(m)}>{t(c)}</button>
              ))}
            </div>
            <a href="./classique/" className="rounded-lg px-2 py-1 text-sm text-accent underline underline-offset-2">{t("versionClassique")}</a>
          </div>
        </div>
      </header>

      <main className="mx-auto grid max-w-[1440px] gap-5 px-4 py-5 sm:px-6">
        <p className="m-0 max-w-[75ch] text-encre-2">{t("sousTitre")} {dateCollecte && t("collecte", { date: dateCollecte })}</p>
        <Tuiles base={base} />

        <section className="grid gap-5 lg:grid-cols-[minmax(0,1.65fr)_minmax(340px,1fr)]">
          <div className="carte-ui relative min-w-0 overflow-hidden">
            <div className="relative h-[72vh] min-h-[520px]">
              <Carte niveau={niveau} contours={contours} couleurs={couleurs} selection={selection} zone={zone} centrage={centrage}
                sombre={theme.sombre} fondActif={fondActif} onSurvol={setSurvol}
                onChoisir={(s) => (modeZone && zoneAccepte(s.niveau) ? basculerDansZone(s) : choisir(s, false))} />
              <div className="pointer-events-none absolute left-3 right-14 top-3 flex flex-wrap items-start gap-2">
                <div className="segments pointer-events-auto max-w-full overflow-x-auto shadow-sm" role="group" aria-label="Découpage">
                  {NIVEAUX.map((n) => (
                    <button key={n} type="button" aria-pressed={niveau === n} onClick={() => changerNiveau(n)}>{t(`niveau.${n}` as Cle)}</button>
                  ))}
                </div>
                <label className="pointer-events-auto min-w-0">
                  <span className="sr-only">{t("indicateur")}</span>
                  <select value={indicateur.id} onChange={(e) => setIndicateurId(e.target.value)}
                    className="max-w-full rounded-xl border border-trait bg-surface px-3 py-1.5 text-sm text-encre shadow-sm">
                    {groupes.map((g) => (
                      <optgroup key={g.cle} label={t(g.cle, g.params)}>
                        {g.liste.map((i) => <option key={i.id} value={i.id} disabled={!disponible(i, niveau)}>{t(i.nom)}</option>)}
                      </optgroup>
                    ))}
                  </select>
                </label>
                <button type="button" aria-pressed={modeZone} onClick={() => setModeZone((m) => !m)}
                  className={`pointer-events-auto cursor-pointer rounded-xl border px-3 py-1.5 text-sm font-semibold shadow-sm ${modeZone
                    ? "border-transparent text-white" : "border-trait bg-surface text-encre"}`}
                  style={modeZone ? { background: "var(--femme)" } : undefined} title={t("zoneBoutonAide")}>
                  {t("zoneTitre")}{zone?.indices.length ? ` (${zone.indices.length})` : ""}
                </button>
                {indicateur.annee && (
                  <label className="carte-ui pointer-events-auto flex items-center gap-2 px-3 py-1.5 text-sm">
                    <span className="etiquette">{t("annee")}</span>
                    <input type="range" min={base.meta.annees_wp[0]} max={base.meta.annees_wp[base.meta.annees_wp.length - 1]} value={annee}
                      onChange={(e) => setAnnee(+e.target.value)} className="w-28 accent-[var(--accent)]" />
                    <span className="chiffre">{annee}</span>
                  </label>
                )}
              </div>
              {echelle && (
                <div className="carte-ui absolute bottom-9 left-3 max-w-[calc(100%-1.5rem)] px-3 py-2 sm:bottom-3 sm:max-w-[420px]">
                  <div className="flex">
                    {echelle.classes.map((c) => (
                      <div key={c.couleur + c.libelle} className="min-w-0 flex-1">
                        <span className="block h-2.5" style={{ background: c.couleur }} />
                        <span className="chiffre block truncate pr-1 pt-0.5 text-[0.68rem] text-encre-2">{c.libelle}</span>
                      </div>
                    ))}
                  </div>
                  <p className="m-0 mt-1 text-[0.72rem] leading-snug text-discret">
                    {t(indicateur.note, { enquete: base.meta.enquete_dhs })} {echelle.divergent ? t("legendeEcart") : t("legendeQuantiles")}
                  </p>
                  <label className="mt-1 flex items-center gap-1.5 text-[0.75rem] text-encre-2">
                    <input type="checkbox" checked={fondActif} onChange={(e) => setFondActif(e.target.checked)} />
                    {t("fondDeCarte")}
                  </label>
                </div>
              )}
            </div>
          </div>
          <aside className="carte-ui min-w-0 p-5 lg:max-h-[72vh] lg:min-h-[520px] lg:overflow-y-auto" aria-live="polite">
            {modeZone ? (
              <PanneauZone base={base} unitesNiveau={zone ? unites[zone.niveau] : null} niveauCarte={niveau}
                zone={zone ?? { niveau, indices: [], nom: "" }} annee={Math.min(new Date().getFullYear(), base.meta.annees_wp[base.meta.annees_wp.length - 1])}
                onRetirer={(i) => setZone((z) => z && { ...z, indices: z.indices.filter((x) => x !== i) })}
                onVider={() => setZone((z) => z && { ...z, indices: [] })}
                onNom={(nom) => setZone((z) => ({ ...(z ?? { niveau, indices: [] }), nom }))}
                onNiveau={changerNiveau} onQuitter={() => setModeZone(false)} />
            ) : (
              <Fiche base={base} unites={unites} selection={selection} fokontanyParCommune={fokontanyParCommune} fkRepere={fkRepere}
                onChoisir={choisir} onReinitialiser={() => { setSelection(null); setCentrage((c) => c + 1); }} />
            )}
          </aside>
        </section>

        <Tendances base={base} />
        <Enquetes base={base} />
        <Classement niveau={niveau} unites={unitesNiveau} indicateur={indicateur} annee={annee} base={base}
          selection={selection} onChoisir={(s) => choisir(s)} />

        <footer className="grid gap-1 pb-6 text-[0.82rem] text-discret">
          <span>{t("sources")}</span>
          <span>
            <a className="text-accent" href="https://github.com/AbelMaminiaina/demographie/blob/main/DONNEES.md">{t("catalogue")}</a>
            {" · "}<a className="text-accent" href="https://github.com/AbelMaminiaina/demographie">{t("depot")}</a>
            {" · "}{t("genere")}
          </span>
        </footer>
      </main>

      <Infobulle bulle={survol && survolUnite ? { x: survol.x, y: survol.y, contenu: (
        <><strong className="block">{survolUnite.n}</strong>
          {parent(survolUnite, survol.niveau) && <span className="block opacity-80">{parent(survolUnite, survol.niveau)}</span>}
          <span className="chiffre">{(() => { const v = indicateur.val(survolUnite, annee); return v == null ? t("pasDeDonnee") : indicateur.fmt(v); })()}</span></>
      ) } : null} />
    </div>
  );
}
