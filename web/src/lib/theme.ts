import { useEffect, useState } from "react";

export type ModeTheme = "auto" | "clair" | "sombre";

function modeInitial(): ModeTheme {
  try {
    const m = localStorage.getItem("mdg-theme");
    if (m === "clair" || m === "sombre") return m;
  } catch { /* stockage indisponible */ }
  return "auto";
}

/** Thème choisi (auto, clair, sombre) et thème effectif (sombre ou non), appliqué sur <html data-theme>. */
export function useTheme() {
  const [mode, setMode] = useState<ModeTheme>(modeInitial);
  const requete = typeof window !== "undefined" ? window.matchMedia("(prefers-color-scheme: dark)") : null;
  const [systemeSombre, setSystemeSombre] = useState(!!requete?.matches);

  useEffect(() => {
    if (!requete) return;
    const ecouter = (e: MediaQueryListEvent) => setSystemeSombre(e.matches);
    requete.addEventListener("change", ecouter);
    return () => requete.removeEventListener("change", ecouter);
  }, [requete]);

  useEffect(() => {
    const racine = document.documentElement;
    if (mode === "auto") delete racine.dataset.theme;
    else racine.dataset.theme = mode === "sombre" ? "dark" : "light";
    try {
      if (mode === "auto") localStorage.removeItem("mdg-theme");
      else localStorage.setItem("mdg-theme", mode);
    } catch { /* stockage indisponible */ }
  }, [mode]);

  return { mode, setMode, sombre: mode === "sombre" || (mode === "auto" && systemeSombre) };
}
