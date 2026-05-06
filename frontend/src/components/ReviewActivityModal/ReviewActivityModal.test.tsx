import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, it, expect, vi } from "vitest";
import ReviewActivityModal from "./ReviewActivityModal";
import type { PhaseReviewItem } from "../../types/conversation";

// ---------------------------------------------------------------------------
// Fixtures
// ---------------------------------------------------------------------------

const approvedDirectionItem: PhaseReviewItem = {
  phase: "direction",
  attempt: 1,
  reviewer_approved: true,
  reviewer_suggestions: null,
  sources_used: [],
  generated_content: JSON.stringify({
    pirs: [
      {
        question: "Who are the primary threat actors?",
        priority: "high",
        rationale: "Identifying actors drives attribution.",
        source_ids: [],
      },
    ],
    reasoning: "The PIR focuses collection on actor identification.",
    pir_text: null,
  }),
};

const rejectedCollectionItem: PhaseReviewItem = {
  phase: "collection",
  attempt: 2,
  reviewer_approved: false,
  reviewer_suggestions: "The evidence base is too narrow. Expand to additional sources.",
  sources_used: ["osint", "web_search"],
  generated_content: null,
};

const approvedWithSuggestions: PhaseReviewItem = {
  phase: "processing",
  attempt: 1,
  reviewer_approved: true,
  reviewer_suggestions: "Good findings. Consider cross-referencing the timestamps.",
  sources_used: [],
  generated_content: null,
};

const baseActivity: PhaseReviewItem[] = [
  approvedDirectionItem,
  rejectedCollectionItem,
];

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

describe("ReviewActivityModal — closed state", () => {
  it("renders nothing when isOpen is false", () => {
    const { container } = render(
      <ReviewActivityModal
        isOpen={false}
        onClose={vi.fn()}
        activity={baseActivity}
      />,
    );
    expect(container).toBeEmptyDOMElement();
  });
});

