import { useEffect, useState, type FormEvent, type ReactNode } from "react";
import { useLangue } from "../i18n";
import type { Cle } from "../i18n/fr";
import { defilerVers } from "../lib/defilement";

export const CONTACT = "a.maminiaina@gmail.com";

type Categorie = "comprendre" | "planifier" | "outiller" | "former";
const CATEGORIES: Record<Categorie, string> = {
  comprendre: "var(--accent)", planifier: "var(--serie-3)", outiller: "var(--femme)", former: "var(--serie-5)",
};
const SERVICES = [
  { id: "analyse", cat: "comprendre" }, { id: "rapport", cat: "comprendre" }, { id: "financement", cat: "comprendre" },
  { id: "dividende", cat: "comprendre" }, { id: "acces", cat: "comprendre" }, { id: "marche", cat: "comprendre" },
  { id: "microplan", cat: "planifier" }, { id: "implantation", cat: "planifier" }, { id: "projections", cat: "planifier" },
  { id: "risques", cat: "planifier" }, { id: "sante", cat: "planifier" }, { id: "jeunesse", cat: "planifier" },
  { id: "urbanisation", cat: "planifier" }, { id: "ciblage", cat: "planifier" }, { id: "listes", cat: "outiller" }, { id: "tableau", cat: "outiller" }, { id: "suivi", cat: "outiller" },
  { id: "cartes", cat: "outiller" }, { id: "enquete", cat: "outiller" }, { id: "formation", cat: "former" },
] as const satisfies readonly { id: string; cat: Categorie }[];
type Service = (typeof SERVICES)[number]["id"] | "partenaire" | "autre";

// Icônes au trait (24 × 24), dessinées avec currentColor
const ICONES: Record<string, ReactNode> = {
  analyse: <path d="M3 21h18M6 17v-6M11 17V5M16 17v-9M21 17v-3" />,
  rapport: <><path d="M6 3h8l5 5v13H6z" /><path d="M14 3v5h5M9 13h7M9 17h5" /></>,
  microplan: <><path d="M12 21s-7-6.2-7-11.5a7 7 0 0 1 14 0C19 14.8 12 21 12 21z" /><circle cx="12" cy="9.5" r="2.5" /></>,
  implantation: <><circle cx="12" cy="12" r="9" /><circle cx="12" cy="12" r="5" /><circle cx="12" cy="12" r="1" /></>,
  projections: <path d="M3 17l6-6 4 4 8-8M15 7h6v6" />,
  tableau: <><rect x="3" y="3" width="7" height="9" rx="1.5" /><rect x="14" y="3" width="7" height="5" rx="1.5" /><rect x="14" y="12" width="7" height="9" rx="1.5" /><rect x="3" y="16" width="7" height="5" rx="1.5" /></>,
  enquete: <><path d="M9 3h6v3H9zM7 4.5H5V21h14V4.5h-2" /><path d="M9 13.5l2 2 4-4" /></>,
  financement: <><rect x="2" y="6" width="20" height="12" rx="2" /><circle cx="12" cy="12" r="3" /><path d="M6 12h.01M18 12h.01" /></>,
  risques: <path d="M12 3l10 18H2zM12 10v4.5M12 17.5h.01" />,
  suivi: <path d="M3 12h4l3-8 4 16 3-8h4" />,
  cartes: <path d="M9 4L3 6v14l6-2 6 2 6-2V4l-6 2zM9 4v14M15 6v14" />,
  dividende: <><circle cx="8" cy="7" r="3" /><circle cx="17" cy="9" r="2.2" /><path d="M2 21v-2a6 6 0 0 1 12 0v2M14 21v-1.5a4 4 0 0 1 7-2.6" /></>,
  sante: <><path d="M12 20s-8-4.6-8-10.5A4.5 4.5 0 0 1 12 7a4.5 4.5 0 0 1 8 2.5C20 15.4 12 20 12 20z" /><path d="M12 10v5M9.5 12.5h5" /></>,
  jeunesse: <><path d="M4 21V10l8-6 8 6v11" /><path d="M9 21v-6h6v6M12 4v3" /></>,
  acces: <path d="M4 20L8 4M20 20L16 4M12 5v2M12 10.5v2.5M12 16.5v3" />,
  marche: <><path d="M5 8h14l-1 13H6z" /><path d="M9 8V6a3 3 0 0 1 6 0v2" /></>,
  ciblage: <path d="M3 4h18l-7 9v6l-4 2v-8z" />,
  listes: <><path d="M9 6h11M9 12h11M9 18h11" /><path d="M4 6h.01M4 12h.01M4 18h.01" /></>,
  urbanisation: <><path d="M3 21h18M5 21V9l5-3v15M10 21V4l9 4v13" /><path d="M13 11h3M13 15h3" /></>,
  formation: <><path d="M2 9l10-5 10 5-10 5z" /><path d="M6 11v5c3 2 9 2 12 0v-5M22 9v5" /></>,
  partenaire: <path d="M12 20s-8-4.6-8-10.5A4.5 4.5 0 0 1 12 7a4.5 4.5 0 0 1 8 2.5C20 15.4 12 20 12 20z" />,
  coche: <path d="M5 12.5l4.5 4.5L19 7" />,
  horloge: <><circle cx="12" cy="12" r="9" /><path d="M12 7v5l3.5 2" /></>,
};
function Icone({ nom, taille = 22 }: { nom: string; taille?: number }) {
  return (
    <svg width={taille} height={taille} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.8}
      strokeLinecap="round" strokeLinejoin="round" aria-hidden="true" className="shrink-0">{ICONES[nom]}</svg>
  );
}
const teinte = (c: string, p = 14) => `color-mix(in srgb, ${c} ${p}%, transparent)`;

