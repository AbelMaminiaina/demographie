// Export de tableaux en CSV, lisibles directement par Excel en français.

/** Téléchargement d'un tableau en CSV (séparateur « ; » et BOM, pour Excel en français). */
export function telechargerCsv(nomFichier: string, lignes: (string | number | null | undefined)[][]) {
  const champ = (v: string | number | null | undefined) => {
    if (v == null) return "";
    const s = typeof v === "number" ? String(v).replace(".", ",") : v;
    return /[;"\n]/.test(s) ? `"${s.replaceAll('"', '""')}"` : s;
  };
  const texte = "﻿" + lignes.map((l) => l.map(champ).join(";")).join("\r\n");
  const lien = document.createElement("a");
  lien.href = URL.createObjectURL(new Blob([texte], { type: "text/csv;charset=utf-8" }));
  lien.download = nomFichier;
  lien.click();
  setTimeout(() => URL.revokeObjectURL(lien.href), 1000);
}
