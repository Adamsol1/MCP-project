import { useState } from "react";
import type {
  CollectionCoverageResult,
  ConfidenceTier,
  CoverageFindingRef,
} from "../../types/analysis";

interface CollectionCoverageViewProps {
  coverage: CollectionCoverageResult;
  onGoBackToCollection?: () => void;
}

// ---------------------------------------------------------------------------
// Tier helpers
// ---------------------------------------------------------------------------

const TIER_BADGE: Record<
  ConfidenceTier,
  { label: string; bg: string; text: string; border: string }
> = {
  low: {
    label: "Low",
    bg: "bg-error-subtle",
    text: "text-error-text",
    border: "border-error/30",
  },
  moderate: {
    label: "Moderate",
    bg: "bg-warning-subtle",
    text: "text-warning-text",
    border: "border-warning/30",
  },
  high: {
    label: "High",
    bg: "bg-success-subtle",
    text: "text-success-text",
    border: "border-success/30",
  },
  assessed: {
    label: "Assessed",
    bg: "bg-success-subtle",
    text: "text-success-text",
    border: "border-success/30",
  },
};

function TierBadge({
  tier,
  score,
}: {
  tier: ConfidenceTier;
  score?: number;
}) {
  const [showScore, setShowScore] = useState(false);
  const styles = TIER_BADGE[tier];

  return (
    <span
      title={score !== undefined ? `Raw score: ${score.toFixed(2)}` : undefined}
      onMouseEnter={() => setShowScore(true)}
      onMouseLeave={() => setShowScore(false)}
      className={`inline-flex cursor-default items-center rounded-full border px-2.5 py-0.5 text-[11px] font-semibold uppercase tracking-[0.12em] transition-all ${styles.bg} ${styles.text} ${styles.border}`}
    >
      {showScore && score !== undefined ? score.toFixed(2) : styles.label}
    </span>
  );
}

const SOURCE_LABELS: Record<string, string> = {
  knowledge_bank: "Knowledge Bank",
  otx: "AlienVault OTX",
  web_search: "Web Search",
  uploaded: "Uploaded",
  other: "Other",
};

function sourceLabel(src: string) {
  return SOURCE_LABELS[src] ?? src;
}

function FindingRefList({ findings }: { findings: CoverageFindingRef[] }) {
  if (findings.length === 0) return null;
  return (
    <div className="space-y-1.5">
      <p className="text-[10px] font-semibold uppercase tracking-widest text-text-muted">
        Contributing Findings
      </p>
      {findings.map((f) => (
        <div
          key={f.id}
          className="flex items-start gap-2 rounded-lg border border-border-muted bg-surface px-2.5 py-1.5"
        >
          <span className="mt-0.5 shrink-0 rounded border border-border-muted bg-surface-muted px-1 py-px text-[10px] font-mono font-semibold text-text-muted">
            {f.id}
          </span>
          <div className="min-w-0 flex-1">
            <p className="text-xs font-medium leading-snug text-text-primary">
              {f.title}
            </p>
            <p className="mt-0.5 text-[10px] text-text-muted">
              {sourceLabel(f.source)}
            </p>
          </div>
        </div>
      ))}
    </div>
  );
}

function PriorityBadge({ priority }: { priority: string }) {
  const styles =
    priority === "high"
      ? "bg-error-subtle text-error-text border-error/20"
      : priority === "medium"
        ? "bg-warning-subtle text-warning-text border-warning/20"
        : "bg-surface text-text-muted border-border";
  return (
    <span
      className={`inline-flex items-center rounded-full border px-2 py-0.5 text-[10px] font-medium uppercase tracking-widest ${styles}`}
    >
      {priority}
    </span>
  );
}

// ---------------------------------------------------------------------------
// Aggregate bar
// ---------------------------------------------------------------------------

function AggregateBar({ score }: { score: number }) {
  const pct = Math.round(score * 100);
  const color =
    score >= 0.9
      ? "bg-success-dark"
      : score >= 0.7
        ? "bg-success"
        : score >= 0.4
          ? "bg-warning"
          : "bg-error";
  return (
    <div className="h-1.5 w-full overflow-hidden rounded-full bg-border/40">
      <div
        className={`h-full rounded-full transition-all duration-500 ${color}`}
        style={{ width: `${pct}%` }}
      />
    </div>
  );
}

