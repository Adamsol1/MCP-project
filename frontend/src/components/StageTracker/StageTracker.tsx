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

function phaseIndex(phase: DialoguePhase): number {
  // Council is a sub-mode of analysis — show Analysis as active
  const normalized = phase === "council" ? "analysis" : phase;
  return PHASE_ORDER.indexOf(normalized);
}

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
                <span className="flex items-center justify-center w-6 h-6 rounded-full bg-primary text-white text-xs font-bold">
                  {i + 1}
                </span>
              ) : (
                <span className="flex items-center justify-center w-6 h-6 rounded-full border-2 border-border text-text-muted text-xs font-bold">
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
