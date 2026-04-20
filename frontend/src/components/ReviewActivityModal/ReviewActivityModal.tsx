import type { PhaseReviewItem } from "../../types/conversation";
import type { CollectedItem, CollectionDisplayData, CollectionSourceSummary, PirData, PirItem, ProcessingData, ProcessingFinding } from "../../types/conversation";
import type { Analysis } from "../../types/analysis";

interface ReviewActivityModalProps {
  isOpen: boolean;
  onClose: () => void;
  activity: PhaseReviewItem[];
  /** If set, this attempt number will be expanded by default. */
  focusAttempt?: number;
}

// ── Inline text formatter ──────────────────────────────────────────────────────

function InlineFormatted({ text }: { text: string }) {
  const parts = text.split(/(\*\*[^*]+\*\*|\*[^*]+\*)/g);
  return (
    <>
      {parts.map((part, i) => {
        if (part.startsWith("**") && part.endsWith("**"))
          return <strong key={i} className="font-semibold text-text-primary">{part.slice(2, -2)}</strong>;
        if (part.startsWith("*") && part.endsWith("*"))
          return <em key={i}>{part.slice(1, -1)}</em>;
        return <span key={i}>{part}</span>;
      })}
    </>
  );
}

function FormattedReviewText({ text }: { text: string }) {
  const lines = text.split("\n");
  const elements: React.ReactNode[] = [];
  lines.forEach((line, i) => {
    const trimmed = line.trim();
    if (!trimmed) { elements.push(<div key={i} className="h-2" />); return; }
    const listMatch = trimmed.match(/^(\d+)[.)]\s+(.+)$/);
    if (listMatch) {
      elements.push(
        <div key={i} className="flex gap-2 mb-1">
          <span className="shrink-0 text-text-muted font-medium">{listMatch[1]}.</span>
          <span className="text-xs text-text-secondary leading-relaxed"><InlineFormatted text={listMatch[2]} /></span>
        </div>
      );
      return;
    }
    elements.push(
      <p key={i} className="text-xs text-text-secondary leading-relaxed mb-1">
        <InlineFormatted text={trimmed} />
      </p>
    );
  });
  return <div>{elements}</div>;
}

// ── Phase-specific transcript renderers ───────────────────────────────────────

const PRIORITY_STYLES: Record<string, string> = {
  high: "bg-error-subtle text-error-text",
  medium: "bg-warning-subtle text-warning-text",
  low: "bg-info-subtle text-info-text",
};

function PirTranscript({ data }: { data: PirData }) {
  return (
    <div className="space-y-4">
      {data.reasoning && (
        <div>
          <p className="text-[10px] font-semibold uppercase tracking-widest text-text-muted mb-1">
            Reasoning
          </p>
          <FormattedReviewText text={data.reasoning} />
        </div>
      )}
      {data.pirs && data.pirs.length > 0 && (
        <div className="space-y-2">
          <p className="text-[10px] font-semibold uppercase tracking-widest text-text-muted">
            Intelligence Requirements ({data.pirs.length})
          </p>
          {data.pirs.map((pir: PirItem, i: number) => (
            <div key={i} className="rounded-lg border border-border-muted bg-surface-muted p-3 space-y-1.5">
              <div className="flex items-start justify-between gap-2">
                <p className="text-xs font-medium text-text-primary leading-snug flex-1">{pir.question}</p>
                {pir.priority && (
                  <span className={`shrink-0 rounded px-1.5 py-0.5 text-[10px] font-semibold uppercase tracking-wide ${PRIORITY_STYLES[pir.priority] ?? "bg-surface-elevated text-text-muted"}`}>
                    {pir.priority}
                  </span>
                )}
              </div>
              {pir.rationale && (
                <p className="text-xs text-text-secondary leading-relaxed">{pir.rationale}</p>
              )}
            </div>
          ))}
        </div>
      )}
      {data.pir_text && !data.pirs?.length && (
        <p className="text-xs text-text-secondary leading-relaxed whitespace-pre-wrap">{data.pir_text}</p>
      )}
    </div>
  );
}

