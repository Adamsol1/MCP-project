import type { DialoguePhase, DialogueStage } from "../../types/dialogue";

export function getWorkspacePhaseForDialogueStage(
  stage: DialogueStage | undefined,
): DialoguePhase {
  switch (stage) {
    case "processing":
    case "complete":
      return "processing";
    case "planning":
    case "plan_confirming":
    case "source_selecting":
    case "collecting":
      return "collection";
    case "reviewing":
      return "processing";
    case "initial":
    case "gathering":
    case "summary_confirming":
    case "pir_confirming":
    default:
      return "direction";
  }
}
