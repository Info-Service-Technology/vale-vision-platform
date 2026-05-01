import { useContext } from "react";
import { LocaleContext } from "../context/localeContextCore";

export function useLocale() {
  const ctx = useContext(LocaleContext);

  if (!ctx) {
    throw new Error("useLocale must be used inside LocaleProvider");
  }

  return ctx;
}