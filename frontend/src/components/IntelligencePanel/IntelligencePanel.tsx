import { useWorkspace } from "../../contexts/WorkspaceContext/WorkspaceContext";
import PirSourcesView from "../PirSourcesView/PirSourcesView";

/**
 * Component for displaying the intelligence panel with phase-specific views.
 * @returns 
 */
export default function IntelligencePanel() {
  const { activePhase } = useWorkspace();

  function renderPhaseView(activePhase: string) {
    switch (activePhase) {
      case "direction":
        return <PirSourcesView />;
      case "collection":
        return <div>Collection Phase View</div>;
      case "processing":
        return <div>Processing Phase View</div>;
      case "analysis":
        return <div>Analysis Phase View</div>;
    }
  }
  return (
    <div className="intelligence-panel">
      <h2>{activePhase.toUpperCase()}</h2>
      {renderPhaseView(activePhase)}
    </div>
  );
}
