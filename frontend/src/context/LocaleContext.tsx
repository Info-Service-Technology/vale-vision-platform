import React, { useMemo, useState } from "react";
import { Lang, normalizeLang, translations } from "../i18n/translations";
import { LocaleContext } from "./localeContextCore";

export function LocaleProvider({ children }: { children: React.ReactNode }) {
  const [lang, setLangState] = useState<Lang>(() =>
    normalizeLang(localStorage.getItem("vale_lang") || navigator.language || "pt-BR")
  );

  const value = useMemo(
    () => ({
      lang,
      setLang: (next: Lang) => {
        const normalized = normalizeLang(next);
        localStorage.setItem("vale_lang", normalized);
        setLangState(normalized);
      },
      t: (key: string) => translations[lang][key] || key,
    }),
    [lang]
  );

  return <LocaleContext.Provider value={value}>{children}</LocaleContext.Provider>;
}