// ---------------------------------------------------------------------------
// Per-PIR row (expandable)
// ---------------------------------------------------------------------------

function PirRow({
  pir,
}: {
  pir: CollectionCoverageResult["per_pir"][number];
}) {
  const [expanded, setExpanded] = useState(false);

  return (
    <div className="border-b border-border last:border-none">
      <button
        type="button"
        onClick={() => setExpanded((v) => !v)}
        className="flex w-full items-start gap-3 px-4 py-3 text-left transition-colors hover:bg-surface/60"
      >
        {/* Expand chevron */}
        <span
          className={`mt-0.5 shrink-0 text-text-muted transition-transform duration-150 ${expanded ? "rotate-90" : ""}`}
        >
          ▶
        </span>

        {/* PIR question (truncated) */}
        <p className="flex-1 text-sm leading-5 text-text-primary line-clamp-2">
          {pir.pir_question}
        </p>

        {/* Meta badges */}
        <div className="ml-2 flex shrink-0 flex-col items-end gap-1.5">
          <TierBadge tier={pir.tier} score={pir.score} />
          <PriorityBadge priority={pir.priority} />
        </div>
      </button>

      {expanded && (
        <div className="px-4 pb-4 pt-1 space-y-3">
          {/* Full question */}
          <p className="text-xs leading-5 text-text-secondary">{pir.pir_question}</p>

          {/* Stats row */}
          <div className="flex flex-wrap gap-4 text-xs text-text-secondary">
            <span>
              <span className="font-medium text-text-primary">{pir.finding_count}</span>{" "}
              finding{pir.finding_count !== 1 ? "s" : ""}
            </span>
            <span>
              <span className="font-medium text-text-primary">
                {pir.source_types.length}
              </span>{" "}
              source type{pir.source_types.length !== 1 ? "s" : ""}
              {pir.source_types.length > 0 && (
                <span className="ml-1 text-text-muted">
                  ({pir.source_types.join(", ")})
                </span>
              )}
            </span>
            {pir.has_gap_flag && (
              <span className="text-warning-text font-medium">⚠ Gap flagged</span>
            )}
          </div>

          {/* Finding references */}
          <FindingRefList findings={pir.findings ?? []} />

          {/* Rationale */}
          <p className="rounded-lg border border-border bg-surface px-3 py-2 text-xs leading-5 text-text-secondary">
            {pir.rationale}
          </p>
        </div>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Main component
// ---------------------------------------------------------------------------

export default function CollectionCoverageView({
  coverage,
  onGoBackToCollection,
}: CollectionCoverageViewProps) {
  const { per_pir, aggregate_tier, aggregate_score, summary } = coverage;
  const aggStyles = TIER_BADGE[aggregate_tier];
  const isLow = aggregate_tier === "low";

  return (
    <div className="space-y-3">
      <p className="text-xs font-medium uppercase tracking-[0.12em] text-text-muted">
        Collection Coverage
      </p>

      <div className="overflow-hidden rounded-3xl border border-border bg-surface shadow-sm">
        {/* Header */}
        <div className="flex items-center justify-between gap-4 px-5 py-4">
          <div className="space-y-1 flex-1 min-w-0">
            <div className="flex items-center gap-2.5 flex-wrap">
              <TierBadge tier={aggregate_tier} score={aggregate_score} />
              <span className="text-[11px] text-text-muted">
                {per_pir.length} PIR{per_pir.length !== 1 ? "s" : ""} assessed
              </span>
            </div>
            <p className="text-sm leading-5 text-text-secondary">{summary}</p>
            <AggregateBar score={aggregate_score} />
          </div>

          {isLow && onGoBackToCollection && (
            <button
              type="button"
              onClick={onGoBackToCollection}
              className={`shrink-0 rounded-xl border px-4 py-2 text-xs font-medium transition-colors ${aggStyles.bg} ${aggStyles.text} ${aggStyles.border} hover:brightness-95`}
            >
              Back to Collection
            </button>
          )}
        </div>

        {/* Per-PIR table */}
        {per_pir.length > 0 && (
          <div className="border-t border-border">
            <p className="px-4 py-2 text-[10px] font-semibold uppercase tracking-widest text-text-muted">
              Per-PIR Breakdown
            </p>
            {per_pir.map((pir) => (
              <PirRow key={pir.pir_index} pir={pir} />
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
