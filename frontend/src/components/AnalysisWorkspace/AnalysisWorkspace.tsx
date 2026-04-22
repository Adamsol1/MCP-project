import { useEffect, useMemo, useRef, useState } from "react";
import { useConversation } from "../../hooks/useConversation/useConversation";
import { useSettings } from "../../contexts/SettingsContext/SettingsContext";
import { useWorkspace } from "../../contexts/WorkspaceContext/WorkspaceContext";
import type { AnalysisResponse, CouncilNote } from "../../types/analysis";
import AnalysisView from "./AnalysisView";
import CouncilView from "./CouncilView";

const PERSPECTIVE_ORDER = ["us", "norway", "china", "eu", "russia", "neutral"];

function normalizePerspectives(perspectives: string[] | undefined) {
  const normalized = perspectives
    ?.map((value) => value.toLowerCase())
    .filter((value) => PERSPECTIVE_ORDER.includes(value));

  if (!normalized || normalized.length === 0) {
    return ["neutral"];
  }

  return PERSPECTIVE_ORDER.filter((value) => normalized.includes(value));
}

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
