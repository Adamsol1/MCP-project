import { useWorkspace } from "../../hooks/useWorkspace/useWorkspace";
import SourceList from "../SourceList/SourceList";
import { useT } from "../../i18n/useT";

/**
 * View for displaying sources related to PIR (Problem Identification and Resolution).
 * @returns JSX.Element
 */
export default function PirSourcesView() {
  const { pirData, highlightedRefs, setHighlightedRefs } = useWorkspace();
  const t = useT();
  const handleSourceHover = (value: string[] | string | null) => {
    setHighlightedRefs(Array.isArray(value) ? value : value ? [value] : []);
  };

  if (!pirData || pirData.sources.length === 0) {
    return (
      <div className="rounded-lg border border-dashed border-border p-4 text-sm text-text-secondary">
        {t.noSourcesAvailable}
      </div>
    );
  }

  return (
    <div className="space-y-2">
      <p className="text-xs font-medium uppercase tracking-wider text-text-muted">
        {t.pirSources(pirData.sources.length)}
      </p>
      <SourceList
        sources={pirData.sources}
        highlightedRefs={highlightedRefs}
        onSourceHover={handleSourceHover}
      />
    </div>
  );
}
