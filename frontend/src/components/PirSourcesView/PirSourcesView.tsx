import { useWorkspace } from "../../hooks/useWorkspace";
import SourceList from "../SourceList/SourceList";

/**
 * View for displaying sources related to PIR (Problem Identification and Resolution).
 * @returns JSX.Element
 */
export default function PirSourcesView() {
  const { pirData, highlightedRef, setHighlightedRef } = useWorkspace();

  if (!pirData || pirData.sources.length === 0) {
    return (
      <div className="rounded-lg border border-dashed border-border p-4 text-sm text-text-secondary">
        No sources available.
      </div>
    );
  }

  return (
    <div className="space-y-2">
      <p className="text-xs font-medium uppercase tracking-wider text-text-muted">
        Sources ({pirData.sources.length})
      </p>
      <SourceList
        sources={pirData.sources}
        highlightedRef={highlightedRef}
        onSourceHover={setHighlightedRef}
      />
    </div>
  );
}
