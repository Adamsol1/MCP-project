import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import CollectionStatsView from "./CollectionStatsView";
import type { CollectionDisplayData } from "../../types/conversation";

// ---------------------------------------------------------------------------
// Minimal fixture data
// ---------------------------------------------------------------------------

const SOURCE_SUMMARIES = [
  { display_name: "AlienVault OTX", count: 12, resource_ids: ["r1", "r2"], has_content: true },
  { display_name: "Internal Knowledge Bank", count: 5, resource_ids: ["r3"], has_content: true },
  { display_name: "Uploaded Documents", count: 0, resource_ids: [], has_content: false },
];

const COLLECTED_ITEMS = [
  { source: "query_otx", resource_id: "r1", content: "threat report content" },
  { source: "list_knowledge_base", resource_id: "r3", content: "internal doc" },
];

const COLLECTION_DATA: CollectionDisplayData = {
  source_summary: SOURCE_SUMMARIES,
  collected_data: COLLECTED_ITEMS,
};

// ---------------------------------------------------------------------------
// Tests: CollectionStatsView
// ---------------------------------------------------------------------------

describe("CollectionStatsView", () => {
  // --- Empty / no-data state ---

  it("renders an empty state when collectionData is null", () => {
    render(<CollectionStatsView collectionData={null} onOpenModal={vi.fn()} />);

    expect(screen.getByText(/no collection data/i)).toBeInTheDocument();
  });

  // --- Summary numbers ---

  it("shows the total number of items collected", () => {
    render(
      <CollectionStatsView
        collectionData={COLLECTION_DATA}
        onOpenModal={vi.fn()}
      />,
    );

    // 12 + 5 + 0 = 17 total items
    expect(screen.getByText("17")).toBeInTheDocument();
  });

  it("shows the number of sources queried", () => {
    render(
      <CollectionStatsView
        collectionData={COLLECTION_DATA}
        onOpenModal={vi.fn()}
      />,
    );

    // 3 sources in SOURCE_SUMMARIES
    expect(screen.getByText("3")).toBeInTheDocument();
  });

  // --- Source bars ---

  it("renders a bar or label for each source", () => {
    render(
      <CollectionStatsView
        collectionData={COLLECTION_DATA}
        onOpenModal={vi.fn()}
      />,
    );

    expect(screen.getByText("AlienVault OTX")).toBeInTheDocument();
    expect(screen.getByText("Internal Knowledge Bank")).toBeInTheDocument();
    expect(screen.getByText("Uploaded Documents")).toBeInTheDocument();
  });

  it("marks sources with no content as empty", () => {
    render(
      <CollectionStatsView
        collectionData={COLLECTION_DATA}
        onOpenModal={vi.fn()}
      />,
    );

    // "Uploaded Documents" has has_content: false → should show "Empty" somewhere
    expect(screen.getByText(/empty/i)).toBeInTheDocument();
  });

  // --- Modal trigger ---

  it("renders a 'View Raw Data' button", () => {
    render(
      <CollectionStatsView
        collectionData={COLLECTION_DATA}
        onOpenModal={vi.fn()}
      />,
    );

    expect(
      screen.getByRole("button", { name: /view raw data/i }),
    ).toBeInTheDocument();
  });

  it("calls onOpenModal when 'View Raw Data' is clicked", async () => {
    const onOpenModal = vi.fn();
    const user = userEvent.setup();

    render(
      <CollectionStatsView
        collectionData={COLLECTION_DATA}
        onOpenModal={onOpenModal}
      />,
    );

    await user.click(screen.getByRole("button", { name: /view raw data/i }));

    expect(onOpenModal).toHaveBeenCalledOnce();
  });
});