function CollectionTranscript({ data, reviewerSuggestions }: { data: CollectionDisplayData; reviewerSuggestions?: string | null }) {
  const bySource = data.source_summary ?? [];
  const items = data.collected_data ?? [];

  return (
    <div className="space-y-4">
      {bySource.length > 0 && (
        <div>
          <p className="text-[10px] font-semibold uppercase tracking-widest text-text-muted mb-1.5">
            Sources ({bySource.length})
          </p>
          <div className="flex flex-wrap gap-1.5">
            {bySource.map((s: CollectionSourceSummary) => (
              <span
                key={s.display_name}
                className="rounded px-2 py-0.5 text-xs font-medium bg-surface-elevated text-text-secondary border border-border-muted"
              >
                {s.display_name}
                {s.count > 1 && (
                  <span className="ml-1 text-text-muted">×{s.count}</span>
                )}
              </span>
            ))}
          </div>
        </div>
      )}
      {items.length > 0 && (
        <div className="space-y-2">
          <p className="text-[10px] font-semibold uppercase tracking-widest text-text-muted">
            Collected Items ({items.length})
          </p>
          {items.map((item: CollectedItem, i: number) => (
            <div key={i} className="rounded-lg border border-border-muted bg-surface-muted p-3 space-y-1.5">
              <div className="flex items-start justify-between gap-2">
                <p className="text-xs font-semibold text-text-primary leading-snug flex-1">
                  {item.title ?? item.resource_id ?? item.source}
                </p>
                <span className="shrink-0 rounded px-1.5 py-0.5 text-[10px] font-medium bg-surface-elevated text-text-muted border border-border-muted">
                  {item.source}
                </span>
              </div>
              {item.author && item.date && (
                <p className="text-[10px] text-text-muted">
                  {item.author} · {item.date}
                  {item.publisher ? ` · ${item.publisher}` : ""}
                </p>
              )}
              <p className="text-xs text-text-secondary leading-relaxed line-clamp-4">
                {item.content}
              </p>
            </div>
          ))}
        </div>
      )}
      {reviewerSuggestions && (
        <div>
          <p className="text-[10px] font-semibold uppercase tracking-widest text-text-muted mb-1.5">
            Reviewer Analysis
          </p>
          <div className="rounded-lg border border-border-muted bg-surface p-3">
            <FormattedReviewText text={reviewerSuggestions} />
          </div>
        </div>
      )}
    </div>
  );
}

const CONFIDENCE_COLOR = (score: number) =>
  score >= 0.7 ? "bg-success-subtle text-success-text" :
  score >= 0.4 ? "bg-warning-subtle text-warning-text" :
  "bg-error-subtle text-error-text";

