import type { PhaseReviewItem } from "../../types/conversation";

interface CollectionActivityModalProps {
  isOpen: boolean;
  onClose: () => void;
  activity: PhaseReviewItem[];
  /** If set, this attempt number will be expanded by default. */
  focusAttempt?: number;
}

// ── Text formatter ─────────────────────────────────────────────────────────────

/**
 * Renders reviewer suggestion text with basic markdown-like formatting:
 * - **text** → bold
 * - Numbered list items (1. 2. 3.) get bullet treatment
 * - Inline emphasis preserved
 */
function FormattedReviewText({ text }: { text: string }) {
  const lines = text.split("\n");
  const elements: React.ReactNode[] = [];

  lines.forEach((line, i) => {
    const trimmed = line.trim();
    if (!trimmed) {
      elements.push(<div key={i} className="h-2" />);
      return;
    }

    // Numbered list item: "1. ..." or "1) ..."
    const listMatch = trimmed.match(/^(\d+)[.)]\s+(.+)$/);
    if (listMatch) {
      elements.push(
        <div key={i} className="flex gap-2 mb-1">
          <span className="shrink-0 text-text-muted font-medium">{listMatch[1]}.</span>
          <span className="text-xs text-text-secondary leading-relaxed">
            <InlineFormatted text={listMatch[2]} />
          </span>
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

/** Handles **bold** and *italic* inline spans. */
function InlineFormatted({ text }: { text: string }) {
  // Split on **...**  or  *...*
  const parts = text.split(/(\*\*[^*]+\*\*|\*[^*]+\*)/g);
  return (
    <>
      {parts.map((part, i) => {
        if (part.startsWith("**") && part.endsWith("**")) {
          return <strong key={i} className="font-semibold text-text-primary">{part.slice(2, -2)}</strong>;
        }
        if (part.startsWith("*") && part.endsWith("*")) {
          return <em key={i}>{part.slice(1, -1)}</em>;
        }
        return <span key={i}>{part}</span>;
      })}
    </>
  );
}

// ── Modal ──────────────────────────────────────────────────────────────────────

export default function CollectionActivityModal({
  isOpen,
  onClose,
  activity,
  focusAttempt,
}: CollectionActivityModalProps) {
  if (!isOpen) return null;

  return (
    <div
      data-testid="activity-modal-backdrop"
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
              {activity.length} attempt{activity.length !== 1 ? "s" : ""}
            </p>
          </div>
          <button
            aria-label="close"
            onClick={onClose}
            className="rounded p-1.5 text-text-muted hover:bg-surface-elevated hover:text-text-primary transition-colors"
          >
            ✕
          </button>
        </div>

        {/* Body */}
        <div className="flex-1 overflow-y-auto px-6 py-5 space-y-3">
          {activity.length === 0 ? (
            <p className="text-sm text-text-muted italic">No activity recorded.</p>
          ) : (
            <div className="rounded-lg border border-border overflow-hidden divide-y divide-border">
              {activity.map((item) => {
                const approved = item.reviewer_approved;
                const isOpen = focusAttempt === undefined || focusAttempt === item.attempt;
                return (
                  <details key={item.attempt} open={isOpen} className="group">
                    <summary className="flex cursor-pointer select-none items-center justify-between px-5 py-3 bg-surface-muted hover:bg-surface-elevated transition-colors list-none">
                      <div className="flex items-center gap-3">
                        <span className="text-[10px] font-bold uppercase tracking-widest text-text-muted">
                          Attempt {item.attempt}
                        </span>
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
                        viewBox="0 0 16 16"
                        fill="none"
                        stroke="currentColor"
                        strokeWidth="1.5"
                      >
                        <path d="M4 6l4 4 4-4" strokeLinecap="round" strokeLinejoin="round" />
                      </svg>
                    </summary>

                    <div className="px-5 py-4 space-y-4 bg-surface">
                      {/* Collector sources */}
                      <div>
                        <p className="text-[10px] font-semibold uppercase tracking-widest text-text-muted mb-1.5">
                          Collector
                        </p>
                        <div className="flex flex-wrap gap-1.5">
                          {item.sources_used.length > 0
                            ? item.sources_used.map((src) => (
                                <span
                                  key={src}
                                  className="rounded px-2 py-0.5 text-xs font-medium bg-surface-muted text-text-secondary border border-border-muted"
                                >
                                  {src}
                                </span>
                              ))
                            : <span className="text-xs text-text-muted italic">No sources recorded</span>
                          }
                        </div>
                      </div>

                      {/* Reviewer feedback */}
                      <div>
                        <p className="text-[10px] font-semibold uppercase tracking-widest text-text-muted mb-1.5">
                          Reviewer
                        </p>
                        {approved && !item.reviewer_suggestions ? (
                          <span className="inline-flex items-center gap-1.5 text-xs font-medium text-success-text">
                            <span className="text-base leading-none">✓</span> Approved with no comments
                          </span>
                        ) : item.reviewer_suggestions ? (
                          <div className={`rounded-lg border p-3 ${approved ? "border-success-subtle bg-success-subtle/30" : "border-error-subtle bg-error-subtle/30"}`}>
                            <FormattedReviewText text={item.reviewer_suggestions} />
                          </div>
                        ) : (
                          <span className="text-xs text-error-text font-medium">Rejected (no suggestions provided)</span>
                        )}
                      </div>
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
