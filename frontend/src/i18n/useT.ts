import { useSettings } from "../contexts/SettingsContext/SettingsContext";
import { en, type Translations } from "./en";
import { no } from "./no";

const translations: Record<string, Translations> = { en, no };
export type { Translations };

/** Returns the translation object for the user's currently selected language. */
export function useT(): Translations {
  const { settings } = useSettings();
  return translations[settings.language] ?? en;
}
