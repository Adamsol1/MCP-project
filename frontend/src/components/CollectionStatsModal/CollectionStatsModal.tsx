import type { CollectionDisplayData, CollectedItem } from "../../types/conversation";

const TOOL_DISPLAY_NAMES: Record<string, string> = {
  list_knowledge_base: "Internal Knowledge Bank",
  read_knowledge_base: "Internal Knowledge Bank",
  query_otx: "AlienVault OTX",
  search_local_data: "Uploaded Documents",
  list_uploads: "Uploaded Documents",
  read_upload: "Uploaded Documents",
  web_search: "Web Search",
  fetch_page: "Web Search",
};

interface CollectionStatsModalProps {
  isOpen: boolean;
  onClose: () => void;
  collectionData: CollectionDisplayData | null;
}

function groupBySource(items: CollectedItem[]): Record<string, CollectedItem[]> {
  const groups: Record<string, CollectedItem[]> = {};
  for (const item of items) {
    const name = TOOL_DISPLAY_NAMES[item.source] ?? item.source;
    if (!groups[name]) groups[name] = [];
    groups[name].push(item);
  }
  return groups;
}

export default function CollectionStatsModal({
  isOpen,
  onClose,
  collectionData,
}: CollectionStatsModalProps) {
  if (!isOpen) return null;

  if (!collectionData)
    return (
      <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60">
        <div
          data-testid="collection-stats-modal"
          className="rounded-lg border border-border bg-surface p-8 shadow-2xl"
        >
          <p className="text-sm text-text-secondary">No data available</p>
        </div>
      </div>
    );

  const groups = groupBySource(collectionData.collected_data);
  const totalItems = collectionData.source_summary.reduce((sum, s) => sum + s.count, 0);
  const maxCount = Math.max(...collectionData.source_summary.map((s) => s.count), 1);

  return (
    <div
      data-testid="modal-backdrop"
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/60"
      onClick={onClose}
    >
      <div
        data-testid="collection-stats-modal"
        role="dialog"
        aria-modal="true"
        className="flex h-[85vh] w-225 max-w-[95vw] flex-col overflow-hidden rounded-lg border border-border bg-surface shadow-2xl"
        onClick={(e) => e.stopPropagation()}
      >
        {/* ── Header ── */}
        <div className="flex items-center justify-between border-b border-border px-16 py-4">
          <div>
            <h2 className="text-base font-semibold text-text-primary">Collection Results</h2>
            <p className="mt-0.5 text-xs text-text-muted">
              {totalItems} items across {collectionData.source_summary.length} sources
            </p>
          </div>
          <button
            aria-label="close"
            onClick={onClose}
            className="text-text-muted hover:text-text-primary transition-colors"
          >
            ✕
          </button>
        </div>

        {/* ── Scrollable body ── */}
        <div className="flex-1 overflow-y-auto px-16 py-5 space-y-6">

          {/* Stats section */}
          <section>
            <p className="mb-3 text-[11px] font-semibold uppercase tracking-widest text-text-muted">
              Source Distribution
            </p>
            <div className="space-y-2">
              {collectionData.source_summary.map((source) => (
                <div key={source.display_name} className="flex items-center gap-3">
                  <span className="w-44 shrink-0 text-xs text-text-secondary truncate">
                    {source.display_name}
                  </span>
                  <div className="flex-1 h-2 rounded-full bg-surface-elevated overflow-hidden">
                    <div
                      className={`h-full rounded-full transition-all ${
                        source.has_content ? "bg-primary" : "bg-border"
                      }`}
                      style={{ width: `${(source.count / maxCount) * 100}%` }}
                    />
                  </div>
                  <span className="w-8 text-right text-xs font-medium tabular-nums text-text-secondary">
                    {source.count}
                  </span>
                  {!source.has_content && (
                    <span className="text-[10px] uppercase tracking-wide text-text-muted">
                      Empty
                    </span>
                  )}
                </div>
              ))}
            </div>
          </section>

          {/* Raw data section */}
          <section>
            <p className="mb-3 text-[11px] font-semibold uppercase tracking-widest text-text-muted">
              Raw Collected Data
            </p>
            <div className="rounded-lg border border-border overflow-hidden divide-y divide-border">
              {Object.entries(groups).map(([groupName, items]) => (
                <details
                  key={groupName}
                  role="group"
                  open
                  className="group"
                >
                  <summary className="flex cursor-pointer select-none items-center justify-between px-4 py-2.5 bg-surface-muted border-b border-border-muted text-sm font-medium text-text-secondary hover:text-text-primary list-none">
                    {groupName}
                    <span className="text-xs text-text-muted">{items.length} items</span>
                  </summary>
                  <div className="divide-y divide-border-muted">
                    {items.map((item, i) => (
                      <div key={i} className="px-4 py-3">
                        {item.resource_id && (
                          <span className="mb-1.5 inline-block rounded bg-primary-subtle px-1.5 py-0.5 text-[11px] font-medium text-info-text">
                            {item.resource_id}
                          </span>
                        )}
                        <pre className="mt-1 max-h-36 overflow-auto whitespace-pre-wrap break-all rounded border border-border-muted bg-surface-muted p-3 text-xs text-text-secondary">
                          {item.content || "(no content)"}
                        </pre>
                      </div>
                    ))}
                  </div>
                </details>
              ))}
            </div>
          </section>
        </div>
      </div>
    </div>
  );
}
