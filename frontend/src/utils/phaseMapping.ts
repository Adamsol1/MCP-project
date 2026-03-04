import type { DialogueStage } from "../types/dialogue";
import type { Phase, PhaseStatus } from "../types/phase";
import { PHASES } from "../types/phase";

/**
 * Maps a DialogueStage to the corresponding Phase.
 *
 *   "initial" | "gathering" | "summary_confirming" | "pir_confirming" → "direction"
 *   "complete"                                                       → null (no active phase)
 */
export function stageToPhase(stage: DialogueStage): Phase | null {
  switch (stage) {
    case "initial":
    case "gathering":
    case "summary_confirming":
    case "pir_confirming":
      return "direction";
    case "complete":
      return null;
    default:
      return "direction";
  }
}

function phaseIndex(phase: Phase | null): number {
  if (phase === null) return PHASES.length;
  return PHASES.findIndex((p) => p.id === phase);
}

export function getPhaseStatus(
  phaseId: Phase,
  activePhase: Phase | null,
): PhaseStatus {
  const activeIdx = phaseIndex(activePhase);
  const thisIdx = PHASES.findIndex((p) => p.id === phaseId);

  if (thisIdx < activeIdx) return "completed";
  if (thisIdx === activeIdx) return "active";
  return "upcoming";
}
