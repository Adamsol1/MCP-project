import {
  createContext,
  useState,
  useCallback,
  useEffect,
  useContext,
  type ReactNode,
} from "react";

import {
  DEFAULT_SETTINGS,
  type Settings,
  type Language,
  type Theme,
  type InputParameters,
} from "../types/settings";

const STORAGE_KEY = "mcp-settings";

export interface SettingsContextValue {
  settings: Settings;
  updateLanguage: (language: Language) => void;
  updateTheme: (theme: Theme) => void;
  updateInputParameters: (params: Partial<InputParameters>) => void;
}

export const SettingsContext = createContext<SettingsContextValue | null>(null);

function loadSettings(): Settings {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return DEFAULT_SETTINGS;
    return { ...DEFAULT_SETTINGS, ...JSON.parse(raw) };
  } catch {
    return DEFAULT_SETTINGS;
  }
}

function saveSettings(settings: Settings): void {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(settings));
}

export function SettingsProvider({ children }: { children: ReactNode }) {
  const [settings, setSettings] = useState<Settings>(loadSettings);

  useEffect(() => {
    saveSettings(settings);
  }, [settings]);

  const updateLanguage = useCallback((language: Language) => {
    setSettings((prev) => ({ ...prev, language }));
  }, []);

  const updateTheme = useCallback((theme: Theme) => {
    setSettings((prev) => ({ ...prev, theme }));
  }, []);

  const updateInputParameters = useCallback(
    (params: Partial<InputParameters>) => {
      setSettings((prev) => ({
        ...prev,
        inputParameters: { ...prev.inputParameters, ...params },
      }));
    },
    [],
  );

  const value: SettingsContextValue = {
    settings,
    updateLanguage,
    updateTheme,
    updateInputParameters,
  };

  return (
    <SettingsContext.Provider value={value}>
      {children}
    </SettingsContext.Provider>
  );
}

export function useSettings(): SettingsContextValue {
  const ctx = useContext(SettingsContext);
  if (!ctx) {
    throw new Error("useSettings must be used within a SettingsProvider");
  }
  return ctx;
}

