import { render, screen, act } from "@testing-library/react";
import { describe, it, expect } from "vitest";
import { WorkspaceProvider, useWorkspace } from "./WorkspaceContext";
import type { CollectionDisplayData, CollectedItem, PirData } from "../../types/conversation";

function HighlightedRefsDisplay() {
  const { highlightedRefs } = useWorkspace();
  return <span data-testid="refs">{highlightedRefs.join(",") || "empty"}</span>;
}

function PirDataDisplay() {
  const { pirData } = useWorkspace();
  return <span data-testid="pir">{pirData ? pirData.pir_text : "null"}</span>;
}

function CollectionDataDisplay() {
  const { collectionData } = useWorkspace();
  return (
    <span data-testid="collection">
      {collectionData ? collectionData.collected_data.length.toString() : "null"}
    </span>
  );
}

function SetHighlightedRefsButton({ refs }: { refs: string[] }) {
  const { setHighlightedRefs } = useWorkspace();
  return <button onClick={() => setHighlightedRefs(refs)}>set refs</button>;
}

function SetPirDataButton({ pirData }: { pirData: PirData }) {
  const { setPirData } = useWorkspace();
  return <button onClick={() => setPirData(pirData)}>set pir</button>;
}

function SetCollectionDataButton({ data }: { data: CollectionDisplayData }) {
  const { setCollectionData } = useWorkspace();
  return <button onClick={() => setCollectionData(data)}>set collection</button>;
}

describe("WorkspaceContext", () => {
  it("provides empty default workspace values", () => {
    render(
      <WorkspaceProvider>
        <HighlightedRefsDisplay />
        <PirDataDisplay />
        <CollectionDataDisplay />
      </WorkspaceProvider>,
    );

    expect(screen.getByTestId("refs")).toHaveTextContent("empty");
    expect(screen.getByTestId("pir")).toHaveTextContent("null");
    expect(screen.getByTestId("collection")).toHaveTextContent("null");
  });

  it("updates highlighted refs", async () => {
    render(
      <WorkspaceProvider>
        <HighlightedRefsDisplay />
        <SetHighlightedRefsButton refs={["[1]", "[2]"]} />
      </WorkspaceProvider>,
    );

    await act(async () => {
      screen.getByRole("button", { name: "set refs" }).click();
    });

    expect(screen.getByTestId("refs")).toHaveTextContent("[1],[2]");
  });

  it("updates pir data", async () => {
    render(
      <WorkspaceProvider>
        <PirDataDisplay />
        <SetPirDataButton
          pirData={{
            pir_text: "Norway threat assessment.",
            claims: [],
            sources: [],
            pirs: [],
            reasoning: "",
          }}
        />
      </WorkspaceProvider>,
    );

    await act(async () => {
      screen.getByRole("button", { name: "set pir" }).click();
    });

    expect(screen.getByTestId("pir")).toHaveTextContent(
      "Norway threat assessment.",
    );
  });

  it("updates collection data", async () => {
    render(
      <WorkspaceProvider>
        <CollectionDataDisplay />
        <SetCollectionDataButton
          data={{
            collected_data: [
              { source: "web", resource_id: null, content: "Sample content" },
            ],
            source_summary: [
              {
                display_name: "Web",
                count: 1,
                resource_ids: [],
                has_content: true,
              },
            ],
          }}
        />
      </WorkspaceProvider>,
    );

    await act(async () => {
      screen.getByRole("button", { name: "set collection" }).click();
    });

    expect(screen.getByTestId("collection")).toHaveTextContent("1");
  });
});

// ---------------------------------------------------------------------------
// mergeCollectionData — deduplication logic
// ---------------------------------------------------------------------------

function MergeCollectionDataButton({ data }: { data: CollectionDisplayData }) {
  const { mergeCollectionData } = useWorkspace();
  return <button onClick={() => mergeCollectionData(data)}>merge</button>;
}

function CollectionItemCountDisplay() {
  const { collectionData } = useWorkspace();
  return (
    <span data-testid="count">
      {collectionData ? collectionData.collected_data.length.toString() : "0"}
    </span>
  );
}