describe("ReviewActivityModal — open state", () => {
  it("renders the modal when isOpen is true", () => {
    render(
      <ReviewActivityModal
        isOpen
        onClose={vi.fn()}
        activity={baseActivity}
      />,
    );
    // The dialog div has role="dialog" but no accessible name — match by role only
    expect(screen.getByRole("dialog")).toBeInTheDocument();
    expect(screen.getByText("Review Activity")).toBeInTheDocument();
  });

  it("shows the attempt count and phase summary in the header", () => {
    render(
      <ReviewActivityModal
        isOpen
        onClose={vi.fn()}
        activity={baseActivity}
      />,
    );
    // 2 attempts shown in the subtitle
    expect(screen.getByText(/2 attempts/i)).toBeInTheDocument();
    // Phase names appear in both the header and item rows — just check at least one exists
    expect(screen.getAllByText(/Direction/i).length).toBeGreaterThan(0);
    expect(screen.getAllByText(/Collection/i).length).toBeGreaterThan(0);
  });

  it("shows singular 'attempt' label for a single item", () => {
    render(
      <ReviewActivityModal
        isOpen
        onClose={vi.fn()}
        activity={[approvedDirectionItem]}
      />,
    );
    expect(screen.getByText(/1 attempt[^s]/i)).toBeInTheDocument();
  });

  it("renders the empty state message when activity is empty", () => {
    render(
      <ReviewActivityModal isOpen onClose={vi.fn()} activity={[]} />,
    );
    expect(
      screen.getByText(/No review feedback recorded yet/i),
    ).toBeInTheDocument();
  });

  it("calls onClose when the close button is clicked", async () => {
    const user = userEvent.setup();
    const onClose = vi.fn();
    render(
      <ReviewActivityModal isOpen onClose={onClose} activity={baseActivity} />,
    );

    await user.click(
      screen.getByRole("button", { name: /Close review activity/i }),
    );

    expect(onClose).toHaveBeenCalledOnce();
  });

  it("calls onClose when the backdrop is clicked", async () => {
    const user = userEvent.setup();
    const onClose = vi.fn();
    render(
      <ReviewActivityModal isOpen onClose={onClose} activity={baseActivity} />,
    );

    await user.click(screen.getByTestId("review-activity-modal-backdrop"));

    expect(onClose).toHaveBeenCalledOnce();
  });

  it("does not close when clicking inside the dialog panel", async () => {
    const user = userEvent.setup();
    const onClose = vi.fn();
    render(
      <ReviewActivityModal isOpen onClose={onClose} activity={baseActivity} />,
    );

    await user.click(screen.getByRole("dialog"));

    expect(onClose).not.toHaveBeenCalled();
  });

  it("shows 'Approved' badge for approved items", () => {
    render(
      <ReviewActivityModal
        isOpen
        onClose={vi.fn()}
        activity={[approvedDirectionItem]}
      />,
    );
    expect(screen.getByText("Approved")).toBeInTheDocument();
  });

  it("shows 'Rejected' badge for rejected items", () => {
    render(
      <ReviewActivityModal
        isOpen
        onClose={vi.fn()}
        activity={[rejectedCollectionItem]}
      />,
    );
    expect(screen.getByText("Rejected")).toBeInTheDocument();
  });

  it("shows reviewer suggestions when present", () => {
    render(
      <ReviewActivityModal
        isOpen
        onClose={vi.fn()}
        activity={[rejectedCollectionItem]}
      />,
    );
    expect(
      screen.getByText(/The evidence base is too narrow/i),
    ).toBeInTheDocument();
  });

  it("shows 'Approved — no further feedback' when approved with no suggestions", () => {
    render(
      <ReviewActivityModal
        isOpen
        onClose={vi.fn()}
        activity={[approvedDirectionItem]}
      />,
    );
    expect(screen.getByText(/Approved — no further feedback/i)).toBeInTheDocument();
  });

  it("shows reviewer suggestions even when the item was approved", () => {
    render(
      <ReviewActivityModal
        isOpen
        onClose={vi.fn()}
        activity={[approvedWithSuggestions]}
      />,
    );
    expect(
      screen.getByText(/Consider cross-referencing the timestamps/i),
    ).toBeInTheDocument();
  });

  it("renders sources used for collection-phase items", () => {
    render(
      <ReviewActivityModal
        isOpen
        onClose={vi.fn()}
        activity={[rejectedCollectionItem]}
      />,
    );
    expect(screen.getByText("osint")).toBeInTheDocument();
    expect(screen.getByText("web_search")).toBeInTheDocument();
  });

  it("opens all items by default when focusAttempt is not set", () => {
    render(
      <ReviewActivityModal
        isOpen
        onClose={vi.fn()}
        activity={baseActivity}
      />,
    );
    // Both items expanded — AI Feedback sections should be visible for both
    const feedbackHeadings = screen.getAllByText(/AI Feedback/i);
    expect(feedbackHeadings.length).toBe(2);
  });

  it("opens only the targeted attempt when focusAttempt is set", () => {
    const { container } = render(
      <ReviewActivityModal
        isOpen
        onClose={vi.fn()}
        activity={baseActivity}
        focusAttempt={1}
      />,
    );
    // focusAttempt=1 → attempt 1 details element has open attribute, attempt 2 does not
    const detailsEls = container.querySelectorAll("details");
    expect(detailsEls).toHaveLength(2);
    expect(detailsEls[0]).toHaveAttribute("open"); // attempt 1 (focusAttempt match)
    expect(detailsEls[1]).not.toHaveAttribute("open"); // attempt 2 (not focused)
  });

  it("renders parsed PIR content in direction phase transcripts", () => {
    render(
      <ReviewActivityModal
        isOpen
        onClose={vi.fn()}
        activity={[approvedDirectionItem]}
      />,
    );
    expect(
      screen.getByText(/Who are the primary threat actors/i),
    ).toBeInTheDocument();
    expect(
      screen.getByText(/Intelligence Requirements/i),
    ).toBeInTheDocument();
  });

  it("renders the attempt number in each row", () => {
    render(
      <ReviewActivityModal
        isOpen
        onClose={vi.fn()}
        activity={baseActivity}
      />,
    );
    expect(screen.getByText(/Attempt 1/i)).toBeInTheDocument();
    expect(screen.getByText(/Attempt 2/i)).toBeInTheDocument();
  });
});
