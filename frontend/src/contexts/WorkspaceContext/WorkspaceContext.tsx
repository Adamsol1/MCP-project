/* eslint-disable react-refresh/only-export-components */
import { createContext, useCallback, useState } from "react";
import type { CollectedItem, CollectionDisplayData, CollectionSourceSummary, PhaseReviewItem, PirData } from "../../types/conversation";
import React from "react";

const TOOL_DISPLAY_NAMES: Record<string, string> = {
  list_knowledge_base: "Knowledge Bank",
  read_knowledge_base: "Knowledge Bank",
  query_otx: "AlienVault OTX",
  search_local_data: "Uploaded Documents",
  list_uploads: "Uploaded Documents",
  read_upload: "Uploaded Documents",
  google_search: "Web Search",
  google_news_search: "Web News",
  fetch_page: "Web Fetch",
};

const WEB_SOURCES = new Set(["fetch_page", "google_news_search", "google_search"]);

function deduplicateItems(items: CollectedItem[]): CollectedItem[] {
  // Pass 1: deduplicate by (source, resource_id) — keep richer content
  const byUrl = new Map<string, CollectedItem>();
  for (const item of items) {
    const key = `${item.source}|${item.resource_id ?? ""}`;
    const existing = byUrl.get(key);
    if (!existing || (item.content?.length ?? 0) > (existing.content?.length ?? 0)) {
      byUrl.set(key, item);
    }
  }

  // Pass 2: deduplicate web items by (source, title) — same article at different URLs
  const seenTitles = new Map<string, number>();
  const result: CollectedItem[] = [];
  for (const item of byUrl.values()) {
    if (WEB_SOURCES.has(item.source) && item.title) {
      const titleKey = `${item.source}|${item.title.trim().toLowerCase().slice(0, 120)}`;
      const idx = seenTitles.get(titleKey);
      if (idx !== undefined) {
        if ((item.content?.length ?? 0) > (result[idx].content?.length ?? 0)) {
          result[idx] = item;
        }
      } else {
        seenTitles.set(titleKey, result.length);
        result.push(item);
      }
    } else {
      result.push(item);
    }
  }
  return result;
}

function buildSourceSummary(items: CollectedItem[]): CollectionSourceSummary[] {
  const statsMap = new Map<string, CollectionSourceSummary>();
  for (const item of items) {
    const displayName = TOOL_DISPLAY_NAMES[item.source] ?? item.source;
    if (!statsMap.has(displayName)) {
      statsMap.set(displayName, { display_name: displayName, count: 0, resource_ids: [], has_content: false });
    }
    const s = statsMap.get(displayName)!;
    s.count++;
    if (item.resource_id && !s.resource_ids.includes(item.resource_id)) {
      s.resource_ids.push(item.resource_id);
    }
    if (item.content?.trim()) s.has_content = true;
  }
  return Array.from(statsMap.values()).sort((a, b) => a.display_name.localeCompare(b.display_name));
}

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
      const combined = prev
        ? [...prev.collected_data, ...incoming.collected_data]
        : incoming.collected_data;
      const collected_data = deduplicateItems(combined);
      const source_summary = buildSourceSummary(collected_data);
      return { collected_data, source_summary };
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
