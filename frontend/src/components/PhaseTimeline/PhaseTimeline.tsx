import { useState, type ReactNode } from "react";
import type { DialogueStage } from "../../types/dialogue";
import type { Phase, PhaseStatus } from "../../types/phase";
import { PHASES } from "../../types/phase";
import { stageToPhase, getPhaseStatus } from "../../utils/phaseMapping";
import PerspectiveSelector from "../PerspectiveSelector/PerspectiveSelector";
import { useSettings } from "../../contexts/SettingsContext";

interface PhaseTimelineProps {
  stage: DialogueStage;
  selectedPerspectives: string[];
  onPerspectiveChange: (perspectives: string[]) => void;
}

function StatusIndicator({ status }: { status: PhaseStatus }) {
  if (status === "active") {
    return (
      <div className="w-4 h-4 rounded-full border-2 border-primary border-t-transparent animate-spin shrink-0" />
    );
  }

  if (status === "completed") {
    return (
      <svg
        width="16"
        height="16"
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        strokeWidth="2.5"
        strokeLinecap="round"
        strokeLinejoin="round"
        className="text-success shrink-0"
        aria-hidden="true"
      >
        <path d="M20 6L9 17l-5-5" />
      </svg>
    );
  }

  return null;
}

function PhaseCard({
  label,
  description,
  status,
  isExpanded,
  onToggle,
  children,
}: {
  label: string;
  description: string;
  status: PhaseStatus;
  isExpanded: boolean;
  onToggle: () => void;
  children?: ReactNode;
}) {
  const borderColor =
    status === "active"
      ? "border-l-primary"
      : status === "completed"
        ? "border-l-success"
        : "border-l-border-muted";

  const bgColor =
    status === "active"
      ? "bg-surface"
      : "bg-surface-muted";

  return (
    <div
      className={`rounded-md border border-border-muted border-l-[3px] ${borderColor} ${bgColor}`}
    >
      <button
        onClick={onToggle}
        className="w-full flex items-center justify-between gap-2 px-3 py-2.5 text-left"
      >
        <div className="flex-1 min-w-0">
          <span
            className={`text-sm font-semibold block ${
              status === "upcoming" ? "text-text-muted" : "text-text-primary"
            }`}
          >
            {label}
          </span>
          <span className="text-[10px] uppercase tracking-wider text-text-secondary block mt-0.5">
            {description}
          </span>
        </div>

        <div className="flex items-center gap-1.5 shrink-0">
          <StatusIndicator status={status} />
          <span className="text-xs text-text-muted">
            {isExpanded ? "Collapse" : "Expand"}
          </span>
        </div>
      </button>

      {isExpanded && (
        <div className="px-3 pb-2.5">
          {children}
        </div>
      )}
    </div>
  );
}

export function PhaseTimeline({
  stage,
  selectedPerspectives,
  onPerspectiveChange,
}: PhaseTimelineProps) {
  const activePhase = stageToPhase(stage);
  const [expandedPhases, setExpandedPhases] = useState<Set<Phase>>(new Set());
  const { settings, updateInputParameters } = useSettings();

  const toggleExpanded = (phaseId: Phase) => {
    setExpandedPhases((prev) => {
      const next = new Set(prev);
      if (next.has(phaseId)) {
        next.delete(phaseId);
      } else {
        next.add(phaseId);
      }
      return next;
    });
  };

  return (
    <div>
      <p className="text-xs font-semibold uppercase tracking-wider text-text-secondary mb-3">
        Phases
      </p>
      <div className="flex flex-col gap-1.5">
        {PHASES.map((phase) => {
          const status = getPhaseStatus(phase.id, activePhase);
          return (
            <PhaseCard
              key={phase.id}
              label={phase.label}
              description={phase.description}
              status={status}
              isExpanded={expandedPhases.has(phase.id)}
              onToggle={() => toggleExpanded(phase.id)}
            >
              {phase.id === "direction" ? (
                <div className="flex flex-col gap-3 pt-1">
                  <PerspectiveSelector
                    selected={selectedPerspectives}
                    onChange={onPerspectiveChange}
                  />
                  <div className="flex flex-col gap-1">
                    <label
                      htmlFor="direction-timeframe"
                      className="text-xs font-semibold uppercase tracking-wider text-text-secondary"
                    >
                      Timeframe
                    </label>
                    <input
                      id="direction-timeframe"
                      type="text"
                      value={settings.inputParameters.timeframe}
                      onChange={(e) =>
                        updateInputParameters({ timeframe: e.target.value })
                      }
                      placeholder="e.g. Last 30 days"
                      className="w-full px-2 py-1.5 text-sm rounded border border-border bg-surface text-text-primary placeholder:text-text-muted focus:outline-none focus:ring-1 focus:ring-primary"
                    />
                  </div>
                </div>
              ) : (
                <p className="text-xs text-text-secondary leading-relaxed">
                  {status === "active" && "This phase is currently in progress."}
                  {status === "completed" && "This phase has been completed."}
                  {status === "upcoming" && "This phase has not started yet."}
                </p>
              )}
            </PhaseCard>
          );
        })}
      </div>
    </div>
  );
}
