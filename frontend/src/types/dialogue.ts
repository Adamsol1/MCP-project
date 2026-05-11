/**
 * Represents the different phases of a dialogue.
 */
export type DialoguePhase =
  | "direction"
  | "collection"
  | "processing"
  | "analysis"
  | "council";

  /**
   * Represents the different stages of a dialogue, which are more granular than phases
   * and can be used to track progress within a phase.
   */
export type DialogueStage =
  | "initial"
  | "gathering"
  | "summary_confirming"
  | "pir_confirming"
  | "planning"
  | "plan_confirming"
  | "source_selecting"
  | "collecting"
  | "reviewing"
  | "processing"
  | "pending"
  | "idle"
  | "complete";

  /**
   * Represents sub-states that can be used to track specific conditions or requirements within a dialogue stage,
   * such as waiting for user input or a decision.
   */
export type DialogueSubState =
  | "awaiting_decision"
  | "awaiting_modifications"
  | "awaiting_gather_more"
  | null;


  /**
   * Represents the different actions that can be taken in a dialogue, which can trigger transitions between stages and phases.
   */
export type DialogueAction =
  | "ask_question"
  | "show_summary"
  | "show_pir"
  | "max_questions"
  | "show_plan"
  | "start_collecting"
  | "show_collection"
  | "show_processing"
  | "show_analysis"
  | "show_council"
  | "select_gaps"
  | "error"
  | "complete";
