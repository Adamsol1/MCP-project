import { useEffect, useMemo, useRef, useState } from "react";
import { useConversation } from "../../hooks/useConversation/useConversation";
import { useSettings } from "../../contexts/SettingsContext/SettingsContext";
import { useWorkspace } from "../../contexts/WorkspaceContext/WorkspaceContext";
import type { AnalysisResponse, CouncilNote } from "../../types/analysis";
import AnalysisView from "./AnalysisView";
import CouncilView from "./CouncilView";

const PERSPECTIVE_ORDER = ["us", "norway", "china", "eu", "russia", "neutral"];

/**
 *  Normalizes an array of perspective keys by converting them to lowercase, filtering out any invalid keys that are not included in the predefined PERSPECTIVE_ORDER, and ensuring that at least a default "neutral" perspective is included if the input is empty or contains no valid keys. The function returns a new array of perspective keys that are valid and ordered according to the PERSPECTIVE_ORDER.
 * @param perspectives An array of perspective keys to normalize, which may include values such as "us", "norway", "china", "eu", "russia", "neutral", or other custom keys. The function processes this array to produce a normalized and validated list of perspective keys for use in the analysis report.
 * @returns A normalized array of perspective keys that are valid and ordered according to the predefined PERSPECTIVE_ORDER. If the input array is empty or contains no valid keys, the function returns an array containing only the default "neutral" perspective.
 */
function normalizePerspectives(perspectives: string[] | undefined) {
  const normalized = perspectives
    ?.map((value) => value.toLowerCase())
    .filter((value) => PERSPECTIVE_ORDER.includes(value));

  if (!normalized || normalized.length === 0) {
    return ["neutral"];
  }

  return PERSPECTIVE_ORDER.filter((value) => normalized.includes(value));
}
/**
 * AnalysisWorkspace component is responsible for rendering the analysis interface,
 * which includes both the main analysis view and the council view. It manages the state of
 * which view is currently active (analysis or council) and retrieves the necessary data from the active conversation to display the analysis results. The component also handles scrolling behavior when switching to the council view and ensures that the appropriate data is passed down to the child components for rendering.
 * @returns A React component that displays the analysis workspace, allowing users to view the analysis results and council notes based on the active conversation's data. The component manages the state of the current view and ensures a smooth user experience when navigating between the analysis and council views.
 */
export default function AnalysisWorkspace() {
  const { activeConversation } = useConversation();
  const { settings } = useSettings();
  const { reviewActivity } = useWorkspace();
  const containerRef = useRef<HTMLDivElement>(null);

  const data = useMemo<AnalysisResponse | null>(() => {
    if (!activeConversation) return null;
    for (let i = activeConversation.messages.length - 1; i >= 0; i--) {
      const msg = activeConversation.messages[i];
      if (msg.type === "analysis" && msg.data) {
        return msg.data as AnalysisResponse;
      }
    }
    return null;
  }, [activeConversation]);

  const councilNote = useMemo<CouncilNote | null>(() => {
    if (!activeConversation) return null;
    for (let i = activeConversation.messages.length - 1; i >= 0; i--) {
      const msg = activeConversation.messages[i];
      if (msg.type === "council" && msg.data) {
        return msg.data as CouncilNote;
      }
    }
    return null;
  }, [activeConversation]);

  const [showCouncil, setShowCouncil] = useState(() => councilNote !== null);

  // When loading a conversation that already has a council note, start on council view.
  // When a new council note arrives after running council, advance automatically.
  useEffect(() => {
    if (councilNote !== null) {
      setShowCouncil(true);
    }
  }, [councilNote]);

  useEffect(() => {
    if (showCouncil) {
      containerRef.current?.scrollIntoView({ behavior: "smooth", block: "start" });
    }
  }, [showCouncil]);

  // Reset to analysis view when switching conversations
  useEffect(() => {
    setShowCouncil(councilNote !== null);
  }, [activeConversation?.sessionId]);

  const defaultPerspectives = useMemo(
    () => normalizePerspectives(activeConversation?.perspectives),
    [activeConversation?.perspectives],
  );

  if (!activeConversation?.sessionId) {
    return (
      <p className="text-sm text-text-secondary">
        Create or select a conversation to load the analysis.
      </p>
    );
  }

  if (!data) {
    return (
      <p className="text-sm text-text-secondary">
        No analysis available for this session.
      </p>
    );
  }

  return (
    <div ref={containerRef} className="scroll-mt-24">
      {showCouncil ? (
        <CouncilView
          processingFindings={data.processing_result.findings}
          councilNote={councilNote}
          defaultPerspectives={defaultPerspectives}
          onBack={() => setShowCouncil(false)}
        />
      ) : (
        <AnalysisView
          data={data}
          conversationTitle={activeConversation?.title}
          onStartCouncil={() => setShowCouncil(true)}
          timeframe={settings.inputParameters.timeframe}
          reviewActivity={reviewActivity}
        />
      )}
    </div>
  );
}
