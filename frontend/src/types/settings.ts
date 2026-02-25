export type Language = "en" | "no";
export type Theme = "light" | "dark";

export interface InputParameters {
  timeframe: string;
}

export interface Settings {
  language: Language;
  theme: Theme;
  inputParameters: InputParameters;
}

export const DEFAULT_SETTINGS: Settings = {
  language: "en",
  theme: "dark",
  inputParameters: {
    timeframe: "",
  },
};
