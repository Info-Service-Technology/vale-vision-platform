import { createContext } from "react";
import { Lang } from "../i18n/translations";

export interface LocaleContextValue {
  lang: Lang;
  setLang: (lang: Lang) => void;
  t: (key: string) => string;
}

export const LocaleContext = createContext<LocaleContextValue | undefined>(undefined);