import {
  createContext,
  useState,
  useCallback,
  useEffect,
  useLayoutEffect,
  useContext,
  type ReactNode,
} from "react";

import {
  DEFAULT_SETTINGS,
  type Settings,
  type Language,
  type Theme,
  type InputParameters,
  type CouncilSettings,
} from "../../types/settings";

/** localStorage key under which the settings object is stored as JSON. */
const STORAGE_KEY = "mcp-settings";

/**
 * The value exposed by SettingsContext to any consuming component.
 *
 * Provides read access to the current settings object and stable callbacks
 * to update individual slices of it. All callbacks are memoised with
 * useCallback so their references stay stable across re-renders.
 */
export interface SettingsContextValue {
  /** The current settings object. */
  settings: Settings;
  /** Replace the selected AI output language. */
  updateLanguage: (language: Language) => void;
  /** Switch the UI theme between light and dark. */
  updateTheme: (theme: Theme) => void;
  /**
   * Merge a partial InputParameters object into the current values.
   * Only the supplied fields are changed — others remain untouched.
   * This makes it safe to call with just `{ timeframe: "..." }` even
   * when more fields are added in the future.
   */
  updateInputParameters: (params: Partial<InputParameters>) => void;
  /** Merge partial council runtime settings into the current values. */
  updateCouncilSettings: (params: Partial<CouncilSettings>) => void;
}

/**
 * The React context object for settings.
 * Initialised with null — a null value at runtime means the consuming
 * component is not wrapped in a SettingsProvider (caught by useSettings).
 */
// eslint-disable-next-line react-refresh/only-export-components
export const SettingsContext = createContext<SettingsContextValue | null>(null);

/**
 * Reads the persisted settings from localStorage.
 * Spreads DEFAULT_SETTINGS first so any missing keys are always present,
 * even if the stored object is from an older version of the app.
 * Falls back to DEFAULT_SETTINGS silently if the stored value is corrupt.
 */
function loadSettings(): Settings {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return DEFAULT_SETTINGS;
    const parsed = JSON.parse(raw) as Partial<Settings>;
    return {
      ...DEFAULT_SETTINGS,
      ...parsed,
      inputParameters: {
        ...DEFAULT_SETTINGS.inputParameters,
        ...parsed.inputParameters,
      },
      councilSettings: {
        ...DEFAULT_SETTINGS.councilSettings,
        ...parsed.councilSettings,
      },
    };
  } catch {
    return DEFAULT_SETTINGS;
  }
}

/**
 * Serialises the settings object to localStorage as JSON.
 * Called by a useEffect inside SettingsProvider after every state change.
 */
function saveSettings(settings: Settings): void {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(settings));
}

/**
 * Provides settings state and mutation callbacks to the entire component tree.
 *
 * State is initialised by reading from localStorage (via the loadSettings
 * initialiser function), so user preferences survive page reloads.
 * A useEffect persists every state change back to localStorage immediately
 * after each render to prevent data loss on tab close.
 *
 * Provider order in main.tsx: SettingsProvider is the outermost data provider
 * so settings are available to ToastProvider and ConversationProvider if needed.
 */
export function SettingsProvider({ children }: { children: ReactNode }) {
  // Pass loadSettings as a reference (not a call) so React only runs it once.
  const [settings, setSettings] = useState<Settings>(loadSettings);

  // Persist the full settings object to localStorage after every state change.
  useEffect(() => {
    saveSettings(settings);
  }, [settings]);

  // Sync <html class="dark"> before paint to prevent flash of wrong theme.
  useLayoutEffect(() => {
    document.documentElement.classList.toggle(
      "dark",
      settings.theme === "dark",
    );
  }, [settings.theme]);

  const updateLanguage = useCallback((language: Language) => {
    setSettings((prev) => ({ ...prev, language }));
  }, []);

  const updateTheme = useCallback((theme: Theme) => {
    setSettings((prev) => ({ ...prev, theme }));
  }, []);

  /**
   * Merges only the supplied fields into inputParameters.
   * The spread pattern `{ ...prev.inputParameters, ...params }` ensures
   * future fields added to InputParameters are never accidentally wiped.
   */
  const updateInputParameters = useCallback(
    (params: Partial<InputParameters>) => {
      setSettings((prev) => ({
        ...prev,
        inputParameters: { ...prev.inputParameters, ...params },
      }));
    },
    [],
  );

  const updateCouncilSettings = useCallback(
    (params: Partial<CouncilSettings>) => {
      setSettings((prev) => ({
        ...prev,
        councilSettings: { ...prev.councilSettings, ...params },
      }));
    },
    [],
  );

  const value: SettingsContextValue = {
    settings,
    updateLanguage,
    updateTheme,
    updateInputParameters,
    updateCouncilSettings,
  };

  return (
    <SettingsContext.Provider value={value}>
      {children}
    </SettingsContext.Provider>
  );
}

/**
 * Convenience hook for consuming SettingsContext.
 *
 * Throws a descriptive error when used outside a SettingsProvider so
 * the developer gets a clear message instead of a cryptic null-access crash.
 */
// eslint-disable-next-line react-refresh/only-export-components
export function useSettings(): SettingsContextValue {
  const ctx = useContext(SettingsContext);
  if (!ctx) {
    throw new Error("useSettings must be used within a SettingsProvider");
  }
  return ctx;
}