describe("WorkspaceContext — mergeCollectionData", () => {
  it("merges a batch from a null start (prev is null → takes incoming path)", async () => {
    const batch1: CollectionDisplayData = {
      collected_data: [{ source: "knowledge_base", resource_id: "kb/1", content: "KB content" }],
      source_summary: [],
    };

    render(
      <WorkspaceProvider>
        <CollectionItemCountDisplay />
        <MergeCollectionDataButton data={batch1} />
      </WorkspaceProvider>,
    );

    // Merge first batch (prev is null, takes the incoming path)
    await act(async () => {
      screen.getByRole("button", { name: "merge" }).click();
    });
    expect(screen.getByTestId("count")).toHaveTextContent("1");
  });

  it("deduplicates web items with the same title (covers lines 40-46)", async () => {
    // Two web items with the same title from the same source → deduplicated to 1
    const webItem1: CollectedItem = {
      source: "google_search",
      resource_id: "url1",
      content: "Short content",
      title: "APT29 Activity Report",
    };
    const webItem2: CollectedItem = {
      source: "google_search",
      resource_id: "url2",
      content: "Much longer content here so it wins",
      title: "APT29 Activity Report",
    };

    const batch: CollectionDisplayData = {
      collected_data: [webItem1, webItem2],
      source_summary: [],
    };

    render(
      <WorkspaceProvider>
        <CollectionItemCountDisplay />
        <MergeCollectionDataButton data={batch} />
      </WorkspaceProvider>,
    );

    await act(async () => {
      screen.getByRole("button", { name: "merge" }).click();
    });

    // Two web items with the same title → deduplicated to 1
    expect(screen.getByTestId("count")).toHaveTextContent("1");
  });

  it("deduplicates by (source, resource_id) when same resource_id appears twice", async () => {
    // Same source + resource_id combo: second has more content and should win
    const item1: CollectedItem = {
      source: "knowledge_base",
      resource_id: "kb/norway",
      content: "Short",
    };
    const item2: CollectedItem = {
      source: "knowledge_base",
      resource_id: "kb/norway",
      content: "Much longer content that should replace the first",
    };

    const batch: CollectionDisplayData = {
      collected_data: [item1, item2],
      source_summary: [],
    };

    render(
      <WorkspaceProvider>
        <CollectionItemCountDisplay />
        <MergeCollectionDataButton data={batch} />
      </WorkspaceProvider>,
    );

    await act(async () => {
      screen.getByRole("button", { name: "merge" }).click();
    });

    // Two items with same (source, resource_id) → deduplicated to 1
    expect(screen.getByTestId("count")).toHaveTextContent("1");
  });

  it("keeps web items with different titles as separate entries", async () => {
    const webItem1: CollectedItem = {
      source: "google_news_search",
      resource_id: "url1",
      content: "Content A",
      title: "Title One",
    };
    const webItem2: CollectedItem = {
      source: "google_news_search",
      resource_id: "url2",
      content: "Content B",
      title: "Title Two",
    };

    const batch: CollectionDisplayData = {
      collected_data: [webItem1, webItem2],
      source_summary: [],
    };

    render(
      <WorkspaceProvider>
        <CollectionItemCountDisplay />
        <MergeCollectionDataButton data={batch} />
      </WorkspaceProvider>,
    );

    await act(async () => {
      screen.getByRole("button", { name: "merge" }).click();
    });

    // Different titles → both kept
    expect(screen.getByTestId("count")).toHaveTextContent("2");
  });

  it("handles items with null resource_id in buildSourceSummary (line 64)", async () => {
    // resource_id is null → the resource_ids push branch is skipped
    const item: CollectedItem = {
      source: "knowledge_base",
      resource_id: null,
      content: "Some content",
    };

    const batch: CollectionDisplayData = {
      collected_data: [item],
      source_summary: [],
    };

    render(
      <WorkspaceProvider>
        <CollectionItemCountDisplay />
        <MergeCollectionDataButton data={batch} />
      </WorkspaceProvider>,
    );

    await act(async () => {
      screen.getByRole("button", { name: "merge" }).click();
    });

    expect(screen.getByTestId("count")).toHaveTextContent("1");
  });

  it("handles items with empty content in buildSourceSummary (line 67)", async () => {
    // content is empty/whitespace → has_content stays false
    const item: CollectedItem = {
      source: "knowledge_base",
      resource_id: "kb/1",
      content: "   ",
    };

    const batch: CollectionDisplayData = {
      collected_data: [item],
      source_summary: [],
    };

    render(
      <WorkspaceProvider>
        <CollectionItemCountDisplay />
        <MergeCollectionDataButton data={batch} />
      </WorkspaceProvider>,
    );

    await act(async () => {
      screen.getByRole("button", { name: "merge" }).click();
    });

    expect(screen.getByTestId("count")).toHaveTextContent("1");
  });

  it("handles setHighlightedRef(null) to clear the ref (line 100)", async () => {
    function SetAndClearRef() {
      const { setHighlightedRef, highlightedRef } = useWorkspace();
      return (
        <>
          <span data-testid="ref">{highlightedRef ?? "empty"}</span>
          <button onClick={() => setHighlightedRef("[1]")}>set</button>
          <button onClick={() => setHighlightedRef(null)}>clear</button>
        </>
      );
    }

    render(
      <WorkspaceProvider>
        <SetAndClearRef />
      </WorkspaceProvider>,
    );

    await act(async () => {
      screen.getByRole("button", { name: "set" }).click();
    });
    expect(screen.getByTestId("ref")).toHaveTextContent("[1]");

    await act(async () => {
      screen.getByRole("button", { name: "clear" }).click();
    });
    expect(screen.getByTestId("ref")).toHaveTextContent("empty");
  });

  it("handles merge when prev collectionData already exists (covers combined path)", async () => {
    // We render a component that can do two merges in sequence
    function TwoMergeTest() {
      const { mergeCollectionData, collectionData } = useWorkspace();
      const count = collectionData ? collectionData.collected_data.length : 0;
      return (
        <>
          <span data-testid="count2">{count}</span>
          <button
            onClick={() =>
              mergeCollectionData({
                collected_data: [{ source: "query_otx", resource_id: "otx/1", content: "A" }],
                source_summary: [],
              })
            }
          >
            merge-a
          </button>
          <button
            onClick={() =>
              mergeCollectionData({
                collected_data: [{ source: "query_otx", resource_id: "otx/2", content: "B" }],
                source_summary: [],
              })
            }
          >
            merge-b
          </button>
        </>
      );
    }

    render(
      <WorkspaceProvider>
        <TwoMergeTest />
      </WorkspaceProvider>,
    );

    await act(async () => {
      screen.getByRole("button", { name: "merge-a" }).click();
    });
    expect(screen.getByTestId("count2")).toHaveTextContent("1");

    await act(async () => {
      screen.getByRole("button", { name: "merge-b" }).click();
    });
    // Two different items from different sources → both kept
    expect(screen.getByTestId("count2")).toHaveTextContent("2");
  });
});
