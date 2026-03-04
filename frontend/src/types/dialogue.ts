export type DialogueStage =
  | "initial"
  | "gathering"
  | "summary_confirming"
  | "pir_confirming"
  | "complete";

export type DialogueSubState =
  | "awaiting_decision"
  | "awaiting_modifications"
  | null;
