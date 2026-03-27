import type { CollectionDisplayData, ActivitySummaryItem } from "../../types/conversation";
import { useT } from "../../i18n/useT";

interface CollectionStatsViewProps {
  collectionData: CollectionDisplayData | null;
  onOpenModal: () => void;
}

export default function CollectionStatsView({
  collectionData,
  onOpenModal,
}: CollectionStatsViewProps) {
  const t = useT();

  if (!collectionData) {
    return (
      <p className="text-sm text-text-muted italic">{t.noCollectionData}</p>
    );
  }

  const total = collectionData.source_summary.reduce((sum, source) => sum + source.count, 0);
  const maxCount = Math.max(...collectionData.source_summary.map((s) => s.count), 1);
  const activity = collectionData.activity_summary;

  return (
    <div className="space-y-4">

      {/* Activity summary — what the collector and reviewer did */}
      {activity && activity.length > 0 && (
        <div className="space-y-2">
          <p className="text-[10px] font-semibold uppercase tracking-widest text-text-muted">
            Collection Activity
          </p>
          {activity.map((item: ActivitySummaryItem) => (
            <div key={item.attempt} className="rounded-lg border border-border-muted bg-surface px-3 py-2 space-y-1">
              <p className="text-[10px] font-semibold uppercase tracking-wide text-text-muted">
                Attempt {item.attempt}
              </p>
              <p className="text-xs text-text-secondary">
                <span className="font-medium text-text-primary">Collector: </span>
                {item.collector_sources.join(", ")}
              </p>
              <p className="text-xs text-text-secondary">
                <span className="font-medium text-text-primary">Reviewer: </span>
                {item.reviewer_approved
                  ? "Approved ✓"
                  : item.reviewer_suggestions ?? "Rejected"}
              </p>
            </div>
          ))}
        </div>
      )}

      {/* Summary stats */}
      <div className="grid grid-cols-2 gap-2">
        <div className="rounded-lg bg-surface border border-border-muted px-3 py-2">
          <p className="text-[10px] font-semibold uppercase tracking-widest text-text-muted">{t.tableItems}</p>
          <p className="mt-0.5 text-xl font-bold tabular-nums text-text-primary">{total}</p>
        </div>
        <div className="rounded-lg bg-surface border border-border-muted px-3 py-2">
          <p className="text-[10px] font-semibold uppercase tracking-widest text-text-muted">{t.statsSources}</p>
          <p className="mt-0.5 text-xl font-bold tabular-nums text-text-primary">{collectionData.source_summary.length}</p>
        </div>
      </div>

      {/* Source bars */}
      <div className="space-y-1">
        <p className="text-[10px] font-semibold uppercase tracking-widest text-text-muted mb-1">{t.bySource}</p>
        {collectionData.source_summary.map((source) => (
          <div key={source.display_name} className="flex items-center justify-between">
            <span className="text-xs text-text-secondary truncate max-w-[80%]">
              {source.display_name}
            </span>
            <span className="text-xs tabular-nums font-medium text-text-muted">
              {source.has_content ? source.count : <span className="text-[10px] uppercase tracking-wide">{t.empty}</span>}
            </span>
          </div>
        ))}
      </div>

      {/* CTA button */}
      <button
        onClick={onOpenModal}
        className="w-full rounded-lg border border-border-muted bg-surface px-3 py-2 text-xs font-medium text-text-secondary transition-colors hover:border-primary hover:bg-primary-subtle hover:text-primary"
      >
        {t.viewRawData}
      </button>
    </div>
  );
}
