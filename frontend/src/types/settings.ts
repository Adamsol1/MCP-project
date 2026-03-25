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

/** User-configurable runtime controls for analysis-stage council runs. */
export interface CouncilSettings {
  /** Deliberation mode. */
  mode: "conference" | "quick";
  /** Number of rounds to run. */
  rounds: number;
  /** Timeout per round, in seconds. */
  timeoutSeconds: number;
  /** Whether to retry once/again when a vote marker is missing. */
  voteRetryEnabled: boolean;
  /** Maximum number of vote retry attempts. */
  voteRetryAttempts: number;
}

/**
 * The full shape of user-configurable application settings.
 * Persisted to localStorage under the key "mcp-settings".
 */
export interface Settings {
  /** Language the AI will use in its responses. */
  language: Language;
  /** Visual theme applied to the UI. */
  theme: Theme;
  /** Prompt context parameters auto-filled on every message send. */
  inputParameters: InputParameters;
  /** Council runtime controls used by the analysis panel. */
  councilSettings: CouncilSettings;
}

/**
 * Fallback values used on first launch or when localStorage is missing/corrupt.
 * English language, dark theme, and no pre-filled parameters.
 */
export const DEFAULT_SETTINGS: Settings = {
  language: "en",
  theme: "dark",
  inputParameters: {
    timeframe: "",
  },
  councilSettings: {
    mode: "conference",
    rounds: 2,
    timeoutSeconds: 180,
    voteRetryEnabled: true,
    voteRetryAttempts: 1,
  },
};