function ProcessingTranscript({ data }: { data: ProcessingData }) {
  return (
    <div className="space-y-3">
      {data.findings && data.findings.length > 0 && (
        <div className="space-y-2">
          <p className="text-[10px] font-semibold uppercase tracking-widest text-text-muted">
            Findings ({data.findings.length})
          </p>
          {data.findings.map((f: ProcessingFinding, i: number) => (
            <div key={f.id ?? i} className="rounded-lg border border-border-muted bg-surface-muted p-3 space-y-1.5">
              <div className="flex items-start justify-between gap-2">
                <p className="text-xs font-semibold text-text-primary leading-snug flex-1">{f.title}</p>
                {f.confidence != null && (
                  <span className={`shrink-0 rounded px-1.5 py-0.5 text-[10px] font-semibold ${CONFIDENCE_COLOR(f.confidence)}`}>
                    {Math.round(f.confidence * 100)}%
                  </span>
                )}
              </div>
              <p className="text-xs text-text-secondary leading-relaxed">{f.finding}</p>
              {f.evidence_summary && (
                <p className="text-[11px] text-text-muted leading-relaxed italic">{f.evidence_summary}</p>
              )}
              {f.why_it_matters && (
                <p className="text-[11px] text-text-muted leading-relaxed">
                  <span className="font-medium not-italic text-text-secondary">Why it matters: </span>
                  {f.why_it_matters}
                </p>
              )}
            </div>
          ))}
        </div>
      )}
      {data.gaps && data.gaps.length > 0 && (
        <div>
          <p className="text-[10px] font-semibold uppercase tracking-widest text-text-muted mb-1.5">
            Gaps ({data.gaps.length})
          </p>
          <ul className="space-y-1">
            {data.gaps.map((gap, i) => (
              <li key={i} className="flex gap-2 text-xs text-text-secondary">
                <span className="shrink-0 text-text-muted">·</span>
                <span>{gap}</span>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}

// ── Python repr → JSON normaliser ─────────────────────────────────────────────

function normalizePythonRepr(s: string): string {
  let result = "";
  let i = 0;
  while (i < s.length) {
    if (s[i] === "'") {
      let j = i + 1;
      while (j < s.length && s[j] !== "'") {
        if (s[j] === "\\") j++;
        j++;
      }
      const inner = s.slice(i + 1, j).replace(/"/g, '\\"');
      result += '"' + inner + '"';
      i = j + 1;
    } else if (s[i] === '"') {
      let j = i + 1;
      while (j < s.length && s[j] !== '"') {
        if (s[j] === "\\") j++;
        j++;
      }
      result += s.slice(i, j + 1);
      i = j + 1;
    } else {
      result += s[i];
      i++;
    }
  }
  return result
    .replace(/\bTrue\b/g, "true")
    .replace(/\bFalse\b/g, "false")
    .replace(/\bNone\b/g, "null");
}

function tryParseContent(content: string): unknown {
  try { return JSON.parse(content); } catch { /* not valid JSON */ }
  try { return JSON.parse(normalizePythonRepr(content)); } catch { /* not valid Python repr either */ }
  return null;
}

// ── Analysis transcript renderer ───────────────────────────────────────────────

function AnalysisTranscript({ data }: { data: Analysis }) {
  return (
    <div className="space-y-4">
      {data.title ? (
        <div>
          <p className="text-[10px] font-semibold uppercase tracking-widest text-text-muted mb-1">Title</p>
          <p className="text-xs font-medium text-text-primary">{data.title}</p>
        </div>
      ) : null}
      {data.summary ? (
        <div>
          <p className="text-[10px] font-semibold uppercase tracking-widest text-text-muted mb-1">Summary</p>
          <p className="text-xs text-text-secondary leading-relaxed">{data.summary}</p>
        </div>
      ) : null}
      {data.key_judgments && data.key_judgments.length > 0 && (
        <div>
          <p className="text-[10px] font-semibold uppercase tracking-widest text-text-muted mb-1.5">
            Key Judgments ({data.key_judgments.length})
          </p>
          <ul className="space-y-1.5">
            {data.key_judgments.map((j, i) => (
              <li key={i} className="flex gap-2 text-xs text-text-secondary leading-relaxed">
                <span className="shrink-0 font-medium text-text-muted">{i + 1}.</span>
                <span>{j}</span>
              </li>
            ))}
          </ul>
        </div>
      )}
      {data.recommended_actions && data.recommended_actions.length > 0 && (
        <div>
          <p className="text-[10px] font-semibold uppercase tracking-widest text-text-muted mb-1.5">
            Recommended Actions
          </p>
          <ul className="space-y-1">
            {data.recommended_actions.map((a, i) => (
              <li key={i} className="flex gap-2 text-xs text-text-secondary">
                <span className="shrink-0 text-text-muted">·</span>
                <span>{a}</span>
              </li>
            ))}
          </ul>
        </div>
      )}
      {data.information_gaps && data.information_gaps.length > 0 && (
        <div>
          <p className="text-[10px] font-semibold uppercase tracking-widest text-text-muted mb-1.5">
            Information Gaps
          </p>
          <ul className="space-y-1">
            {data.information_gaps.map((g, i) => (
              <li key={i} className="flex gap-2 text-xs text-text-secondary">
                <span className="shrink-0 text-text-muted">·</span>
                <span>{g}</span>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}

// ── Transcript dispatcher ──────────────────────────────────────────────────────

function TranscriptRenderer({ phase, content, reviewerSuggestions }: { phase: PhaseReviewItem["phase"]; content: string; reviewerSuggestions?: string | null }) {
  const parsed = tryParseContent(content);

  if (phase === "direction" && parsed && typeof parsed === "object" && ("pirs" in parsed || "pir_text" in parsed)) {
    return <PirTranscript data={parsed as PirData} />;
  }

  if (phase === "collection" && parsed && typeof parsed === "object" && "collected_data" in parsed) {
    return <CollectionTranscript data={parsed as CollectionDisplayData} reviewerSuggestions={reviewerSuggestions} />;
  }

  if (phase === "processing" && parsed && typeof parsed === "object" && "findings" in parsed) {
    return <ProcessingTranscript data={parsed as ProcessingData} />;
  }

  if (phase === "analysis" && parsed && typeof parsed === "object") {
    const draft = "analysis_draft" in parsed
      ? (parsed as { analysis_draft: Analysis }).analysis_draft
      : (parsed as unknown as Analysis);
    if (draft && typeof draft === "object" && ("summary" in draft || "key_judgments" in draft)) {
      return <AnalysisTranscript data={draft} />;
    }
  }

  // Unrecognised shape — render as formatted text
  return (
    <div className="text-xs text-text-secondary leading-relaxed">
      <FormattedReviewText text={content} />
    </div>
  );
}

// ── Helpers ───────────────────────────────────────────────────────────────────

function phaseLabel(phase: PhaseReviewItem["phase"]): string {
  switch (phase) {
    case "direction": return "Direction";
    case "collection": return "Collection";
    case "processing": return "Processing";
    case "analysis": return "Analysis";
  }
}

// ── Modal ──────────────────────────────────────────────────────────────────────

export default function ReviewActivityModal({
  isOpen,
  onClose,
  activity,
  focusAttempt,
}: ReviewActivityModalProps) {
  if (!isOpen) return null;

  const phases = [...new Set(activity.map((a) => a.phase))];
  const phasesSummary = phases.map(phaseLabel).join(", ");

  return (
    <div
      data-testid="review-activity-modal-backdrop"
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 p-4"
      onClick={onClose}
    >
      <div
        role="dialog"
        aria-modal="true"
        className="flex h-[85vh] w-full max-w-2xl flex-col overflow-hidden rounded-xl border border-border bg-surface shadow-2xl"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="flex shrink-0 items-center justify-between border-b border-border px-6 py-4">
          <div>
            <h2 className="text-base font-semibold text-text-primary">Review Activity</h2>
            <p className="mt-0.5 text-xs text-text-muted">
              {activity.length} attempt{activity.length !== 1 ? "s" : ""} — {phasesSummary}
            </p>
          </div>
          <button
            aria-label="Close review activity"
            onClick={onClose}
            className="rounded p-1.5 text-text-muted hover:bg-surface-elevated hover:text-text-primary transition-colors"
          >
            ✕
          </button>
        </div>

        {/* Body */}
        <div className="flex-1 overflow-y-auto px-6 py-5 space-y-3">
          {activity.length === 0 ? (
            <p className="text-sm text-text-muted italic">No review feedback recorded yet.</p>
          ) : (
            <div className="rounded-lg border border-border overflow-hidden divide-y divide-border">
              {activity.map((item) => {
                const approved = item.reviewer_approved;
                const defaultOpen = focusAttempt === undefined || focusAttempt === item.attempt;
                return (
                  <details key={`${item.phase}-${item.attempt}`} open={defaultOpen} className="group">
                    <summary className="flex cursor-pointer select-none items-center justify-between px-5 py-3 bg-surface-muted hover:bg-surface-elevated transition-colors list-none">
                      <div className="flex items-center gap-3">
                        <span className="text-[10px] font-bold uppercase tracking-widest text-text-muted">
                          Attempt {item.attempt}
                        </span>
                        <span className="text-[10px] text-text-muted">·</span>
                        <span className="text-[10px] text-text-muted">{phaseLabel(item.phase)}</span>
                        <span
                          className={`rounded px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wide ${
                            approved
                              ? "bg-success-subtle text-success-text"
                              : "bg-error-subtle text-error-text"
                          }`}
                        >
                          {approved ? "Approved" : "Rejected"}
                        </span>
                      </div>
                      <svg
                        className="h-4 w-4 text-text-muted transition-transform group-open:rotate-180"
                        viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.5"
                      >
                        <path d="M4 6l4 4 4-4" strokeLinecap="round" strokeLinejoin="round" />
                      </svg>
                    </summary>

                    <div className="px-5 py-4 space-y-4 bg-surface">
                      {/* Sources — collection phase only */}
                      {item.sources_used.length > 0 && (
                        <div>
                          <p className="text-[10px] font-semibold uppercase tracking-widest text-text-muted mb-1.5">
                            Sources Used
                          </p>
                          <div className="flex flex-wrap gap-1.5">
                            {item.sources_used.map((src) => (
                              <span key={src} className="rounded px-2 py-0.5 text-xs font-medium bg-surface-muted text-text-secondary border border-border-muted">
                                {src}
                              </span>
                            ))}
                          </div>
                        </div>
                      )}

                      {/* AI Feedback */}
                      <div>
                        <p className="text-[10px] font-semibold uppercase tracking-widest text-text-muted mb-1.5">
                          AI Feedback
                        </p>
                        {approved && !item.reviewer_suggestions ? (
                          <span className="inline-flex items-center gap-1.5 text-xs font-medium text-success-text">
                            <span className="text-base leading-none">✓</span> Approved — no further feedback
                          </span>
                        ) : item.reviewer_suggestions ? (
                          <div className={`rounded-lg border p-3 ${approved ? "border-success-subtle bg-success-subtle/30" : "border-error-subtle bg-error-subtle/30"}`}>
                            <FormattedReviewText text={item.reviewer_suggestions} />
                          </div>
                        ) : (
                          <span className="text-xs text-error-text font-medium">Rejected — no feedback provided</span>
                        )}
                      </div>

                      {/* Full transcript — parsed per phase */}
                      {item.generated_content && (
                        <div>
                          <p className="text-[10px] font-semibold uppercase tracking-widest text-text-muted mb-2">
                            Full Transcript
                          </p>
                          <div className="rounded-lg border border-border-muted bg-surface-muted p-3 overflow-y-auto max-h-72">
                            <TranscriptRenderer phase={item.phase} content={item.generated_content} reviewerSuggestions={item.reviewer_suggestions} />
                          </div>
                        </div>
                      )}
                    </div>
                  </details>
                );
              })}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
