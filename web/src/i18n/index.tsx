import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from "react";
import { fr, type Cle } from "./fr";
import { mg } from "./mg";

export type Langue = "fr" | "mg";
const TEXTES: Record<Langue, Partial<Record<Cle, string>>> = { fr, mg };

type Traduire = (cle: Cle, valeurs?: Record<string, string | number>) => string;
const Contexte = createContext<{ langue: Langue; setLangue: (l: Langue) => void; t: Traduire } | null>(null);

function langueInitiale(): Langue {
  try {
    if (localStorage.getItem("mdg-langue") === "mg") return "mg";
  } catch { /* stockage indisponible */ }
  return "fr";
}

export function FournisseurLangue({ children }: { children: ReactNode }) {
  const [langue, setLangue] = useState<Langue>(langueInitiale);
  useEffect(() => {
    document.documentElement.lang = langue;
    try { localStorage.setItem("mdg-langue", langue); } catch { /* stockage indisponible */ }
  }, [langue]);
  const t = useCallback<Traduire>((cle, valeurs) => {
    let texte = TEXTES[langue][cle] ?? fr[cle] ?? cle;
    if (valeurs) for (const [k, v] of Object.entries(valeurs)) texte = texte.replaceAll(`{${k}}`, String(v));
    return texte;
  }, [langue]);
  const valeur = useMemo(() => ({ langue, setLangue, t }), [langue, t]);
  return <Contexte.Provider value={valeur}>{children}</Contexte.Provider>;
}

export function useLangue() {
  const c = useContext(Contexte);
  if (!c) throw new Error("useLangue doit être utilisé dans FournisseurLangue");
  return c;
}
