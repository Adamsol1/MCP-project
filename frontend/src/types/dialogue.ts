export type DialogueStage =
  | "initial"
  | "gathering"
  | "summary_confirming"
  | "pir_confirming"
  | "planning"
  | "plan_confirming"
  | "collecting"
  | "reviewing"
  | "complete";

export type DialogueSubState =
  | "awaiting_decision"
  | "awaiting_modifications"
  | "awaiting_gather_more"
  | null;

export type DialogueAction =
  | "ask_question"
  | "show_summary"
  | "show_pir"
  | "max_questions"
  | "show_plan"
  | "start_collecting"
  | "show_collection"
  | "error"
  | "complete";
