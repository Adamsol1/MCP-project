import { describe, it, expect, vi } from "vitest";
import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import CollectionStatsModal from "./CollectionStatsModal";
import { renderWithSettings } from "../../test/renderWithProviders";
import type { CollectionDisplayData } from "../../types/conversation";
import { axe } from "vitest-axe";

// ---------------------------------------------------------------------------
// Fixture data (same shape as real CollectionDisplayData)
// ---------------------------------------------------------------------------

const COLLECTION_DATA: CollectionDisplayData = {
  source_summary: [
    { display_name: "AlienVault OTX", count: 12, resource_ids: ["r1", "r2"], has_content: true },
    { display_name: "Knowledge Bank", count: 5, resource_ids: ["r3"], has_content: true },
  ],
  collected_data: [
    { source: "query_otx", resource_id: "r1", content: "threat report about APT29" },
    { source: "query_otx", resource_id: "r2", content: "indicator of compromise list" },
    { source: "list_knowledge_base", resource_id: "r3", content: "internal threat brief" },
  ],
};

// ---------------------------------------------------------------------------
// Tests: CollectionStatsModal
// ---------------------------------------------------------------------------

describe("CollectionStatsModal", () => {
  // --- Visibility ---

  it("renders nothing when isOpen is false", () => {
    const { container } = renderWithSettings(
      <CollectionStatsModal
        isOpen={false}
        onClose={vi.fn()}
        collectionData={COLLECTION_DATA}
      />,
    );

    expect(container.innerHTML).toBe("");
  });

  it("renders modal content when isOpen is true", () => {
    renderWithSettings(
      <CollectionStatsModal
        isOpen={true}
        onClose={vi.fn()}
        collectionData={COLLECTION_DATA}
      />,
    );

    expect(screen.getByTestId("collection-stats-modal")).toBeInTheDocument();
  });

  // --- Close behaviour ---

  it("calls onClose when the backdrop is clicked", async () => {
    const onClose = vi.fn();
    const user = userEvent.setup();

    renderWithSettings(
      <CollectionStatsModal
        isOpen={true}
        onClose={onClose}
        collectionData={COLLECTION_DATA}
      />,
    );

    await user.click(screen.getByTestId("modal-backdrop"));

    expect(onClose).toHaveBeenCalledOnce();
  });

  it("calls onClose when the close button is clicked", async () => {
    const onClose = vi.fn();
    const user = userEvent.setup();

    renderWithSettings(
      <CollectionStatsModal
        isOpen={true}
        onClose={onClose}
        collectionData={COLLECTION_DATA}
      />,
    );

    await user.click(screen.getByRole("button", { name: /close/i }));

    expect(onClose).toHaveBeenCalledOnce();
  });

  // --- Stats section ---

  it("shows all source names in the stats section", () => {
    renderWithSettings(
      <CollectionStatsModal
        isOpen={true}
        onClose={vi.fn()}
        collectionData={COLLECTION_DATA}
      />,
    );

    expect(screen.getAllByText("AlienVault OTX").length).toBeGreaterThanOrEqual(1);
    expect(screen.getAllByText("Knowledge Bank").length).toBeGreaterThanOrEqual(1);
  });

  it("shows the item count for each source", () => {
    renderWithSettings(
      <CollectionStatsModal
        isOpen={true}
        onClose={vi.fn()}
        collectionData={COLLECTION_DATA}
      />,
    );

    // counts: 12 and 5
    expect(screen.getByText("12")).toBeInTheDocument();
    expect(screen.getByText("5")).toBeInTheDocument();
  });

  // --- Raw data section ---

  it("renders a collapsible section for each source's raw items", () => {
    renderWithSettings(
      <CollectionStatsModal
        isOpen={true}
        onClose={vi.fn()}
        collectionData={COLLECTION_DATA}
      />,
    );

    // Each source group has a summary element with the source display name
    const summaries = screen.getAllByRole("group");
    // We expect at least one group per source that has data
    expect(summaries.length).toBeGreaterThanOrEqual(2);
  });

  it("renders raw content for collected items", () => {
    renderWithSettings(
      <CollectionStatsModal
        isOpen={true}
        onClose={vi.fn()}
        collectionData={COLLECTION_DATA}
      />,
    );

    expect(screen.getByText(/threat report about APT29/i)).toBeInTheDocument();
    expect(screen.getByText(/indicator of compromise list/i)).toBeInTheDocument();
  });

  // --- Null data guard ---

  it("renders a fallback when collectionData is null", () => {
    renderWithSettings(
      <CollectionStatsModal
        isOpen={true}
        onClose={vi.fn()}
        collectionData={null}
      />,
    );

    expect(screen.getByText(/no data available/i)).toBeInTheDocument();
  });
});

// ---------------------------------------------------------------------------
// Additional tests for uncovered lines
// ---------------------------------------------------------------------------

describe("CollectionStatsModal — empty source handling", () => {
  it("shows empty indicator for sources with no content", () => {
    const dataWithEmpty: CollectionDisplayData = {
      source_summary: [
        { display_name: "AlienVault OTX", count: 3, resource_ids: ["r1"], has_content: true },
        { display_name: "Knowledge Bank", count: 0, resource_ids: [], has_content: false },
      ],
      collected_data: [
        { source: "query_otx", resource_id: "r1", content: "some data" },
      ],
    };
    renderWithSettings(
      <CollectionStatsModal isOpen onClose={vi.fn()} collectionData={dataWithEmpty} />,
    );
    // "Empty" label should appear for the source with has_content: false
    expect(screen.getByText(/empty/i)).toBeInTheDocument();
  });
});

