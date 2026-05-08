import type { DialoguePhase, DialogueStage } from "../../types/dialogue";

/**
 * Maps a `DialogueStage` to the `DialoguePhase` that the workspace UI should display.
 *
 * The workspace has fewer distinct views than the backend has stages, so several
 * stages collapse to the same phase. Notably, `reviewing` maps to `"processing"`
 * (not `"collection"`) because the workspace treats it as a post-collection step.
 *
 * @param stage - The current dialogue stage, or undefined before the first backend response.
 * @returns The corresponding `DialoguePhase` for workspace rendering.
 */
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
