import { useState } from "react";
import { useWorkspace } from "../../contexts/WorkspaceContext/WorkspaceContext";
import PirSourcesView from "../PirSourcesView/PirSourcesView";
import CollectionStatsView from "../CollectionStatsView/CollectionStatsView";
import CollectionStatsModal from "../CollectionStatsModal/CollectionStatsModal";

export default function IntelligencePanel() {
  const { activePhase, collectionData } = useWorkspace();
  const [isModalOpen, setIsModalOpen] = useState(false);

  function renderPhaseView(activePhase: string) {
    switch (activePhase) {
      case "direction":
        return <PirSourcesView />;
      case "collection":
        return (
          <CollectionStatsView
            collectionData={collectionData}
            onOpenModal={() => setIsModalOpen(true)}
          />
        );
      case "processing":
        return (
          <p className="text-sm text-text-secondary">
            Processing artifacts will appear here.
          </p>
        );
      case "analysis":
        return (
          <p className="text-sm text-text-secondary">
            Analysis outputs will appear here.
          </p>
        );
      default:
        return null;
    }
  }

  const phaseLabel = activePhase.toUpperCase();

  return (
    <div className="h-full flex flex-col bg-surface">
      <header className="border-b border-border-muted px-4 py-3">
        <p className="text-[11px] font-medium uppercase tracking-[0.12em] text-text-muted">
          Intelligence Workspace
        </p>
        <div className="mt-2 flex items-center justify-between">
          <h2 className="text-sm font-semibold text-text-primary">{phaseLabel}</h2>
          <span className="inline-flex items-center rounded-full border border-border bg-surface-muted px-2 py-0.5 text-[11px] font-medium uppercase tracking-wide text-text-secondary">
            {activePhase}
          </span>
        </div>
      </header>

      <div className="flex-1 overflow-y-auto px-3 py-3 scrollbar-chatgpt">
        <section className="rounded-xl border border-border-muted bg-surface-muted/70 p-3 shadow-sm">
          {renderPhaseView(activePhase)}
        </section>
      </div>

      <CollectionStatsModal
        isOpen={isModalOpen}
        onClose={() => setIsModalOpen(false)}
        collectionData={collectionData}
      />
    </div>
  );
}