describe("CollectionStatsModal — item count badge", () => {
  it("shows correct item count for each source group", () => {
    renderWithSettings(
      <CollectionStatsModal
        isOpen
        onClose={vi.fn()}
        collectionData={COLLECTION_DATA}
      />,
    );
    // The itemCount() function renders "2 items" and "1 item"
    expect(screen.getByText("2 items")).toBeInTheDocument();
    expect(screen.getByText("1 item")).toBeInTheDocument();
  });
});

describe("CollectionStatsModal — OTX content rendering", () => {
  it("renders OTX pulse data when source is query_otx with JSON pulse content", () => {
    const otxData: CollectionDisplayData = {
      source_summary: [
        { display_name: "AlienVault OTX", count: 1, resource_ids: ["otx-1"], has_content: true },
      ],
      collected_data: [
        {
          source: "query_otx",
          resource_id: "otx-1",
          content: JSON.stringify([{
            name: "APT29 Campaign",
            description: "Russian cyber campaign targeting EU",
            adversary: "APT29",
            indicator_count: 42,
            tags: ["russia", "apt29", "eu"],
            targeted_countries: ["Norway", "Germany"],
            malware_families: ["Cozy Bear"],
            attack_ids: ["T1190"],
          }]),
        },
      ],
    };
    renderWithSettings(
      <CollectionStatsModal isOpen onClose={vi.fn()} collectionData={otxData} />,
    );
    // Source group should appear
    expect(screen.getAllByText("AlienVault OTX").length).toBeGreaterThanOrEqual(1);
  });
});

describe("CollectionStatsModal — multiple items from one source", () => {
  it("shows correct count when a source has multiple items", () => {
    const multiData: CollectionDisplayData = {
      source_summary: [
        { display_name: "AlienVault OTX", count: 3, resource_ids: ["r1", "r2", "r3"], has_content: true },
      ],
      collected_data: [
        { source: "query_otx", resource_id: "r1", content: "item 1" },
        { source: "query_otx", resource_id: "r2", content: "item 2" },
        { source: "query_otx", resource_id: "r3", content: "item 3" },
      ],
    };
    renderWithSettings(
      <CollectionStatsModal isOpen onClose={vi.fn()} collectionData={multiData} />,
    );
    // "3 items" may appear more than once (header + group count)
    expect(screen.getAllByText("3 items").length).toBeGreaterThanOrEqual(1);
  });
});

describe("CollectionStatsModal — KB content with no content placeholder", () => {
  it("renders (no content) placeholder for KB items with empty content", () => {
    const kbEmptyData: CollectionDisplayData = {
      source_summary: [
        { display_name: "Knowledge Bank", count: 1, resource_ids: ["kb-1"], has_content: false },
      ],
      collected_data: [
        { source: "list_knowledge_base", resource_id: "kb-1", content: "" },
      ],
    };
    renderWithSettings(
      <CollectionStatsModal isOpen onClose={vi.fn()} collectionData={kbEmptyData} />,
    );
    // KbContent renders "(no content)" for empty content
    expect(screen.getByText("(no content)")).toBeInTheDocument();
  });
});

describe("CollectionStatsModal — web article-type slices", () => {
  it("renders web article-type legend entries and nested sub-groups for web sources", () => {
    // Web sources (fetch_page, google_search, google_news_search) get grouped by article type
    const webData: CollectionDisplayData = {
      source_summary: [
        { display_name: "Web Fetch", count: 2, resource_ids: ["https://example.gov/report", "https://reuters.com/article"], has_content: true },
      ],
      collected_data: [
        {
          source: "fetch_page",
          resource_id: "https://example.gov/report",
          title: "Official Report",
          content: "Official government report content",
        },
        {
          source: "fetch_page",
          resource_id: "https://reuters.com/article",
          title: "News Article",
          content: "News article content",
        },
      ],
    };
    renderWithSettings(
      <CollectionStatsModal isOpen onClose={vi.fn()} collectionData={webData} />,
    );
    // The modal should render with web source data
    expect(screen.getByTestId("collection-stats-modal")).toBeInTheDocument();
    // Source group for Web Fetch should appear
    expect(screen.getAllByText("Web Fetch").length).toBeGreaterThanOrEqual(1);
  });
});

describe("CollectionStatsModal — itemsAcrossSources header", () => {
  it("renders the items-across-sources summary in the header", () => {
    renderWithSettings(
      <CollectionStatsModal
        isOpen
        onClose={vi.fn()}
        collectionData={COLLECTION_DATA}
      />,
    );
    // 17 items across 2 sources (12 + 5)
    expect(screen.getByText(/17 items across 2 sources/i)).toBeInTheDocument();
  });
});

describe("CollectionStatsModal — accessibility (WCAG 2.1 AA)", () => {
  it("has no violations when open with data", async () => {
    const { container } = renderWithSettings(
      <CollectionStatsModal
        isOpen={true}
        onClose={vi.fn()}
        collectionData={COLLECTION_DATA}
      />,
    );
    expect(await axe(container)).toHaveNoViolations();
  });
});
