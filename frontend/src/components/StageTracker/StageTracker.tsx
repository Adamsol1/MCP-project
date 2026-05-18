import type { DialoguePhase } from "../../types/dialogue";

const STAGES: { phase: DialoguePhase; label: string }[] = [
  { phase: "direction", label: "Direction" },
  { phase: "collection", label: "Collection" },
  { phase: "processing", label: "Processing" },
  { phase: "analysis", label: "Analysis" },
];

const PHASE_ORDER: DialoguePhase[] = [
  "direction",
  "collection",
  "processing",
  "analysis",
];

/**
 * Returns the index of the given phase in the phase order array.
 * @param phase The dialogue phase for which to find the index.
 * @returns The index of the phase in the PHASE_ORDER array, or -1 if not found.
 * Note: The "council" phase is treated as a sub-mode of "analysis" and will return the same index as "analysis".
 */
function phaseIndex(phase: DialoguePhase): number {
  // Council is a sub-mode of analysis — show Analysis as active
  const normalized = phase === "council" ? "analysis" : phase;
  return PHASE_ORDER.indexOf(normalized);
}

/**
 * Renders a stage tracker component that visually represents the current phase of a dialogue process.
 * Each stage is represented by a circle with a label, and the active stage is highlighted.
 * Completed stages are marked with a check icon, while upcoming stages are shown with a numbered circle.
 *
 * @param activePhase The current active dialogue phase to determine which stage is active in the tracker.
 * @returns A React component that displays the stage tracker with appropriate styling for completed, active, and upcoming stages.
 */
function CheckIcon() {
  return (
    <svg
      width="14"
      height="14"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="3"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      <path d="M5 13l4 4L19 7" />
    </svg>
  );
}

/**
 * Renders a right-pointing chevron icon used as a separator between stages in the stage tracker.
 * @returns  A React component that displays a chevron icon with appropriate styling.
 */
function ChevronRight() {
  return (
    <svg
      width="14"
      height="14"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2.5"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
      className="text-text-muted"
    >
      <path d="M9 6l6 6-6 6" />
    </svg>
  );
}

/**
 *  StageTracker component visually represents the current phase of a dialogue process, showing completed, active, and upcoming stages with appropriate styling.
 * @param Object containing the activePhase prop, which indicates the current dialogue phase to determine the active stage in the tracker.
 * @returns A React component that displays the stage tracker with circles and labels for each stage, using icons and styling to differentiate between completed, active, and upcoming stages.
 */
export default function StageTracker({
  activePhase,
}: {
  activePhase: DialoguePhase;
}) {
  const activeIdx = phaseIndex(activePhase);

  return (
    <div className="flex items-center">
      <div className="flex items-center gap-1">
        {STAGES.map((stage, i) => {
          const isCompleted = i < activeIdx;
          const isActive = i === activeIdx;

          return (
            <div key={stage.phase} className="flex items-center gap-1">
              {i > 0 && (
                <span className="mx-1">
                  <ChevronRight />
                </span>
              )}

              {/* Circle indicator */}
              {isCompleted ? (
                <span className="flex items-center justify-center w-6 h-6 rounded-full bg-success text-white">
                  <CheckIcon />
                </span>
              ) : isActive ? (
                <span className="flex items-center justify-center w-6 h-6 rounded-full bg-primary text-text-inverse text-xs font-bold">
                  {i + 1}
                </span>
              ) : (
                <span className="flex items-center justify-center w-6 h-6 rounded-full border-2 border-border text-text-secondary text-xs font-bold">
                  {i + 1}
                </span>
              )}

              {/* Label */}
              <span
                className={`text-sm font-medium ${
                  isActive
                    ? "text-text-primary"
                    : isCompleted
                      ? "text-text-primary"
                      : "text-text-muted"
                }`}
              >
                {stage.label}
              </span>
            </div>
          );
        })}
      </div>
    </div>
  );
}
