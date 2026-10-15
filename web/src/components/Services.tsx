import { useEffect, useState, type FormEvent } from "react";
import { useLangue } from "../i18n";
import type { Cle } from "../i18n/fr";
import { defilerVers } from "../lib/defilement";

export const CONTACT = "a.maminiaina@gmail.com";
const SERVICES = ["analyse", "rapport", "formation", "accompagnement"] as const;
type Service = (typeof SERVICES)[number] | "autre";

const champ = "w-full min-w-0 rounded-lg border border-trait-fort bg-surface px-3 py-2 text-sm text-encre";
const bouton = "cursor-pointer rounded-lg border border-trait-fort bg-surface px-3 py-1.5 text-sm font-semibold text-accent hover:bg-accent-doux";

// Une fiche ou une zone pré-remplit la demande : l'événement porte le lieu et le lien qui le rouvre
const EVENEMENT = "mdg-devis";
interface Demande { service: Service; lieux: string; lien: string }

/** Invitation à commander un rapport sur le lieu ou la zone affichés. */
export function AppelDevis({ texte, lieux, lien }: { texte: string; lieux: string; lien: string }) {
  const { t } = useLangue();
  const demander = () => window.dispatchEvent(new CustomEvent<Demande>(EVENEMENT, { detail: { service: "rapport", lieux, lien } }));
  return (
    <div className="flex flex-wrap items-center justify-between gap-2 rounded-xl border border-trait bg-accent-doux px-4 py-3">
      <span className="min-w-0 text-[0.86rem] text-encre">{texte}</span>
      <button type="button" className={bouton} onClick={demander}>{t("serviceDevis")}</button>
    </div>
  );
}

/** Services payants sur devis : présentation et demande préparée dans la messagerie de l'utilisateur. */
export function Services() {
  const { t } = useLangue();
  const [service, setService] = useState<Service>("analyse");
  const [lieux, setLieux] = useState("");
  const [lien, setLien] = useState("");
  const [copie, setCopie] = useState(false);
  const nomService = (s: Service) => t(s === "autre" ? "formAutre" : (`service.${s}` as Cle));
  useEffect(() => {
    const recevoir = (e: Event) => {
      const d = (e as CustomEvent<Demande>).detail;
      setService(d.service); setLieux(d.lieux); setLien(d.lien);
      defilerVers("demande", "demande-nom");
    };
    window.addEventListener(EVENEMENT, recevoir);
    return () => window.removeEventListener(EVENEMENT, recevoir);
  }, []);

  const choisir = (s: Service) => {
    setService(s);
    defilerVers("demande", "demande-nom");
  };
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
    <section className="carte-ui grid grid-cols-[minmax(0,1fr)] gap-5 p-5" id="services">
      <div className="grid gap-1">
        <h2 className="m-0 text-lg font-semibold">{t("servicesTitre")}</h2>
        <p className="m-0 max-w-[80ch] text-[0.9rem] text-encre-2">{t("servicesIntro")}</p>
      </div>

      <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
        {SERVICES.map((s) => (
          <div key={s} className="grid content-start gap-2 rounded-xl border border-trait bg-surface-2 p-4">
            <h3 className="m-0 text-base font-semibold">{t(`service.${s}` as Cle)}</h3>
            <p className="m-0 text-[0.86rem] leading-snug text-encre-2">{t(`service.${s}.texte` as Cle)}</p>
            <p className="m-0 text-[0.78rem] text-discret">{t("serviceTarif")}</p>
            <div><button type="button" className={bouton} onClick={() => choisir(s)}>{t("serviceDevis")}</button></div>
          </div>
        ))}
      </div>

      <form id="demande" onSubmit={envoyer} className="grid max-w-[820px] gap-3 rounded-xl border border-trait p-4">
        <h3 className="m-0 text-base font-semibold">{t("formTitre")}</h3>
        <label className="grid gap-1 text-sm">
          <span className="etiquette">{t("formService")}</span>
          <select value={service} onChange={(e) => setService(e.target.value as Service)} className={champ}>
            {[...SERVICES, "autre" as const].map((s) => <option key={s} value={s}>{nomService(s)}</option>)}
          </select>
        </label>
        <div className="grid gap-3 sm:grid-cols-2">
          <label className="grid gap-1 text-sm">
            <span className="etiquette">{t("formNom")} *</span>
            <input id="demande-nom" name="nom" required autoComplete="name" className={champ} />
          </label>
          <label className="grid gap-1 text-sm">
            <span className="etiquette">{t("formOrganisation")}</span>
            <input name="organisation" autoComplete="organization" className={champ} />
          </label>
          <label className="grid gap-1 text-sm">
            <span className="etiquette">{t("formLieux")}</span>
            <input name="lieux" value={lieux} placeholder={t("formLieuxAide")} className={champ}
              onChange={(e) => { setLieux(e.target.value); setLien(""); }} />
          </label>
          <label className="grid gap-1 text-sm">
            <span className="etiquette">{t("formEcheance")}</span>
            <input name="echeance" className={champ} />
          </label>
        </div>
        <label className="grid gap-1 text-sm">
          <span className="etiquette">{t("formMessage")} *</span>
          <textarea name="message" required rows={4} placeholder={t("formMessageAide")} className={champ} />
        </label>
        <div className="flex flex-wrap items-center gap-3">
          <button type="submit" className="cursor-pointer rounded-lg border-0 px-4 py-2 text-sm font-semibold text-white"
            style={{ background: "var(--accent)" }}>{t("formEnvoyer")}</button>
          <span className="text-sm text-encre-2">
            <a className="text-accent" href={`mailto:${CONTACT}`}>{CONTACT}</a>
            {" · "}<button type="button" onClick={copier} className="cursor-pointer border-0 bg-transparent p-0 text-sm text-accent underline underline-offset-2">
              {copie ? t("adresseCopiee") : t("copierAdresse")}
            </button>
          </span>
        </div>
        <p className="m-0 text-[0.78rem] text-discret">{t("formAide")}</p>
      </form>
    </section>
  );
}
