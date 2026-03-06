/* eslint-disable react-refresh/only-export-components */
import { createContext, useState } from "react";
import type { PirData } from "../../types/conversation";
import React from "react";

export type Phase = "direction" | "collection" | "processing" | "analysis";

export interface WorkspaceContextValue {
  highlightedRef: string | null;
  setHighlightedRef: (ref: string | null) => void;
  pirData: PirData | null;
  setPirData: (pirData: PirData | null) => void;
  activePhase: Phase;
  setActivePhase: (phase: Phase) => void;
}

export { useWorkspace } from "../../hooks/useWorkspace";

export const WorkspaceContext = createContext<WorkspaceContextValue | null>(
  null,
);

export function WorkspaceProvider({ children }: { children: React.ReactNode }) {
  const [highlightedRef, setHighlightedRef] = useState<string | null>(null);
  const [pirData, setPirData] = useState<PirData | null>(null);
  const [activePhase, setActivePhase] = useState<Phase>("direction");
  const value = {
    highlightedRef,
    setHighlightedRef,
    pirData,
    setPirData,
    activePhase,
    setActivePhase,
  };

  return (
    <WorkspaceContext.Provider value={value}>
      {children}
    </WorkspaceContext.Provider>
  );
}
