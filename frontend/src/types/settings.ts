/** Supported AI output languages. */
export type Language = "en" | "no";

/** Supported UI themes. */
export type Theme = "light" | "dark";

/** Per-web-source-tier timeframe codes (Serper date_restrict format). */
export interface SourceTimeframes {
  /** Government & official sources (.gov, .mil, ministry/agency sites). */
  web_gov: string;
  /** Think tanks & research institutions (RAND, CSIS, Chatham House, etc.). */
  web_think_tank: string;
  /** News & media outlets (Reuters, BBC, AP, FT, etc.). */
  web_news: string;
  /** Other / unclassified web sources. */
  web_other: string;
  /** AlienVault OTX threat intelligence feed. */
  otx: string;
}

/**
 * Context parameters that are auto-injected into every prompt
 * so the AI has background information without needing to ask.
 * Add new fields here as the feature grows.
 */
export interface InputParameters {
  /** The time period the analysis should cover (e.g. "Last 30 days"). */
  timeframe: string;
  /** Per-source-tier date window overrides. Empty string means no restriction. */
  sourceTimeframes: SourceTimeframes;
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
  /** Language used to render the UI (menus, labels, etc.). */
  language: Language;
  /** Language the AI will use in its responses (sent to backend). */
  aiLanguage: Language;
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
  aiLanguage: "en",
  theme: "dark",
  inputParameters: {
    timeframe: "",
    sourceTimeframes: {
      web_gov: "",
      web_think_tank: "",
      web_news: "",
      web_other: "",
      otx: "",
    },
  },
  councilSettings: {
    mode: "conference",
    rounds: 2,
    timeoutSeconds: 180,
    voteRetryEnabled: true,
    voteRetryAttempts: 1,
  },
};
