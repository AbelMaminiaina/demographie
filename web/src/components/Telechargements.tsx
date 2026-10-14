import { useEffect, useState } from "react";
import { useLangue } from "../i18n";
import type { Cle } from "../i18n/fr";
import { entier, nombre } from "../lib/format";

const DOSSIER = `${import.meta.env.BASE_URL}donnees/telechargements/`;

interface Fichier { fichier: string; theme: string; description: string; licence: string; lignes: number; octets: number }
interface Catalogue { collecte: string | null; fichiers: Fichier[]; archives: Record<string, number> }

const THEMES = ["recensement", "estimations", "territoires", "national", "sante", "enquetes"];
const taille = (o: number) => (o >= 1e6 ? `${nombre(o / 1e6, 1)} Mo` : `${nombre(o / 1e3, 0)} ko`);

/** Liste des fichiers de données téléchargeables, produite par le pipeline (catalogue.json). */
export function Telechargements() {
  const { t } = useLangue();
  const [catalogue, setCatalogue] = useState<Catalogue | null>(null);
  const [erreur, setErreur] = useState(false);
  useEffect(() => {
    fetch(`${DOSSIER}catalogue.json`).then((r) => (r.ok ? r.json() : Promise.reject())).then(setCatalogue).catch(() => setErreur(true));
  }, []);
  if (erreur) return null;

  const bouton = "inline-flex items-center gap-2 rounded-lg px-4 py-2 text-sm font-semibold no-underline";
  return (
    <section className="carte-ui grid gap-4 p-5" id="donnees">
      <div className="grid gap-1">
        <h2 className="m-0 text-lg font-semibold">{t("telTitre")}</h2>
        <p className="m-0 max-w-[80ch] text-[0.9rem] text-encre-2">{t("telIntro")}</p>
      </div>
      {!catalogue ? <p className="m-0 text-sm text-discret">{t("chargement")}</p> : (
        <>
          <div className="flex flex-wrap gap-3">
            <a href={`${DOSSIER}donnees_madagascar.xlsx`} download className={`${bouton} text-white`} style={{ background: "var(--accent)" }}>
              {t("telExcel")} <span className="font-normal opacity-85">{taille(catalogue.archives["donnees_madagascar.xlsx"])}</span>
            </a>
            <a href={`${DOSSIER}donnees_madagascar.zip`} download className={`${bouton} border border-trait-fort text-accent hover:bg-accent-doux`}>
              {t("telZip")} <span className="font-normal text-discret">{taille(catalogue.archives["donnees_madagascar.zip"])}</span>
            </a>
          </div>
          <div className="overflow-x-auto rounded-lg border border-trait">
            <table className="w-full border-collapse text-[0.85rem]">
              <thead>
                <tr className="text-left">
                  <th className="border-b border-trait px-3 py-2 font-semibold">{t("telFichier")}</th>
                  <th className="border-b border-trait px-3 py-2 text-right font-semibold">{t("telLignes")}</th>
                  <th className="border-b border-trait px-3 py-2 font-semibold">{t("telLicence")}</th>
                  <th className="border-b border-trait px-3 py-2 text-right font-semibold">CSV</th>
                </tr>
              </thead>
              {THEMES.map((theme) => {
                const liste = catalogue.fichiers.filter((f) => f.theme === theme);
                return liste.length > 0 && (
                  <tbody key={theme}>
                    <tr><td colSpan={4} className="bg-surface-2 px-3 py-1.5 etiquette">{t(`telTheme.${theme}` as Cle)}</td></tr>
                    {liste.map((f) => (
                      <tr key={f.fichier}>
                        <td className="border-b border-trait px-3 py-1.5">
                          <span className="block">{f.description}</span>
                          <span className="chiffre block text-[0.74rem] text-discret">{f.fichier}</span>
                        </td>
                        <td className="chiffre border-b border-trait px-3 py-1.5 text-right">{entier(f.lignes)}</td>
                        <td className="border-b border-trait px-3 py-1.5 text-[0.8rem] text-encre-2">{f.licence}</td>
                        <td className="border-b border-trait px-3 py-1.5 text-right">
                          <a href={`${DOSSIER}${f.fichier}`} download className="whitespace-nowrap text-accent">{taille(f.octets)}</a>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                );
              })}
            </table>
          </div>
          <p className="m-0 text-[0.8rem] text-discret">{t("telNote")}</p>
        </>
      )}
    </section>
  );
}
