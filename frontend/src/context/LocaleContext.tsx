import React, { createContext, useContext, useMemo, useState } from "react";
import { Lang, translations } from "../i18n/translations";

interface LocaleContextValue { lang: Lang; setLang: (lang: Lang) => void; t: (key: string) => string; }
const LocaleContext = createContext<LocaleContextValue | undefined>(undefined);
export function LocaleProvider({ children }: { children: React.ReactNode }) {
  const [lang, setLangState] = useState<Lang>(() => (localStorage.getItem("vale_lang") as Lang) || "pt-BR");
  const value = useMemo(() => ({ lang, setLang: (next: Lang) => { localStorage.setItem("vale_lang", next); setLangState(next); }, t: (key: string) => translations[lang][key] || key }), [lang]);
  return <LocaleContext.Provider value={value}>{children}</LocaleContext.Provider>;
}
export function useLocale() { const ctx = useContext(LocaleContext); if (!ctx) throw new Error("useLocale must be used inside LocaleProvider"); return ctx; }
