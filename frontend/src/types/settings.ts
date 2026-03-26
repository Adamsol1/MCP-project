/** Supported AI output languages. */
export type Language = "en" | "no";

/** Supported UI themes. */
export type Theme = "light" | "dark";

/**
 * Context parameters that are auto-injected into every prompt
 * so the AI has background information without needing to ask.
 * Add new fields here as the feature grows.
 */
export interface InputParameters {
  /** The time period the analysis should cover (e.g. "Last 30 days"). */
  timeframe: string;
}

/**
 * The full shape of user-configurable application settings.
 * Persisted to localStorage under the key "mcp-settings".
 */
export interface Settings {
  /** Language used to render the UI (menus, labels, etc.). */
  language: Language;
  /** Language the AI will use in its responses (sent to backend). */
  aiLanguage: Language;
  /** Visual theme applied to the UI. */
  theme: Theme;
  /** Prompt context parameters auto-filled on every message send. */
  inputParameters: InputParameters;
}

/**
 * Fallback values used on first launch or when localStorage is missing/corrupt.
 * English language, dark theme, and no pre-filled parameters.
 */
export const DEFAULT_SETTINGS: Settings = {
  language: "en",
  aiLanguage: "en",
  theme: "dark",
  inputParameters: {
    timeframe: "",
  },
};
