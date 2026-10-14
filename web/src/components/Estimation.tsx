import { useLangue } from "../i18n";
import type { Cle } from "../i18n/fr";
import { arrondi, estimer } from "../lib/estimation";
import { entier, nombre } from "../lib/format";
import type { Base, Niveau, Unite } from "../lib/types";

/** Population d'un lieu ou d'une zone à une date choisie : estimation retenue, fourchette, méthodes,
 * groupes d'âge. Le choix de l'année est masqué à l'impression (l'année figure dans le texte). */
export function EstimationDate({ base, unites, niveau, annee, onAnnee }: {
  base: Base; unites: Unite[]; niveau: Niveau; annee: number; onAnnee: (a: number) => void;
}) {
  const { t } = useLangue();
  const e = estimer(base, unites, niveau, annee);
  const fk = niveau === "fokontany";
  const methodes: [string, number | null, boolean][] = [
    [t(fk ? "estLocaleCalee" : "estLocale"), e.locale, e.locale != null],
    [t("estWorldpop"), e.worldpop, e.locale == null],
    [t(fk ? "estNationaleCalee" : "estNationale"), e.nationale, false],
  ];
  const cellule = "border-b border-trait px-2 py-1";

  return (
    <div className="grid gap-2">
      <div className="flex flex-wrap items-baseline justify-between gap-x-3 gap-y-1">
        <p className="m-0">
          <span className="chiffre text-[1.35rem] font-semibold">{entier(arrondi(e.centrale))}</span>{" "}
          <span className="text-encre-2">{t("estHabitantsEn", { annee })}</span>
        </p>
        <label className="ecran-seul flex items-center gap-2 text-sm">
          <span className="etiquette">{t("annee")}</span>
          <select value={annee} onChange={(ev) => onAnnee(Number(ev.target.value))}
            className="rounded-lg border border-trait-fort bg-surface px-2 py-1 text-sm text-encre">
            {base.meta.annees_wp.map((a) => <option key={a} value={a}>{a}</option>)}
          </select>
        </label>
      </div>
      {e.locale != null && (
        <p className="m-0 text-[0.86rem] text-encre-2">
          {t("estFourchette", { min: entier(arrondi(e.min)), max: entier(arrondi(e.max)), ecart: nombre((100 * (e.max - e.min)) / e.centrale, 0) })}
        </p>
      )}
      <table className="w-full border-collapse text-[0.82rem]">
        <tbody>
          {methodes.filter(([, v]) => v != null).map(([nom, v, retenue]) => (
            <tr key={nom}>
              <td className={cellule}>{nom}{retenue && <span className="ml-1.5 text-[0.72rem] font-semibold text-accent">{t("estRetenue")}</span>}</td>
              <td className={`${cellule} chiffre text-right ${retenue ? "font-semibold" : ""}`}>{entier(arrondi(v!))}</td>
            </tr>
          ))}
        </tbody>
      </table>
      {e.avecBase < e.n && e.avecBase > 0 && (
        <p className="m-0 text-[0.78rem] text-discret">{t("estCouverture", { k: e.avecBase, n: e.n })}</p>
      )}

      <h4 className="etiquette m-0 mt-2">{t("estGroupes", { annee })}</h4>
      <table className="w-full border-collapse text-[0.82rem]">
        <tbody>
          {e.groupes.map((g) => (
            <tr key={g.cle}>
              <td className={cellule}>{t(`age.${g.cle}` as Cle)}</td>
              <td className={`${cellule} chiffre text-right`}>{entier(arrondi(g.valeur))}</td>
              <td className={`${cellule} chiffre w-16 text-right text-discret`}>{nombre(g.part, 1)} %</td>
            </tr>
          ))}
        </tbody>
      </table>
      <p className="m-0 text-[0.78rem] text-discret">
        {t("estNoteAges", { annee: e.anneeStructure })}{" "}
        {t(e.locale == null ? "estNoteMethodeWp" : fk ? "estNoteMethodeCalee" : "estNoteMethode")}
      </p>
    </div>
  );
}
