/* eslint-disable react-refresh/only-export-components */
import { createContext, useCallback, useState } from "react";
import type { CollectedItem, CollectionDisplayData, CollectionSourceSummary, PhaseReviewItem, PirData } from "../../types/conversation";
import React from "react";

/** Maps internal MCP tool names to user-facing source display names. */
const TOOL_DISPLAY_NAMES: Record<string, string> = {
  knowledge_base: "Knowledge Bank",
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


/** Sources that require title-based deduplication in addition to URL-based deduplication. */
const WEB_SOURCES = new Set(["fetch_page", "google_news_search", "google_search"]);

/**
 * Deduplicates collected items based on their source and resource ID.
 * @param items List of collected items to deduplicate.
 * @returns Deduplicated list of collected items.
 */

function deduplicateItems(items: CollectedItem[]): CollectedItem[] {
  // Pass 1: deduplicate by (canonical-source, resource_id)
  const byUrl = new Map<string, CollectedItem>();
  for (const item of items) {
    const canonical = TOOL_DISPLAY_NAMES[item.source] ?? item.source;
    const key = `${canonical}|${item.resource_id ?? ""}`;
    const existing = byUrl.get(key);
    if (!existing || (item.content?.length ?? 0) > (existing.content?.length ?? 0)) {
      byUrl.set(key, item);
    }
  }

  // Pass 2: deduplicate web items by (source, title), keeping the one with the longest content
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

/**
 *  Builds a summary of collection sources from the list of collected items.
 * @param items List of collected items to summarize.
 * @returns List of collection source summaries, sorted by display name.
 */
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
/**
 * Defines the shape of the workspace context value, including state and updater functions for highlighted references, PIR data, collection data, and review activity.
 * This context is used to manage and share workspace-related state across the application.
 */
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

/**
 * Provides shared workspace state to the component tree.
 * Holds PIR data, collection results, highlighted source references,
 * and review activity produced by the AI reviewer between phases.
 * @param children - The child component tree that will consume the workspace context.
 * @returns A context provider wrapping the provided children.
 */
export function WorkspaceProvider({ children }: { children: React.ReactNode }) {
  const [highlightedRefs, setHighlightedRefs] = useState<string[]>([]);
  const [pirData, setPirData] = useState<PirData | null>(null);
  const [collectionData, setCollectionData] =
    useState<CollectionDisplayData | null>(null);
  const [reviewActivity, setReviewActivity] = useState<PhaseReviewItem[]>([]);
  const highlightedRef = highlightedRefs[0] ?? null;
  const setHighlightedRef = useCallback((ref: string | null) => {
    setHighlightedRefs(ref ? [ref] : []);
  }, []);
  /**
   * Merges incoming collection data with existing state, deduplicating items
   * and rebuilding the source summary in a single pass.
   * @param incoming - The new collection display data to merge in.
   */
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
