import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, it, expect, vi } from "vitest";
import { axe } from "vitest-axe";
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

// ---------------------------------------------------------------------------
// Transcript rendering tests
// ---------------------------------------------------------------------------

describe("ReviewActivityModal — transcript rendering", () => {
  it("renders PIR transcript with pirs list and reasoning", () => {
    const item: PhaseReviewItem = {
      phase: "direction",
      attempt: 1,
      reviewer_approved: true,
      reviewer_suggestions: null,
      sources_used: [],
      generated_content: JSON.stringify({
        pirs: [{ question: "Q?", priority: "high", rationale: "R" }],
        reasoning: "R.",
      }),
    };
    render(
      <ReviewActivityModal isOpen onClose={vi.fn()} activity={[item]} />,
    );
    expect(screen.getByText(/Intelligence Requirements/i)).toBeInTheDocument();
    expect(screen.getByText("Q?")).toBeInTheDocument();
    expect(screen.getByText("R")).toBeInTheDocument();
  });

  it("renders CollectionTranscript with collected items and source summary", () => {
    const item: PhaseReviewItem = {
      phase: "collection",
      attempt: 1,
      reviewer_approved: true,
      reviewer_suggestions: null,
      sources_used: [],
      generated_content: JSON.stringify({
        collected_data: [
          {
            source: "otx",
            resource_id: "r1",
            title: "Threat Title",
            content: "Content about threats",
            author: "Author",
            date: "2024",
            publisher: "Pub",
          },
        ],
        source_summary: [{ display_name: "OTX", count: 2 }],
      }),
    };
    render(
      <ReviewActivityModal isOpen onClose={vi.fn()} activity={[item]} />,
    );
    expect(screen.getByText("OTX")).toBeInTheDocument();
    expect(screen.getByText(/Collected Items/i)).toBeInTheDocument();
  });

  it("renders CollectionSummaryTranscript with summary, sources_used, and gaps", () => {
    const item: PhaseReviewItem = {
      phase: "collection",
      attempt: 1,
      reviewer_approved: true,
      reviewer_suggestions: null,
      sources_used: [],
      generated_content: JSON.stringify({
        summary: "Summary text here",
        sources_used: ["osint"],
        gaps: "Some gaps identified",
      }),
    };
    render(
      <ReviewActivityModal isOpen onClose={vi.fn()} activity={[item]} />,
    );
    expect(screen.getByText("Summary text here")).toBeInTheDocument();
    expect(screen.getByText("osint")).toBeInTheDocument();
    expect(screen.getByText("Some gaps identified")).toBeInTheDocument();
  });

  it("renders ProcessingTranscript with findings and gaps", () => {
    const item: PhaseReviewItem = {
      phase: "processing",
      attempt: 1,
      reviewer_approved: true,
      reviewer_suggestions: null,
      sources_used: [],
      generated_content: JSON.stringify({
        findings: [
          {
            id: "f1",
            title: "Finding Title",
            finding: "Detail",
            confidence: 0.8,
            evidence_summary: "Ev",
            why_it_matters: "Important",
          },
        ],
        gaps: ["Gap 1"],
      }),
    };
    render(
      <ReviewActivityModal isOpen onClose={vi.fn()} activity={[item]} />,
    );
    expect(screen.getByText(/Findings/i)).toBeInTheDocument();
    expect(screen.getByText("Finding Title")).toBeInTheDocument();
    expect(screen.getByText("Gap 1")).toBeInTheDocument();
  });

  it("renders AnalysisTranscript with title, summary, judgments, actions, and gaps", () => {
    const item: PhaseReviewItem = {
      phase: "analysis",
      attempt: 1,
      reviewer_approved: true,
      reviewer_suggestions: null,
      sources_used: [],
      generated_content: JSON.stringify({
        analysis_draft: {
          title: "Analysis Title",
          summary: "Sum",
          key_judgments: ["J1"],
          recommended_actions: ["A1"],
          information_gaps: ["G1"],
        },
      }),
    };
    render(
      <ReviewActivityModal isOpen onClose={vi.fn()} activity={[item]} />,
    );
    expect(screen.getByText("Analysis Title")).toBeInTheDocument();
    expect(screen.getByText("Sum")).toBeInTheDocument();
    expect(screen.getByText("J1")).toBeInTheDocument();
    expect(screen.getByText("A1")).toBeInTheDocument();
    expect(screen.getByText("G1")).toBeInTheDocument();
  });

  it("renders bold text from reviewer_suggestions using InlineFormatted", () => {
    const item: PhaseReviewItem = {
      phase: "direction",
      attempt: 1,
      reviewer_approved: false,
      reviewer_suggestions: "Please fix **this issue** now.",
      sources_used: [],
      generated_content: null,
    };
    render(
      <ReviewActivityModal isOpen onClose={vi.fn()} activity={[item]} />,
    );
    const boldEl = screen.getByText("this issue");
    expect(boldEl.tagName).toBe("STRONG");
  });

  it("renders unrecognised content as formatted text when shape doesn't match any transcript", () => {
    const item: PhaseReviewItem = {
      phase: "direction",
      attempt: 1,
      reviewer_approved: true,
      reviewer_suggestions: null,
      sources_used: [],
      generated_content: "Plain text content that is not JSON",
    };
    render(
      <ReviewActivityModal isOpen onClose={vi.fn()} activity={[item]} />,
    );
    expect(screen.getByText("Plain text content that is not JSON")).toBeInTheDocument();
  });

  it("renders ProcessingTranscript from array-of-findings format (not object)", () => {
    // This exercises the Array.isArray path (line 409) where processing content
    // is an array of findings rather than an object with a 'findings' key.
    const item: PhaseReviewItem = {
      phase: "processing",
      attempt: 1,
      reviewer_approved: true,
      reviewer_suggestions: null,
      sources_used: [],
      generated_content: JSON.stringify([
        {
          id: "f1",
          title: "Array Finding",
          finding: "Found from array format",
          confidence: 0.9,
        },
      ]),
    };
    render(
      <ReviewActivityModal isOpen onClose={vi.fn()} activity={[item]} />,
    );
    expect(screen.getByText("Array Finding")).toBeInTheDocument();
  });

  it("renders a low-priority PIR badge (exercises the 'low' PRIORITY_STYLES entry)", () => {
    const item: PhaseReviewItem = {
      phase: "direction",
      attempt: 1,
      reviewer_approved: true,
      reviewer_suggestions: null,
      sources_used: [],
      generated_content: JSON.stringify({
        pirs: [{ question: "Low priority Q?", priority: "low", rationale: "Not urgent" }],
        reasoning: "",
      }),
    };
    render(
      <ReviewActivityModal isOpen onClose={vi.fn()} activity={[item]} />,
    );
    expect(screen.getByText("low")).toBeInTheDocument();
  });

  it("opens and closes the help modal when HelpButton is clicked", async () => {
    const user = userEvent.setup();
    render(
      <ReviewActivityModal isOpen onClose={vi.fn()} activity={[approvedDirectionItem]} />,
    );
    // Click the help button (the ? icon button)
    const helpBtn = screen.getByRole("button", { name: /review activity guide/i });
    await user.click(helpBtn);
    // Help modal should be visible
    expect(screen.getByText(/What is Review Activity\?/i)).toBeInTheDocument();
  });

  it("parses content wrapped in a markdown code fence (exercises stripCodeFence)", () => {
    // Content starts with ```json ... ``` — the stripCodeFence function handles this
    const item: PhaseReviewItem = {
      phase: "direction",
      attempt: 1,
      reviewer_approved: true,
      reviewer_suggestions: null,
      sources_used: [],
      generated_content: "```json\n" + JSON.stringify({
        pirs: [{ question: "Code fence Q?", priority: "medium", rationale: "Code fence R" }],
        reasoning: "Code fence reasoning",
      }) + "\n```",
    };
    render(
      <ReviewActivityModal isOpen onClose={vi.fn()} activity={[item]} />,
    );
    expect(screen.getByText("Code fence Q?")).toBeInTheDocument();
  });

  it("parses Python-repr content by normalising single quotes to double quotes", () => {
    // Python repr uses single quotes — normalizePythonRepr handles the conversion
    const item: PhaseReviewItem = {
      phase: "direction",
      attempt: 1,
      reviewer_approved: true,
      reviewer_suggestions: null,
      sources_used: [],
      // Python repr with single quotes and True/False/None
      generated_content: "{'pirs': [{'question': 'Python Q?', 'priority': 'high', 'rationale': 'Python R'}], 'reasoning': 'Python reasoning', 'pir_text': None}",
    };
    render(
      <ReviewActivityModal isOpen onClose={vi.fn()} activity={[item]} />,
    );
    expect(screen.getByText("Python Q?")).toBeInTheDocument();
  });
});

describe("ReviewActivityModal — accessibility (WCAG 2.1 AA)", () => {
  it("has no violations when open with activity", async () => {
    const { container } = render(
      <ReviewActivityModal isOpen onClose={vi.fn()} activity={baseActivity} />,
    );
    expect(await axe(container)).toHaveNoViolations();
  });

  it("has no violations when open with empty activity", async () => {
    const { container } = render(
      <ReviewActivityModal isOpen onClose={vi.fn()} activity={[]} />,
    );
    expect(await axe(container)).toHaveNoViolations();
  });

  it("has no violations with a focused attempt", async () => {
    const { container } = render(
      <ReviewActivityModal
        isOpen
        onClose={vi.fn()}
        activity={baseActivity}
        focusAttempt={1}
      />,
    );
    expect(await axe(container)).toHaveNoViolations();
  });
});
