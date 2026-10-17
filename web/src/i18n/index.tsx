import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from "react";
import { choisirLangueNombres } from "../lib/format";
import { en } from "./en";
import { fr, type Cle } from "./fr";
import { mg } from "./mg";

export type Langue = "fr" | "mg" | "en";
export const LANGUES: Record<Langue, string> = { fr: "Français", mg: "Malagasy", en: "English" };
const TEXTES: Record<Langue, Partial<Record<Cle, string>>> = { fr, mg, en };
const estLangue = (l: string | null): l is Langue => l != null && l in TEXTES;

type Traduire = (cle: Cle, valeurs?: Record<string, string | number>) => string;
const Contexte = createContext<{ langue: Langue; setLangue: (l: Langue) => void; t: Traduire } | null>(null);

// Ordre : ?lang= dans l'adresse (liens envoyés aux partenaires), choix mémorisé, navigateur anglophone
function langueInitiale(): Langue {
  const parametre = new URLSearchParams(window.location.search).get("lang");
  if (estLangue(parametre)) return parametre;
  try {
    const memorisee = localStorage.getItem("mdg-langue");
    if (estLangue(memorisee)) return memorisee;
  } catch { /* stockage indisponible */ }
  return navigator.language?.toLowerCase().startsWith("en") ? "en" : "fr";
}

export function FournisseurLangue({ children }: { children: ReactNode }) {
  const [langue, setLangue] = useState<Langue>(langueInitiale);
  choisirLangueNombres(langue);
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
