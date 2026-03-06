import { useWorkspace } from "../../hooks/useWorkspace";
import SourceList from "../SourceList/SourceList";

/**
 * View for displaying sources related to PIR (Problem Identification and Resolution).
 * @returns JSX.Element
 */
export default function PirSourcesView() {
  const { pirData, highlightedRef, setHighlightedRef } = useWorkspace();

  if (!pirData || pirData.sources.length === 0) {
    return <div>No sources available.</div>;
  }

  return (
    <SourceList
      sources={pirData.sources}
      highlightedRef={highlightedRef}
      onSourceHover={setHighlightedRef}
    />
  );
}