const champ = "w-full min-w-0 rounded-xl border border-trait-fort bg-surface px-3 py-2.5 text-sm text-encre";
const bouton = "cursor-pointer rounded-lg border border-trait-fort bg-surface px-3 py-1.5 text-sm font-semibold text-accent hover:bg-accent-doux";

// Une fiche ou une zone pré-remplit la demande : l'événement porte le lieu et le lien qui le rouvre
const EVENEMENT = "mdg-devis";
interface Demande { service: Service; lieux: string; lien: string }
const demanderDevis = (d: Demande) => window.dispatchEvent(new CustomEvent<Demande>(EVENEMENT, { detail: d }));

/** Invitation à commander un rapport sur le lieu ou la zone affichés. */
export function AppelDevis({ texte, lieux, lien }: { texte: string; lieux: string; lien: string }) {
  const { t } = useLangue();
  return (
    <div className="flex flex-wrap items-center justify-between gap-2 rounded-xl border border-trait bg-accent-doux px-4 py-3">
      <span className="min-w-0 text-[0.86rem] text-encre">{texte}</span>
      <button type="button" className={bouton} onClick={() => demanderDevis({ service: "rapport", lieux, lien })}>{t("serviceDevis")}</button>
    </div>
  );
}

/** Services payants sur devis : offres, abonnement et demande préparée dans la messagerie de l'utilisateur. */
export function Services() {
  const { t } = useLangue();
  const [service, setService] = useState<Service>("analyse");
  const [lieux, setLieux] = useState("");
  const [lien, setLien] = useState("");
  const [copie, setCopie] = useState(false);
  const nomService = (s: Service) => t(s === "autre" ? "formAutre" : s === "partenaire" ? "partenaireTitre" : (`service.${s}` as Cle));

  const choisir = (s: Service) => { setService(s); defilerVers("demande", "demande-nom"); };
  useEffect(() => {
    const recevoir = (e: Event) => {
      const d = (e as CustomEvent<Demande>).detail;
      setService(d.service); setLieux(d.lieux); setLien(d.lien);
      defilerVers("demande", "demande-nom");
    };
    window.addEventListener(EVENEMENT, recevoir);
    return () => window.removeEventListener(EVENEMENT, recevoir);
  }, []);

  const envoyer = (e: FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    const f = new FormData(e.currentTarget);
    const v = (k: string) => String(f.get(k) ?? "").trim();
    // Les champs facultatifs vides sont omis ; les lignes vides séparent les paragraphes
    const lignes = [
      t("mailIntro", { service: nomService(service) }), "",
      `${t("formNom")} : ${v("nom")}`,
      v("organisation") ? `${t("formOrganisation")} : ${v("organisation")}` : null,
      v("lieux") ? `${t("formLieux")} : ${v("lieux")}` : null,
      v("echeance") ? `${t("formEcheance")} : ${v("echeance")}` : null,
      lien ? `${t("formLien")} : ${lien}` : null,
      "", `${t("formMessage")} :`, v("message"),
    ].filter((l) => l != null);
    const sujet = t("mailSujet", { service: nomService(service) });
    window.location.href = `mailto:${CONTACT}?subject=${encodeURIComponent(sujet)}&body=${encodeURIComponent(lignes.join("\n"))}`;
  };
  const copier = async () => {
    try { await navigator.clipboard.writeText(CONTACT); setCopie(true); setTimeout(() => setCopie(false), 2000); } catch { /* adresse visible à l'écran */ }
  };

  return (
    <section id="services" className="grid grid-cols-[minmax(0,1fr)] gap-5">
      {/* Accroche */}
      <div className="relative overflow-hidden rounded-[20px] px-6 py-9 text-white sm:px-10 sm:py-12"
        style={{ background: "linear-gradient(135deg, #1c5cab 0%, #0d366b 100%)" }}>
        <div aria-hidden="true" className="pointer-events-none absolute -right-24 -top-24 h-72 w-72 rounded-full" style={{ background: "rgb(255 255 255 / 0.07)" }} />
        <div aria-hidden="true" className="pointer-events-none absolute -bottom-32 right-24 h-64 w-64 rounded-full" style={{ background: "rgb(255 255 255 / 0.05)" }} />
        <div className="relative grid max-w-[720px] gap-4">
          <span className="w-fit rounded-full px-3 py-1 text-[0.75rem] font-semibold uppercase tracking-[0.08em]" style={{ background: "rgb(255 255 255 / 0.14)" }}>
            {t("servicesSurtitre")}
          </span>
          <h2 className="m-0 text-[1.75rem] font-bold leading-tight sm:text-[2.2rem]">{t("servicesTitre")}</h2>
          <p className="m-0 text-[1rem] leading-relaxed" style={{ color: "rgb(255 255 255 / 0.85)" }}>{t("servicesIntro")}</p>
          <div className="mt-1 flex flex-wrap gap-3">
            <button type="button" onClick={() => defilerVers("demande", "demande-nom")}
              className="cursor-pointer rounded-xl border-0 bg-white px-5 py-3 text-[0.95rem] font-semibold shadow-lg transition hover:-translate-y-0.5" style={{ color: "#0d366b" }}>
              {t("servicesCta")}
            </button>
            <button type="button" onClick={() => defilerVers("offres")}
              className="cursor-pointer rounded-xl border px-5 py-3 text-[0.95rem] font-semibold text-white transition hover:bg-white/10" style={{ borderColor: "rgb(255 255 255 / 0.4)", background: "transparent" }}>
              {t("servicesVoirOffres")}
            </button>
          </div>
          <ul className="m-0 mt-2 flex list-none flex-wrap gap-x-6 gap-y-2 p-0 text-[0.88rem]" style={{ color: "rgb(255 255 255 / 0.9)" }}>
            {(["servicesAtout1", "servicesAtout2", "servicesAtout3"] as Cle[]).map((c) => (
              <li key={c} className="flex items-center gap-2"><Icone nom="coche" taille={16} />{t(c)}</li>
            ))}
          </ul>
        </div>
      </div>

      {/* Offres */}
      <div id="offres" className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        {SERVICES.map(({ id, cat }) => {
          const c = CATEGORIES[cat];
          return (
            <article key={id} className="carte-ui group flex flex-col gap-3 p-5 transition hover:-translate-y-1 hover:shadow-lg">
              <div className="flex items-center justify-between gap-2">
                <span className="grid h-11 w-11 place-items-center rounded-xl" style={{ background: teinte(c), color: c }}><Icone nom={id} /></span>
                <span className="rounded-full px-2.5 py-0.5 text-[0.72rem] font-semibold" style={{ background: teinte(c, 12), color: c }}>
                  {t(`categorie.${cat}` as Cle)}
                </span>
              </div>
              <div className="grid gap-1">
                <h3 className="m-0 text-[1.05rem] font-semibold leading-snug">{t(`service.${id}` as Cle)}</h3>
                <p className="m-0 text-[0.88rem] leading-snug text-encre-2">{t(`service.${id}.texte` as Cle)}</p>
              </div>
              <ul className="m-0 grid list-none gap-1.5 p-0 text-[0.84rem]">
                {[1, 2, 3].map((k) => (
                  <li key={k} className="flex gap-2"><span style={{ color: c }} className="mt-0.5"><Icone nom="coche" taille={15} /></span>{t(`service.${id}.l${k}` as Cle)}</li>
                ))}
              </ul>
              <p className="m-0 text-[0.78rem] text-discret">{t("servicePour", { public: t(`service.${id}.public` as Cle) })}</p>
              <div className="mt-auto flex items-center justify-between gap-2 border-t border-trait pt-3">
                <span className="flex items-center gap-1.5 text-[0.8rem] text-encre-2"><Icone nom="horloge" taille={15} />{t(`service.${id}.duree` as Cle)}</span>
                <button type="button" onClick={() => choisir(id)}
                  className="cursor-pointer whitespace-nowrap border-0 bg-transparent p-0 text-sm font-semibold text-accent group-hover:underline">
                  {t("serviceDevis")} →
                </button>
              </div>
            </article>
          );
        })}
      </div>

      {/* Abonnement */}
      <div className="carte-ui flex flex-wrap items-center gap-4 p-5 sm:p-6" style={{ background: `linear-gradient(90deg, ${teinte("var(--serie-4)", 14)}, var(--surface))` }}>
        <span className="grid h-12 w-12 place-items-center rounded-xl" style={{ background: teinte("var(--serie-4)", 22), color: "var(--serie-4)" }}><Icone nom="partenaire" /></span>
        <div className="grid min-w-0 flex-1 basis-[280px] gap-0.5">
          <h3 className="m-0 text-[1.05rem] font-semibold">{t("partenaireTitre")}</h3>
          <p className="m-0 text-[0.9rem] text-encre-2">{t("partenaireTexte")}</p>
        </div>
        <button type="button" onClick={() => choisir("partenaire")}
          className="cursor-pointer rounded-xl border-0 px-5 py-2.5 text-sm font-semibold text-white" style={{ background: "var(--accent)" }}>
          {t("partenaireCta")}
        </button>
      </div>

      {/* Étapes et demande */}
      <div className="carte-ui grid gap-8 p-5 sm:p-8 lg:grid-cols-[minmax(0,0.8fr)_minmax(0,1.2fr)]">
        <div className="grid content-start gap-5">
          <h3 className="m-0 text-xl font-bold">{t("etapesTitre")}</h3>
          <ol className="m-0 grid list-none gap-5 p-0">
            {[1, 2, 3].map((k) => (
              <li key={k} className="flex gap-4">
                <span className="grid h-9 w-9 shrink-0 place-items-center rounded-full text-sm font-bold text-white" style={{ background: "var(--accent)" }}>{k}</span>
                <span className="grid gap-0.5">
                  <strong className="text-[0.95rem]">{t(`etape${k}` as Cle)}</strong>
                  <span className="text-[0.86rem] text-encre-2">{t(`etape${k}.texte` as Cle)}</span>
                </span>
              </li>
            ))}
          </ol>
          <div className="grid gap-1 rounded-xl bg-surface-2 p-4 text-sm">
            <span className="etiquette">{t("ecrireDirectement")}</span>
            <span className="flex flex-wrap items-center gap-x-3 gap-y-1">
              <a className="font-semibold text-accent" href={`mailto:${CONTACT}`}>{CONTACT}</a>
              <button type="button" onClick={copier} className="cursor-pointer border-0 bg-transparent p-0 text-sm text-encre-2 underline underline-offset-2">
                {copie ? t("adresseCopiee") : t("copierAdresse")}
              </button>
            </span>
          </div>
        </div>

        <form id="demande" onSubmit={envoyer} className="grid content-start gap-3">
          <h3 className="m-0 text-xl font-bold">{t("formTitre")}</h3>
          <label className="grid gap-1 text-sm">
            <span className="font-medium">{t("formService")}</span>
            <select value={service} onChange={(e) => setService(e.target.value as Service)} className={champ}>
              {(Object.keys(CATEGORIES) as Categorie[]).map((cat) => (
                <optgroup key={cat} label={t(`categorie.${cat}` as Cle)}>
                  {SERVICES.filter((s) => s.cat === cat).map((s) => <option key={s.id} value={s.id}>{nomService(s.id)}</option>)}
                </optgroup>
              ))}
              <option value="partenaire">{nomService("partenaire")}</option>
              <option value="autre">{nomService("autre")}</option>
            </select>
          </label>
          <div className="grid gap-3 sm:grid-cols-2">
            <label className="grid gap-1 text-sm">
              <span className="font-medium">{t("formNom")} *</span>
              <input id="demande-nom" name="nom" required autoComplete="name" className={champ} />
            </label>
            <label className="grid gap-1 text-sm">
              <span className="font-medium">{t("formOrganisation")}</span>
              <input name="organisation" autoComplete="organization" className={champ} />
            </label>
            <label className="grid gap-1 text-sm">
              <span className="font-medium">{t("formLieux")}</span>
              <input name="lieux" value={lieux} placeholder={t("formLieuxAide")} className={champ}
                onChange={(e) => { setLieux(e.target.value); setLien(""); }} />
            </label>
            <label className="grid gap-1 text-sm">
              <span className="font-medium">{t("formEcheance")}</span>
              <input name="echeance" className={champ} />
            </label>
          </div>
          <label className="grid gap-1 text-sm">
            <span className="font-medium">{t("formMessage")} *</span>
            <textarea name="message" required rows={4} placeholder={t("formMessageAide")} className={champ} />
          </label>
          <button type="submit" className="w-full cursor-pointer rounded-xl border-0 px-5 py-3 text-[0.95rem] font-semibold text-white shadow-md transition hover:-translate-y-0.5 sm:w-fit"
            style={{ background: "var(--accent)" }}>{t("formEnvoyer")}</button>
          <p className="m-0 text-[0.78rem] text-discret">{t("formAide")}</p>
        </form>
      </div>
    </section>
  );
}
