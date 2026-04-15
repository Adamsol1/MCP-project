/* eslint-disable react-refresh/only-export-components */
import { createContext, useState } from "react";
import type { CollectionDisplayData, PhaseReviewItem, PirData } from "../../types/conversation";
import React from "react";

export interface WorkspaceContextValue {
  highlightedRef: string | null;
  setHighlightedRef: (ref: string | null) => void;
  highlightedRefs: string[];
  setHighlightedRefs: (refs: string[]) => void;
  pirData: PirData | null;
  setPirData: (pirData: PirData | null) => void;
  collectionData: CollectionDisplayData | null;
  setCollectionData: (data: CollectionDisplayData | null) => void;
  reviewActivity: PhaseReviewItem[];
  setReviewActivity: (items: PhaseReviewItem[]) => void;
}

export { useWorkspace } from "../../hooks/useWorkspace/useWorkspace";

export const WorkspaceContext = createContext<WorkspaceContextValue | null>(
  null,
);

export function WorkspaceProvider({ children }: { children: React.ReactNode }) {
  const [highlightedRefs, setHighlightedRefs] = useState<string[]>([]);
  const [pirData, setPirData] = useState<PirData | null>(null);
  const [collectionData, setCollectionData] =
    useState<CollectionDisplayData | null>(null);
  const [reviewActivity, setReviewActivity] = useState<PhaseReviewItem[]>([]);
  const highlightedRef = highlightedRefs[0] ?? null;
  const setHighlightedRef = (ref: string | null) => {
    setHighlightedRefs(ref ? [ref] : []);
  };
  const value = {
    highlightedRef,
    setHighlightedRef,
    highlightedRefs,
    setHighlightedRefs,
    pirData,
    setPirData,
    collectionData,
    setCollectionData,
    reviewActivity,
    setReviewActivity,
  };

  return (
    <WorkspaceContext.Provider value={value}>
      {children}
    </WorkspaceContext.Provider>
  );
}
