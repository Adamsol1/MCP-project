import { render, screen, act } from "@testing-library/react";
import { describe, it, expect, vi } from "vitest";
import userEvent from "@testing-library/user-event";
import IntelligencePanel from "./IntelligencePanel";
import { WorkspaceProvider, WorkspaceContext } from "../../contexts/WorkspaceContext/WorkspaceContext";
import type { WorkspaceContextValue } from "../../contexts/WorkspaceContext/WorkspaceContext";
import { ConversationProvider } from "../../contexts/ConversationContext/ConversationContext";
import { SettingsProvider } from "../../contexts/SettingsContext/SettingsContext";
import type { DialoguePhase } from "../../types/dialogue";
import type { PhaseReviewItem } from "../../types/conversation";
import type { CollectionStatus } from "../../services/dialogue/dialogue";
import { axe } from "vitest-axe";

function renderPanel(phase: DialoguePhase) {
  return render(
    <SettingsProvider>
      <ConversationProvider>
        <WorkspaceProvider>
          <IntelligencePanel phase={phase} />
        </WorkspaceProvider>
      </ConversationProvider>
    </SettingsProvider>,
  );
}

/** Renders the panel with a pre-seeded WorkspaceContext value. */
function renderPanelWithWorkspace(
  phase: DialoguePhase,
  workspaceOverrides: Partial<WorkspaceContextValue> = {},
  panelProps: Partial<React.ComponentProps<typeof IntelligencePanel>> = {},
) {
  const defaultCtx: WorkspaceContextValue = {
    highlightedRef: null,
    setHighlightedRef: vi.fn(),
    highlightedRefs: [],
    setHighlightedRefs: vi.fn(),
    pirData: null,
    setPirData: vi.fn(),
    collectionData: null,
    setCollectionData: vi.fn(),
    mergeCollectionData: vi.fn(),
    reviewActivity: [],
    setReviewActivity: vi.fn(),
  };
  const ctx = { ...defaultCtx, ...workspaceOverrides };
  return render(
    <SettingsProvider>
      <ConversationProvider>
        <WorkspaceContext.Provider value={ctx}>
          <IntelligencePanel phase={phase} {...panelProps} />
        </WorkspaceContext.Provider>
      </ConversationProvider>
    </SettingsProvider>,
  );
}

describe("IntelligencePanel", () => {
  it("renders the direction header and view", () => {
    renderPanel("direction");

    expect(screen.getByRole("heading", { name: /direction/i })).toBeInTheDocument();
    // Direction phase shows perspective selector, not a sources list
    expect(screen.queryByText(/no sources available/i)).not.toBeInTheDocument();
  });

  it("renders the collection header and hides the direction view", () => {
    renderPanel("collection");

    expect(screen.getByRole("heading", { name: /collection/i })).toBeInTheDocument();
    expect(screen.queryByText(/no sources available/i)).not.toBeInTheDocument();
  });

  it("renders the processing header", () => {
    renderPanel("processing");

    expect(screen.getByRole("heading", { name: /processing/i })).toBeInTheDocument();
    // Processing phase shows the file upload section
    expect(screen.getByText(/upload files/i)).toBeInTheDocument();
  });

  it("renders the analysis header", () => {
    renderPanel("analysis");

    expect(screen.getByRole("heading", { name: /analysis/i })).toBeInTheDocument();
    // Analysis phase shows the file upload section
    expect(screen.getByText(/upload files/i)).toBeInTheDocument();
  });
});

// ---------- FileUploadSection show-more/show-less ----------

describe("IntelligencePanel — FileUploadSection show more/less", () => {
  function makeFile(n: number) {
    return {
      file_upload_id: `id-${n}`,
      original_filename: `file${n}.pdf`,
      created_at: "2024-01-01",
    };
  }

  it("shows a 'Show N more' button when there are more than 3 uploaded files", () => {
    const files = [makeFile(1), makeFile(2), makeFile(3), makeFile(4), makeFile(5)];
    renderPanelWithWorkspace("collection", {}, { uploadedFiles: files });
    // hiddenCount = 5-3 = 2, button text includes the count
    expect(screen.getByText(/show 2 more/i)).toBeInTheDocument();
  });

  it("clicking 'Show N more' toggles to show all files", async () => {
    const user = userEvent.setup();
    const files = [makeFile(1), makeFile(2), makeFile(3), makeFile(4)];
    renderPanelWithWorkspace("collection", {}, { uploadedFiles: files });

    const toggleBtn = screen.getByText(/show 1 more/i);
    await user.click(toggleBtn);
    // After clicking, all files visible — button should change to "Show less"
    expect(screen.getByText(/show less/i)).toBeInTheDocument();
  });

  it("does not show a 'Show more' button when there are 3 or fewer files", () => {
    const files = [makeFile(1), makeFile(2), makeFile(3)];
    renderPanelWithWorkspace("collection", {}, { uploadedFiles: files });
    expect(screen.queryByText(/show \d+ more/i)).not.toBeInTheDocument();
  });
});

// ---------- ReviewActivitySection ----------

const approvedItem: PhaseReviewItem = {
  phase: "direction",
  attempt: 1,
  reviewer_approved: true,
  reviewer_suggestions: null,
  sources_used: [],
  generated_content: null,
};

const rejectedItem: PhaseReviewItem = {
  phase: "collection",
  attempt: 2,
  reviewer_approved: false,
  reviewer_suggestions: "Expand sources.",
  sources_used: ["osint"],
  generated_content: null,
};

