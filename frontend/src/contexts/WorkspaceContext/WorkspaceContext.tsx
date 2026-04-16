/* eslint-disable react-refresh/only-export-components */
import { createContext, useCallback, useState } from "react";
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
  mergeCollectionData: (data: CollectionDisplayData) => void;
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
  const mergeCollectionData = useCallback((incoming: CollectionDisplayData) => {
    setCollectionData((prev) => {
      if (!prev) return incoming;
      const mergedItems = [...prev.collected_data, ...incoming.collected_data];
      const summaryMap = new Map(prev.source_summary.map((s) => [s.display_name, { ...s }]));
      for (const s of incoming.source_summary) {
        const existing = summaryMap.get(s.display_name);
        if (existing) {
          existing.count += s.count;
          existing.has_content = existing.has_content || s.has_content;
          existing.resource_ids = [...new Set([...existing.resource_ids, ...s.resource_ids])];
        } else {
          summaryMap.set(s.display_name, { ...s });
        }
      }
      return {
        collected_data: mergedItems,
        source_summary: Array.from(summaryMap.values()),
      };
    });
  }, []);
  const value = {
    highlightedRef,
    setHighlightedRef,
    highlightedRefs,
    setHighlightedRefs,
    pirData,
    setPirData,
    collectionData,
    setCollectionData,
    mergeCollectionData,
    reviewActivity,
    setReviewActivity,
  };

  return (
    <WorkspaceContext.Provider value={value}>
      {children}
    </WorkspaceContext.Provider>
  );
}
