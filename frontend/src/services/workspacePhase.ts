import type { Phase } from "../contexts/WorkspaceContext/WorkspaceContext";
import type { DialogueStage } from "../types/dialogue";

export function getWorkspacePhaseForDialogueStage(
  stage: DialogueStage | undefined,
): Phase {
  switch (stage) {
    case "source_selecting":
    case "collecting":
    case "reviewing":
      return "collection";
    case "complete":
      return "analysis";
    case "initial":
    case "gathering":
    case "summary_confirming":
    case "pir_confirming":
    case "planning":
    case "plan_confirming":
    default:
      return "direction";
  }
}