describe("IntelligencePanel — ReviewActivitySection", () => {
  it("renders Review Activity section when reviewActivity has items", () => {
    renderPanelWithWorkspace("direction", { reviewActivity: [approvedItem] });
    expect(screen.getByText(/review activity/i)).toBeInTheDocument();
  });

  it("shows 'Approved' badge for approved review items", () => {
    renderPanelWithWorkspace("direction", { reviewActivity: [approvedItem] });
    expect(screen.getByText("Approved")).toBeInTheDocument();
  });

  it("shows 'Rejected' badge for rejected review items", () => {
    renderPanelWithWorkspace("direction", { reviewActivity: [rejectedItem] });
    expect(screen.getByText("Rejected")).toBeInTheDocument();
  });

  it("does not render Review Activity section when reviewActivity is empty", () => {
    renderPanel("direction");
    expect(screen.queryByText(/review activity/i)).not.toBeInTheDocument();
  });

  it("clicking an attempt row does not throw (onOpenReviewModal is called)", async () => {
    const user = userEvent.setup();
    renderPanelWithWorkspace("direction", { reviewActivity: [approvedItem] });
    const attemptBtn = screen.getByRole("button", { name: /attempt 1/i });
    // Should not throw
    await user.click(attemptBtn);
    // Modal opens — look for the dialog
    expect(screen.getByRole("dialog")).toBeInTheDocument();
  });

  it("shows expand button for processing review item with generated content", () => {
    const processingItem: PhaseReviewItem = {
      phase: "processing",
      attempt: 1,
      reviewer_approved: true,
      reviewer_suggestions: null,
      sources_used: [],
      generated_content: JSON.stringify({
        findings: [{ id: "f1", title: "Finding A", finding: "Detail", confidence: 0.8 }],
        gaps: ["Gap 1"],
      }),
    };
    renderPanelWithWorkspace("direction", { reviewActivity: [processingItem] });
    // Expand button should be visible
    expect(screen.getByRole("button", { name: /expand/i })).toBeInTheDocument();
  });

  it("clicking expand button shows inline findings content", async () => {
    const user = userEvent.setup();
    const processingItem: PhaseReviewItem = {
      phase: "processing",
      attempt: 1,
      reviewer_approved: true,
      reviewer_suggestions: null,
      sources_used: [],
      generated_content: JSON.stringify({
        findings: [{ id: "f1", title: "Finding A", finding: "Detail", confidence: 0.8 }],
        gaps: ["Gap 1"],
      }),
    };
    renderPanelWithWorkspace("direction", { reviewActivity: [processingItem] });
    const expandBtn = screen.getByRole("button", { name: /expand/i });
    await user.click(expandBtn);
    // After expanding, the findings section should appear
    expect(screen.getByText(/Findings/i)).toBeInTheDocument();
    expect(screen.getByText("Finding A")).toBeInTheDocument();
  });

  it("calls onFileRemove when remove button is clicked in FileUploadSection", async () => {
    const user = userEvent.setup();
    const onFileRemove = vi.fn();
    const files = [
      { file_upload_id: "id-1", original_filename: "report.pdf", created_at: "2024-01-01" },
    ];
    renderPanelWithWorkspace("collection", {}, { uploadedFiles: files, onFileRemove });
    await user.click(screen.getByRole("button", { name: /remove report\.pdf/i }));
    expect(onFileRemove).toHaveBeenCalledWith(files[0]);
  });
});

// ---------- CollectionStatusDisplay ----------

describe("IntelligencePanel — CollectionStatusDisplay (direction phase)", () => {
  const collectionStatus: CollectionStatus = {
    current_source: "Web Search",
    current_activity: "Fetching results",
    sources: {
      "AlienVault OTX": { call_count: 2 },
      "Web Search": { call_count: 0 },
      "Knowledge Bank": { call_count: 1 },
    },
  };

  it("renders source names when collectionStatus has sources", () => {
    renderPanelWithWorkspace(
      "direction",
      {},
      { isCollecting: true, collectionStatus },
    );
    expect(screen.getByText("AlienVault OTX")).toBeInTheDocument();
    expect(screen.getByText("Web Search")).toBeInTheDocument();
    expect(screen.getByText("Knowledge Bank")).toBeInTheDocument();
  });

  it("renders the active indicator (●) for current_source", () => {
    renderPanelWithWorkspace(
      "direction",
      {},
      { isCollecting: true, collectionStatus },
    );
    // The active source shows "●"
    const activeIndicators = screen.getAllByText("●");
    expect(activeIndicators.length).toBeGreaterThanOrEqual(1);
  });

  it("renders the current_activity text when set", () => {
    renderPanelWithWorkspace(
      "direction",
      {},
      { isCollecting: true, collectionStatus },
    );
    expect(screen.getByText("Fetching results")).toBeInTheDocument();
  });

  it("renders done indicator (✓) for sources with call_count > 0 that are not current", () => {
    renderPanelWithWorkspace(
      "direction",
      {},
      { isCollecting: true, collectionStatus },
    );
    const doneIndicators = screen.getAllByText("✓");
    expect(doneIndicators.length).toBeGreaterThanOrEqual(1);
  });
});

describe("IntelligencePanel — accessibility (WCAG 2.1 AA)", () => {
  it("has no violations in direction phase", async () => {
    const { container } = renderPanel("direction");
    expect(await axe(container)).toHaveNoViolations();
  });

  it("has no violations in collection phase", async () => {
    const { container } = renderPanel("collection");
    expect(await axe(container)).toHaveNoViolations();
  });
});
