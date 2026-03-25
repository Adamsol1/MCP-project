import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import CollectionStatsModal from "./CollectionStatsModal";
import type { CollectionDisplayData } from "../../types/conversation";

// ---------------------------------------------------------------------------
// Fixture data (same shape as real CollectionDisplayData)
// ---------------------------------------------------------------------------

const COLLECTION_DATA: CollectionDisplayData = {
  source_summary: [
    { display_name: "AlienVault OTX", count: 12, resource_ids: ["r1", "r2"], has_content: true },
    { display_name: "Internal Knowledge Bank", count: 5, resource_ids: ["r3"], has_content: true },
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
    const { container } = render(
      <CollectionStatsModal
        isOpen={false}
        onClose={vi.fn()}
        collectionData={COLLECTION_DATA}
      />,
    );

    expect(container.innerHTML).toBe("");
  });

  it("renders modal content when isOpen is true", () => {
    render(
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

    render(
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

    render(
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
    render(
      <CollectionStatsModal
        isOpen={true}
        onClose={vi.fn()}
        collectionData={COLLECTION_DATA}
      />,
    );

    expect(screen.getAllByText("AlienVault OTX").length).toBeGreaterThanOrEqual(1);
    expect(screen.getAllByText("Internal Knowledge Bank").length).toBeGreaterThanOrEqual(1);
  });

  it("shows the item count for each source", () => {
    render(
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
    render(
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
    render(
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
    render(
      <CollectionStatsModal
        isOpen={true}
        onClose={vi.fn()}
        collectionData={null}
      />,
    );

    expect(screen.getByText(/no data available/i)).toBeInTheDocument();
  });
});
