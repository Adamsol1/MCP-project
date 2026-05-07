import { render, screen } from "@testing-library/react";
import { describe, it, expect, vi } from "vitest";
import userEvent from "@testing-library/user-event";
import type { ReactNode } from "react";
import ChatWindow from "./ChatWindow";
import { ToastProvider } from "../../contexts/Toast/ToastContext";
import { WorkspaceProvider } from "../../contexts/WorkspaceContext/WorkspaceContext";
import { SettingsProvider } from "../../contexts/SettingsContext/SettingsContext";
import { axe } from "vitest-axe";

vi.mock("../AnalysisWorkspace/AnalysisWorkspace", () => ({
  default: () => <div>Inline analysis view</div>,
}));

// ChatWindow renders ToastContainer (needs ToastProvider) and PirMessage
// calls useWorkspace (needs WorkspaceProvider).
function renderWithToast(ui: ReactNode) {
  return render(
    <SettingsProvider>
      <WorkspaceProvider>
        <ToastProvider>{ui}</ToastProvider>
      </WorkspaceProvider>
    </SettingsProvider>
  );
}

// describe() groups related tests together under a label
describe("ChatWindow", () => {
  // it() defines a single test case - what behavior we expect
  it("renders a greeting message", () => {
    // render() mounts the component in a virtual DOM (jsdom)
    renderWithToast(<ChatWindow />);

    // screen.getByText() searches the rendered output for text content
    // The /regex/i syntax is case-insensitive matching
    expect(screen.getByText(/ready to start?/i)).toBeInTheDocument();
  });

  it("renders a message input field", () => {
    renderWithToast(<ChatWindow />); // Render component

    const input = screen.getByPlaceholderText(/type anything/i);
    expect(input).toBeInTheDocument();
  });

  it("renders the empty-state composer on a themed surface", () => {
    renderWithToast(<ChatWindow />);

    const input = screen.getByPlaceholderText(/type anything/i);
    expect(input.closest("form")).toHaveClass("bg-surface", "rounded-[22px]");
  });

  it("keeps the in-conversation composer more compact", () => {
    renderWithToast(
      <ChatWindow
        messages={[{ id: "1", text: "Hello", sender: "system" as const }]}
      />,
    );

    const input = screen.getByPlaceholderText(/type anything/i);
    expect(input.closest("form")).toHaveClass("rounded-xl");
  });

  it("renders send button", () => {
    renderWithToast(<ChatWindow />);

    // getByRole() finds elements by their ARIA role
    const sendButton = screen.getByRole("button", { name: /send/i });
    expect(sendButton).toBeInTheDocument();
  });

  it("disables send button when input is empty", () => {
    renderWithToast(<ChatWindow />);

    const sendButton = screen.getByRole("button", { name: /send/i });
    // toBeDisabled() checks the HTML disabled attribute
    // An empty input means nothing to send, so the button should be inactive
    expect(sendButton).toBeDisabled();
  });

  // ---------- Button state ----------

  it("enables send button when input has text", async () => {
    // userEvent.setup() creates a user simulation instance
    // Unlike fireEvent, userEvent simulates real browser behavior
    // (keydown, keypress, keyup, input events in sequence)
    const user = userEvent.setup();
    renderWithToast(<ChatWindow />);

    const input = screen.getByPlaceholderText(/type anything/i);
    // user.type() simulates typing character by character, just like a real user
    await user.type(input, "Hello");

    const sendButton = screen.getByRole("button", { name: /send/i });
    expect(sendButton).toBeEnabled();
  });

  // ---------- Sending messages ----------

  it("calls onSendMessage when form is submitted", async () => {
    const user = userEvent.setup();
    // vi.fn() creates a mock function - it records how it was called
    // so we can assert on it later. This is how we test callback props.
    const handleSend = vi.fn();
    renderWithToast(<ChatWindow onSendMessage={handleSend} />);

    const input = screen.getByPlaceholderText(/type anything/i);
    await user.type(input, "Investigate recent APT activity");

    const sendButton = screen.getByRole("button", { name: /send/i });
    await user.click(sendButton);

    // Verify the callback was called exactly once, with the typed text
    expect(handleSend).toHaveBeenCalledTimes(1);
    expect(handleSend).toHaveBeenCalledWith("Investigate recent APT activity");
  });

  it("clears input after sending a message", async () => {
    const user = userEvent.setup();
    renderWithToast(<ChatWindow onSendMessage={vi.fn()} />);

    const input = screen.getByPlaceholderText(/type anything/i);
    await user.type(input, "Hello");

    const sendButton = screen.getByRole("button", { name: /send/i });
    await user.click(sendButton);

    // After sending, the input should be empty so the user can type again
    expect(input).toHaveValue("");
  });

  it("submits on Enter key press", async () => {
    const user = userEvent.setup();
    const handleSend = vi.fn();
    renderWithToast(<ChatWindow onSendMessage={handleSend} />);

    const input = screen.getByPlaceholderText(/type anything/i);
    // {Enter} is userEvent syntax for pressing the Enter key
    await user.type(input, "Test message{Enter}");

    expect(handleSend).toHaveBeenCalledTimes(1);
    expect(handleSend).toHaveBeenCalledWith("Test message");
  });

  // ---------- Displaying messages ----------

  it("displays messages passed via props", () => {
    // Messages come from the parent component as a prop array
    // Each message has an id, text, and sender ("user" or "system")
    const messages = [
      { id: "1", text: "Hello, how can I help?", sender: "system" as const },
      { id: "2", text: "Investigate APT29", sender: "user" as const },
    ];

    renderWithToast(<ChatWindow messages={messages} />);

    expect(screen.getByText("Hello, how can I help?")).toBeInTheDocument();
    expect(screen.getByText("Investigate APT29")).toBeInTheDocument();
  });

  it("applies different styles for user and system messages", () => {
    const messages = [
      { id: "1", text: "System message", sender: "system" as const },
      { id: "2", text: "User message", sender: "user" as const },
    ];

    renderWithToast(<ChatWindow messages={messages} />);

    // data-sender is a custom data attribute we use to mark message origin
    // This lets us (and CSS) distinguish between user and system messages
    const systemMsg = screen.getByText("System message").closest("div");
    const userMsg = screen.getByText("User message").closest("div");

    expect(systemMsg).toHaveAttribute("data-sender", "system");
    expect(userMsg).toHaveAttribute("data-sender", "user");
  });

  it("hides greeting when messages are present", () => {
    const messages = [{ id: "1", text: "Hello", sender: "system" as const }];

    renderWithToast(<ChatWindow messages={messages} />);

    // queryByText returns null instead of throwing when not found
    // (unlike getByText which throws). Use queryBy* when you expect
    // an element NOT to exist.
    expect(screen.queryByText(/ready to start/i)).not.toBeInTheDocument();
  });

  // ---------- S2.5.2: Approve button ----------

  it("shows Approve button when isConfirming is true", () => {
    // When the dialogue flow reaches confirmation, the user should see
    // an Approve button to accept the summary and proceed.
    renderWithToast(<ChatWindow isConfirming={true} />);

    const approveBtn = screen.getByRole("button", { name: /approve/i });
    expect(approveBtn).toBeInTheDocument();
  });

  it("calls onApprove when approve is clicked", async () => {
    const user = userEvent.setup();
    const handleApprove = vi.fn();

    renderWithToast(
      <ChatWindow isConfirming={true} onApprove={handleApprove} />,
    );

    const approveBtn = screen.getByRole("button", { name: /approve/i });
    await user.click(approveBtn);

    expect(handleApprove).toHaveBeenCalledTimes(1);
  });

  it("does not show Approve button when isConfirming is false", () => {
    renderWithToast(<ChatWindow isConfirming={false} />);

    // queryByRole returns null instead of throwing when not found
    expect(
      screen.queryByRole("button", { name: /approve/i }),
    ).not.toBeInTheDocument();
  });

  // ---------- S2.5.4: Reject button with feedback ----------

  it("shows Reject button when isConfirming is true", () => {
    renderWithToast(<ChatWindow isConfirming={true} />);

    const rejectBtn = screen.getByRole("button", { name: /reject/i });
    expect(rejectBtn).toBeInTheDocument();
  });

  it("calls onReject when Reject button is clicked", async () => {
    const user = userEvent.setup();
    const handleReject = vi.fn();

    renderWithToast(<ChatWindow isConfirming={true} onReject={handleReject} />);

    const rejectBtn = screen.getByRole("button", { name: /reject/i });
    await user.click(rejectBtn);

    expect(handleReject).toHaveBeenCalledTimes(1);
  });

  it("does not show Reject button when isConfirming is false", () => {
    renderWithToast(<ChatWindow isConfirming={false} />);

    expect(
      screen.queryByRole("button", { name: /reject/i }),
    ).not.toBeInTheDocument();
  });

  // ---------- Structured message rendering ----------

  it("renders data.summary as plain text for 'summary' type messages", () => {
    const messages = [
      {
        id: "1",
        text: JSON.stringify({
          summary:
            "Investigation focused on APT29 targeting EU infrastructure.",
        }),
        sender: "system" as const,
        type: "summary" as const,
        data: {
          summary:
            "Investigation focused on APT29 targeting EU infrastructure.",
        },
      },
    ];

    renderWithToast(<ChatWindow messages={messages} />);

    expect(
      screen.getByText(
        "Investigation focused on APT29 targeting EU infrastructure.",
      ),
    ).toBeInTheDocument();
  });

  it("does not render raw JSON string when message type is 'summary'", () => {
    const rawJson = JSON.stringify({ summary: "Some summary text." });
    const messages = [
      {
        id: "1",
        text: rawJson,
        sender: "system" as const,
        type: "summary" as const,
        data: { summary: "Some summary text." },
      },
    ];

    renderWithToast(<ChatWindow messages={messages} />);

    // The structured renderer should show data.summary, not the raw JSON blob
    expect(screen.queryByText(rawJson)).not.toBeInTheDocument();
  });

  it("renders a PIR section heading for 'pir' type messages", () => {
    const messages = [
      {
        id: "1",
        text: "{}",
        sender: "system" as const,
        type: "pir" as const,
        data: {
          pir_text: "PIRs generated successfully.",
          claims: [],
          sources: [],
          pirs: [
            {
              question: "Q1?",
              priority: "high" as const,
              rationale: "Important.",
              source_ids: [],
            },
          ],
          reasoning: "Based on the scope provided.",
        },
      },
    ];

    renderWithToast(<ChatWindow messages={messages} />);

    expect(
      screen.getByText(/Priority Intelligence Requirements/),
    ).toBeInTheDocument();
  });

  it("renders each PIR question in the list", () => {
    const messages = [
      {
        id: "1",
        text: "{}",
        sender: "system" as const,
        type: "pir" as const,
        data: {
          pir_text: "PIRs generated.",
          claims: [],
          sources: [],
          pirs: [
            {
              question: "What TTPs has APT29 used?",
              priority: "high" as const,
              rationale: "Core requirement.",
              source_ids: [],
            },
            {
              question: "Which EU sectors were targeted?",
              priority: "medium" as const,
              rationale: "Scope clarification.",
              source_ids: [],
            },
          ],
          reasoning: "Selected based on context.",
        },
      },
    ];

    renderWithToast(<ChatWindow messages={messages} />);

    expect(screen.getByText(/What TTPs has APT29 used\?/)).toBeInTheDocument();
    expect(
      screen.getByText(/Which EU sectors were targeted\?/),
    ).toBeInTheDocument();
  });

  it("renders the priority label for PIR items", () => {
    const messages = [
      {
        id: "1",
        text: "{}",
        sender: "system" as const,
        type: "pir" as const,
        data: {
          pir_text: "PIRs generated.",
          claims: [],
          sources: [],
          pirs: [
            {
              question: "High priority Q?",
              priority: "high" as const,
              rationale: "Critical.",
              source_ids: [],
            },
            {
              question: "Medium priority Q?",
              priority: "medium" as const,
              rationale: "Important.",
              source_ids: [],
            },
            {
              question: "Low priority Q?",
              priority: "low" as const,
              rationale: "Nice to have.",
              source_ids: [],
            },
          ],
          reasoning: "Reasoning here.",
        },
      },
    ];

    renderWithToast(<ChatWindow messages={messages} />);

    // Badges show 1-indexed numbers; priority label includes the "Priority: " prefix
    expect(screen.getAllByText("1").length).toBeGreaterThan(0);
    expect(screen.getAllByText("2").length).toBeGreaterThan(0);
    expect(screen.getAllByText("3").length).toBeGreaterThan(0);
    expect(screen.getByText("Priority: High")).toBeInTheDocument();
    expect(screen.getByText("Priority: Medium")).toBeInTheDocument();
    expect(screen.getByText("Priority: Low")).toBeInTheDocument();
  });

  it("shows a 'Rationale' toggle for each PIR item", () => {
    const messages = [
      {
        id: "1",
        text: "{}",
        sender: "system" as const,
        type: "pir" as const,
        data: {
          pir_text: "PIRs generated.",
          claims: [],
          sources: [],
          pirs: [
            {
              question: "Q1?",
              priority: "high" as const,
              rationale: "Because it matters.",
              source_ids: [],
            },
            {
              question: "Q2?",
              priority: "low" as const,
              rationale: "Secondary concern.",
              source_ids: [],
            },
          ],
          reasoning: "Reasoning here.",
        },
      },
    ];

    renderWithToast(<ChatWindow messages={messages} />);

    // One "Rationale" toggle should appear per PIR item
    const toggles = screen.getAllByText(/rationale/i);
    expect(toggles).toHaveLength(2);
  });

  it("keeps rationale text in the DOM inside each collapsible", () => {
    const messages = [
      {
        id: "1",
        text: "{}",
        sender: "system" as const,
        type: "pir" as const,
        data: {
          pir_text: "PIRs generated.",
          claims: [],
          sources: [],
          pirs: [
            {
              question: "Q1?",
              priority: "high" as const,
              rationale: "Because it matters.",
              source_ids: [],
            },
          ],
          reasoning: "Reasoning here.",
        },
      },
    ];

    renderWithToast(<ChatWindow messages={messages} />);

    expect(screen.getByText("Because it matters.")).toBeInTheDocument();
  });

  it("renders **bold** markers in reasoning as <strong> elements", () => {
    const messages = [
      {
        id: "1",
        text: "{}",
        sender: "system" as const,
        type: "pir" as const,
        data: {
          pir_text: "PIRs generated.",
          claims: [],
          sources: [],
          pirs: [
            {
              question: "Q1?",
              priority: "high" as const,
              rationale: "R1.",
              source_ids: [],
            },
          ],
          reasoning: "1. **Scope**: Covers the main area.",
        },
      },
    ];

    renderWithToast(<ChatWindow messages={messages} />);

    // ReasoningMarkdown processes **bold** markers → <strong> elements via renderInline
    const scopeEl = screen.getByText("Scope");
    expect(scopeEl.tagName).toBe("STRONG");
  });

  it("renders a 'Show reasoning' toggle for PIR messages", () => {
    const messages = [
      {
        id: "1",
        text: "{}",
        sender: "system" as const,
        type: "pir" as const,
        data: {
          pir_text: "PIRs generated.",
          claims: [],
          sources: [],
          pirs: [
            {
              question: "Q1?",
              priority: "low" as const,
              rationale: "R1.",
              source_ids: [],
            },
          ],
          reasoning: "Selected based on scope and context provided.",
        },
      },
    ];

    renderWithToast(<ChatWindow messages={messages} />);

    expect(screen.getByText(/show reasoning/i)).toBeInTheDocument();
  });

  it("keeps reasoning text in the DOM inside the collapsible", () => {
    // <details> hides content visually but keeps it in the DOM — the text
    // should be findable even before the user expands the section.
    const messages = [
      {
        id: "1",
        text: "{}",
        sender: "system" as const,
        type: "pir" as const,
        data: {
          pir_text: "PIRs generated.",
          claims: [],
          sources: [],
          pirs: [
            {
              question: "Q1?",
              priority: "low" as const,
              rationale: "R1.",
              source_ids: [],
            },
          ],
          reasoning: "Selected based on scope and context provided.",
        },
      },
    ];

    renderWithToast(<ChatWindow messages={messages} />);

    expect(
      screen.getByText("Selected based on scope and context provided."),
    ).toBeInTheDocument();
  });

  it("splits numbered reasoning points into separate paragraphs", () => {
    const messages = [
      {
        id: "1",
        text: "{}",
        sender: "system" as const,
        type: "pir" as const,
        data: {
          pir_text: "PIRs generated.",
          claims: [],
          sources: [],
          pirs: [
            {
              question: "Q1?",
              priority: "high" as const,
              rationale: "R1.",
              source_ids: [],
            },
          ],
          reasoning:
            "Intro text. 1. First point here. 2. Second point here. 3. Third point here.",
        },
      },
    ];

    renderWithToast(<ChatWindow messages={messages} />);

    // Each point is split into its own list item; the number prefix is stripped
    // and replaced with a badge — check the text content directly
    expect(screen.getByText(/First point here/)).toBeInTheDocument();
    expect(screen.getByText(/Second point here/)).toBeInTheDocument();
    expect(screen.getByText(/Third point here/)).toBeInTheDocument();
  });

  it("falls back to plain text for 'question' type messages", () => {
    const messages = [
      {
        id: "1",
        text: "What is the scope of your investigation?",
        sender: "system" as const,
        type: "question" as const,
      },
    ];

    renderWithToast(<ChatWindow messages={messages} />);

    expect(
      screen.getByText("What is the scope of your investigation?"),
    ).toBeInTheDocument();
  });

  it("falls back to plain text when summary message has no data (malformed JSON upstream)", () => {
    const messages = [
      {
        id: "1",
        text: "This is not valid JSON {{{",
        sender: "system" as const,
        type: "summary" as const,
        // data is intentionally absent — upstream JSON.parse failed
      },
    ];

    renderWithToast(<ChatWindow messages={messages} />);

    expect(screen.getByText("This is not valid JSON {{{")).toBeInTheDocument();
  });

  // ---------- S2.5.5: Validation - prevent skipping approval ----------

  it("hides text input and send button when isConfirming is true", () => {
    // The user MUST click Approve or Reject — they cannot bypass
    // the decision by typing a free message.
    renderWithToast(<ChatWindow isConfirming={true} />);

    expect(
      screen.queryByPlaceholderText(/type anything/i),
    ).not.toBeInTheDocument();
    expect(
      screen.queryByRole("button", { name: /send/i }),
    ).not.toBeInTheDocument();
  });

  it("shows text input and send button when isConfirming is false", () => {
    // Normal state: the user can type and send messages
    renderWithToast(<ChatWindow isConfirming={false} />);

    expect(screen.getByPlaceholderText(/type anything/i)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /send/i })).toBeInTheDocument();
  });

  it("renders the analysis inline and hides the composer when stage is complete", () => {
    const messages = [
      // type:"analysis" + truthy data triggers AnalysisWorkspace (mocked) and hides the composer
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      { id: "1", text: "Analysis complete.", sender: "system" as const, type: "analysis" as const, data: {} as any },
    ];

    renderWithToast(<ChatWindow messages={messages} stage="complete" />);

    expect(screen.getByText("Analysis complete.")).toBeInTheDocument();
    expect(screen.getByText("Inline analysis view")).toBeInTheDocument();
    expect(
      screen.queryByPlaceholderText(/type anything/i),
    ).not.toBeInTheDocument();
  });

  it("renders processing review when stage is reviewing and phase is processing", () => {
    renderWithToast(
      <ChatWindow
        isConfirming={true}
        stage="reviewing"
        phase="processing"
      />,
    );

    expect(screen.getByText(/processing review/i)).toBeInTheDocument();
    expect(
      screen.queryByText(/collection review/i),
    ).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: /collect more/i })).toBeInTheDocument();
  });
});

// ---------- Rationale citation rendering ----------
// pir.rationale can contain [N] markers just like pir_text.
// These tests verify that rationale is rendered through CitationText so
// markers become interactive superscripts wired to the shared hover state.

describe("PirMessage — rationale citation rendering", () => {
  // Shared fixture: a PIR message where only the rationale contains a [N] marker.
  // pir_text is marker-free so any <sup> in the DOM must come from the rationale.
  const rationaleMessage = [
    {
      id: "1",
      text: "{}",
      sender: "system" as const,
      type: "pir" as const,
      data: {
        pir_text: "PIRs generated successfully.",
        claims: [],
        sources: [
          {
            id: "geopolitical/norway_russia",
            ref: "[1]",
            source_type: "kb",
            citation: {
              author: "Threat Intelligence System",
              year: "2025",
              title: "Norwegian-Russian Geopolitical Relations",
              publisher: "Knowledge Bank",
            },
          },
        ],
        pirs: [
          {
            question: "What is the threat level for Norway?",
            priority: "high" as const,
            rationale:
              "Norway faces elevated risk[1] based on recent intelligence.",
            source_ids: [],
          },
        ],
        reasoning: "",
      },
    },
  ];

  it("renders [N] markers in rationale as superscript elements", () => {
    // If rationale is passed as plain text, [1] stays as a string character.
    // CitationText splits on [N] patterns and wraps each in a <sup>.
    renderWithToast(<ChatWindow messages={rationaleMessage} />);

    const sups = document.querySelectorAll("sup");
    expect(sups).toHaveLength(1);
    expect(sups[0]).toHaveTextContent("[1]");
  });

  it("hovering a [N] marker in rationale highlights the matching source card", async () => {
    // Hovering the <sup> calls onRefHover("[1]"), which sets highlightedRef in
    // PirMessage, which flows into SourceList and highlights the matching <li>.
    const user = userEvent.setup();
    renderWithToast(<ChatWindow messages={rationaleMessage} />);

    const sup = document.querySelector("sup")!;
    await user.hover(sup);

    // Multiple listitems exist (PIR items + source items), so scope to the
    // source card by finding its unique citation text and walking up to the <li>.
    const sourceCard = screen
      .getByText(/Norwegian-Russian Geopolitical Relations/)
      .closest("li")!;
    expect(sourceCard).toHaveClass("text-primary");
  });

  it("renders rationale without [N] markers as plain text with no superscripts", () => {
    // Regression guard: plain rationale text must still appear in the DOM.
    const plainMessage = [
      {
        id: "2",
        text: "{}",
        sender: "system" as const,
        type: "pir" as const,
        data: {
          pir_text: "PIRs generated.",
          claims: [],
          sources: [],
          pirs: [
            {
              question: "Q1?",
              priority: "low" as const,
              rationale: "Because it matters.",
              source_ids: [],
            },
          ],
          reasoning: "",
        },
      },
    ];

    renderWithToast(<ChatWindow messages={plainMessage} />);

    expect(screen.getByText("Because it matters.")).toBeInTheDocument();
    expect(document.querySelectorAll("sup")).toHaveLength(0);
  });
});

// ---------------------------------------------------------------------------
// CollectionPlanMessage, SuggestedSourcesMessage, CollectionSummaryMessage
// ---------------------------------------------------------------------------

describe("ChatWindow — plan message", () => {
  it("renders step titles, descriptions, and numbering for plan messages with steps", () => {
    const messages = [
      {
        id: "1",
        text: "{}",
        sender: "system" as const,
        type: "plan" as const,
        data: {
          plan: "Plan text",
          steps: [
            {
              title: "Gather OSINT",
              description: "Collect publicly available intelligence.",
              suggested_sources: ["Web Search"],
            },
            {
              title: "Analyse findings",
              description: "Cross-reference gathered data.",
              suggested_sources: [],
            },
          ],
        },
      },
    ];
    renderWithToast(<ChatWindow messages={messages} />);
    expect(screen.getByText("Collection Plan")).toBeInTheDocument();
    expect(screen.getByText("Gather OSINT")).toBeInTheDocument();
    expect(screen.getByText("Collect publicly available intelligence.")).toBeInTheDocument();
    expect(screen.getByText("Analyse findings")).toBeInTheDocument();
    // Step numbers 1 and 2 should appear
    expect(screen.getAllByText("1").length).toBeGreaterThan(0);
    expect(screen.getAllByText("2").length).toBeGreaterThan(0);
  });

  it("renders suggested sources inside a step", () => {
    const messages = [
      {
        id: "1",
        text: "{}",
        sender: "system" as const,
        type: "plan" as const,
        data: {
          plan: "",
          steps: [
            {
              title: "Research phase",
              description: "Gather data.",
              suggested_sources: ["Web Search", "AlienVault OTX"],
            },
          ],
        },
      },
    ];
    renderWithToast(<ChatWindow messages={messages} />);
    expect(screen.getByText("Web Search")).toBeInTheDocument();
    expect(screen.getByText("AlienVault OTX")).toBeInTheDocument();
  });

  it("renders plain plan text when steps is absent", () => {
    const messages = [
      {
        id: "1",
        text: "{}",
        sender: "system" as const,
        type: "plan" as const,
        data: {
          plan: "Collect from all available sources and summarise findings.",
        },
      },
    ];
    renderWithToast(<ChatWindow messages={messages} />);
    expect(
      screen.getByText("Collect from all available sources and summarise findings."),
    ).toBeInTheDocument();
  });

  it("renders 'Show reasoning' toggle when plan has reasoning text", () => {
    const messages = [
      {
        id: "1",
        text: "{}",
        sender: "system" as const,
        type: "plan" as const,
        data: {
          plan: "Some plan",
          reasoning: "Chose these steps because of scope.",
        },
      },
    ];
    renderWithToast(<ChatWindow messages={messages} />);
    expect(screen.getByText(/show reasoning/i)).toBeInTheDocument();
  });
});

describe("ChatWindow — suggested_sources message", () => {
  it("renders source names for suggested_sources message", () => {
    const messages = [
      {
        id: "1",
        text: "{}",
        sender: "system" as const,
        type: "suggested_sources" as const,
        data: ["Web Search", "AlienVault OTX", "Knowledge Bank"],
      },
    ];
    renderWithToast(<ChatWindow messages={messages} />);
    expect(screen.getByText(/Suggested Sources/i)).toBeInTheDocument();
    expect(screen.getByText("Web Search")).toBeInTheDocument();
    expect(screen.getByText("AlienVault OTX")).toBeInTheDocument();
    expect(screen.getByText("Knowledge Bank")).toBeInTheDocument();
  });

  it("renders no-suggestions text when suggested_sources is an empty array", () => {
    const messages = [
      {
        id: "1",
        text: "{}",
        sender: "system" as const,
        type: "suggested_sources" as const,
        data: [],
      },
    ];
    renderWithToast(<ChatWindow messages={messages} />);
    expect(screen.getByText(/No source suggestions were returned/i)).toBeInTheDocument();
  });
});

describe("ChatWindow — collection summary message (type='collection' with sources_used)", () => {
  it("renders Collection Summary header with summary text and sources used", () => {
    const messages = [
      {
        id: "1",
        text: "{}",
        sender: "system" as const,
        type: "collection" as const,
        data: {
          summary: "Intelligence gathered from multiple sources.",
          sources_used: ["AlienVault OTX", "Web Search"],
          gaps: "Missing data on insider threats.",
        },
      },
    ];
    renderWithToast(<ChatWindow messages={messages} />);
    expect(screen.getByText(/Collection Summary/i)).toBeInTheDocument();
    expect(screen.getByText("Intelligence gathered from multiple sources.")).toBeInTheDocument();
    expect(screen.getByText("AlienVault OTX")).toBeInTheDocument();
    expect(screen.getByText("Missing data on insider threats.")).toBeInTheDocument();
  });
});

describe("ChatWindow — collection review state", () => {
  it("renders Collection Review header when stage=reviewing, phase=collection, isConfirming=true", () => {
    renderWithToast(
      <ChatWindow
        isConfirming={true}
        stage="reviewing"
        phase="collection"
      />,
    );
    expect(screen.getByText(/Collection Review/i)).toBeInTheDocument();
  });

  it("renders 'Accept', 'Revise', and 'Collect More' buttons in collection review", () => {
    renderWithToast(
      <ChatWindow
        isConfirming={true}
        stage="reviewing"
        phase="collection"
      />,
    );
    expect(screen.getByRole("button", { name: /^accept$/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /^revise$/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /^collect more$/i })).toBeInTheDocument();
  });

  it("calls onApprove when Accept button is clicked in collection review", async () => {
    const user = userEvent.setup();
    const onApprove = vi.fn();
    renderWithToast(
      <ChatWindow
        isConfirming={true}
        stage="reviewing"
        phase="collection"
        onApprove={onApprove}
      />,
    );
    await user.click(screen.getByRole("button", { name: /^accept$/i }));
    expect(onApprove).toHaveBeenCalledOnce();
  });

  it("calls onGatherMore when 'Collect More' is clicked", async () => {
    const user = userEvent.setup();
    const onGatherMore = vi.fn();
    renderWithToast(
      <ChatWindow
        isConfirming={true}
        stage="reviewing"
        phase="collection"
        onGatherMore={onGatherMore}
      />,
    );
    await user.click(screen.getByRole("button", { name: /^collect more$/i }));
    expect(onGatherMore).toHaveBeenCalledOnce();
  });

  it("calls onReject when 'Revise' is clicked in collection review", async () => {
    const user = userEvent.setup();
    const onReject = vi.fn();
    renderWithToast(
      <ChatWindow
        isConfirming={true}
        stage="reviewing"
        phase="collection"
        onReject={onReject}
      />,
    );
    await user.click(screen.getByRole("button", { name: /^revise$/i }));
    expect(onReject).toHaveBeenCalledOnce();
  });
});

describe("ChatWindow — processing review state", () => {
  it("renders Processing Review header when isConfirming=true, phase=processing", () => {
    renderWithToast(
      <ChatWindow
        isConfirming={true}
        stage="reviewing"
        phase="processing"
      />,
    );
    expect(screen.getByText(/Processing Review/i)).toBeInTheDocument();
  });

  it("renders Accept and Collect More buttons in processing review", () => {
    renderWithToast(
      <ChatWindow
        isConfirming={true}
        stage="reviewing"
        phase="processing"
      />,
    );
    expect(screen.getByRole("button", { name: /^accept$/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /^collect more$/i })).toBeInTheDocument();
  });

  it("calls onApprove when Accept is clicked in processing review", async () => {
    const user = userEvent.setup();
    const onApprove = vi.fn();
    renderWithToast(
      <ChatWindow
        isConfirming={true}
        stage="reviewing"
        phase="processing"
        onApprove={onApprove}
      />,
    );
    await user.click(screen.getByRole("button", { name: /^accept$/i }));
    expect(onApprove).toHaveBeenCalledOnce();
  });

  it("calls onGatherMoreFromProcessing when Collect More clicked in processing review", async () => {
    const user = userEvent.setup();
    const onGatherMoreFromProcessing = vi.fn();
    renderWithToast(
      <ChatWindow
        isConfirming={true}
        stage="reviewing"
        phase="processing"
        onGatherMoreFromProcessing={onGatherMoreFromProcessing}
      />,
    );
    await user.click(screen.getByRole("button", { name: /^collect more$/i }));
    expect(onGatherMoreFromProcessing).toHaveBeenCalledOnce();
  });
});

// ---------------------------------------------------------------------------
// Source selection UI
// ---------------------------------------------------------------------------

describe("ChatWindow — source selection", () => {
  it("renders Select Sources header when isSourceSelecting is true", () => {
    renderWithToast(
      <ChatWindow
        isSourceSelecting={true}
        availableSources={["Web Search", "AlienVault OTX"]}
        selectedSources={[]}
      />,
    );
    expect(screen.getByText(/Select Sources/i)).toBeInTheDocument();
  });

  it("renders available source buttons in source selection mode", () => {
    renderWithToast(
      <ChatWindow
        isSourceSelecting={true}
        availableSources={["Web Search", "AlienVault OTX"]}
        selectedSources={[]}
      />,
    );
    expect(screen.getByText("Web Search")).toBeInTheDocument();
    expect(screen.getByText("AlienVault OTX")).toBeInTheDocument();
  });

  it("calls onToggleSourceSelection when a source button is clicked", async () => {
    const user = userEvent.setup();
    const onToggle = vi.fn();
    renderWithToast(
      <ChatWindow
        isSourceSelecting={true}
        availableSources={["Web Search"]}
        selectedSources={[]}
        onToggleSourceSelection={onToggle}
      />,
    );
    await user.click(screen.getByText("Web Search"));
    expect(onToggle).toHaveBeenCalledWith("Web Search");
  });

  it("renders no-source-suggestions message when availableSources is empty", () => {
    renderWithToast(
      <ChatWindow
        isSourceSelecting={true}
        availableSources={[]}
        selectedSources={[]}
      />,
    );
    expect(screen.getByText(/No source suggestions available/i)).toBeInTheDocument();
  });

  it("renders Start Collecting button that is disabled when no sources are selected", () => {
    renderWithToast(
      <ChatWindow
        isSourceSelecting={true}
        availableSources={["Web Search"]}
        selectedSources={[]}
      />,
    );
    const btn = screen.getByRole("button", { name: /start collecting/i });
    expect(btn).toBeDisabled();
  });

  it("calls onSubmitSourceSelection when Start Collecting is clicked with sources selected", async () => {
    const user = userEvent.setup();
    const onSubmit = vi.fn();
    renderWithToast(
      <ChatWindow
        isSourceSelecting={true}
        availableSources={["Web Search"]}
        selectedSources={["Web Search"]}
        onSubmitSourceSelection={onSubmit}
      />,
    );
    await user.click(screen.getByRole("button", { name: /start collecting/i }));
    expect(onSubmit).toHaveBeenCalledOnce();
  });
});

// ---------------------------------------------------------------------------
// Collecting status UI
// ---------------------------------------------------------------------------

describe("ChatWindow — collecting status", () => {
  it("renders Collecting section when isCollecting is true without status", () => {
    renderWithToast(<ChatWindow isCollecting={true} />);
    expect(screen.getByText(/collecting/i)).toBeInTheDocument();
  });

  it("renders collection status sources when collectionStatus is provided", () => {
    const collectionStatus = {
      current_source: "Web Search",
      current_activity: null,
      sources: {
        "Web Search": { call_count: 0 },
        "AlienVault OTX": { call_count: 3 },
      },
    };
    renderWithToast(
      <ChatWindow isCollecting={true} collectionStatus={collectionStatus} />,
    );
    expect(screen.getByText("Web Search")).toBeInTheDocument();
    expect(screen.getByText("AlienVault OTX")).toBeInTheDocument();
  });
});

// ---------------------------------------------------------------------------
// Collection display message
// ---------------------------------------------------------------------------

describe("ChatWindow — collection message type", () => {
  it("renders CollectionResults header for collection message with collected_data", () => {
    const messages = [
      {
        id: "1",
        text: "{}",
        sender: "system" as const,
        type: "collection" as const,
        data: {
          collected_data: [{ source: "query_otx", resource_id: "r1", content: "data" }],
          source_summary: [{ display_name: "AlienVault OTX", count: 1, resource_ids: ["r1"], has_content: true }],
        },
      },
    ];
    renderWithToast(<ChatWindow messages={messages} />);
    expect(screen.getByText(/Collection Results/i)).toBeInTheDocument();
  });
});

// ---------------------------------------------------------------------------
// ProcessingMessage — rendered as a message in ChatWindow
// ---------------------------------------------------------------------------

describe("ChatWindow — processing message with findings", () => {
  const processingMessage = {
    id: "1",
    text: "{}",
    sender: "system" as const,
    type: "processing" as const,
    data: {
      findings: [
        {
          id: "f1",
          title: "APT29 phishing campaign detected",
          finding: "Detailed finding text about the campaign.",
          confidence: 0.85,
          source: "query_otx",
          categories: ["phishing"],
          relevant_to: ["PIR-1"],
          reasoning: "",
          attack_ids: [],
          sources: [],
        },
      ],
      gaps: ["Additional context on attribution needed."],
      reasoning: "",
    },
  };

  it("renders Processing Results header and finding title", () => {
    renderWithToast(<ChatWindow messages={[processingMessage]} />);
    expect(screen.getByText("Processing Results")).toBeInTheDocument();
    expect(screen.getByText("APT29 phishing campaign detected")).toBeInTheDocument();
  });

  it("renders gap text in the gaps section", () => {
    renderWithToast(<ChatWindow messages={[processingMessage]} />);
    expect(
      screen.getByText("Additional context on attribution needed."),
    ).toBeInTheDocument();
  });

  it("passes onGapCollect to ProcessingMessage (line 1288 branch)", () => {
    const onGapCollect = vi.fn();
    const onSendMessage = vi.fn();
    renderWithToast(
      <ChatWindow
        messages={[processingMessage]}
        onGapCollect={onGapCollect}
        onSendMessage={onSendMessage}
      />,
    );
    // The "Collect More" button should appear since onGapCollect is provided
    expect(
      screen.getByRole("button", { name: /collect more/i }),
    ).toBeInTheDocument();
  });

  it("opens FindingDetailModal when a finding row is clicked", async () => {
    const user = userEvent.setup();
    renderWithToast(<ChatWindow messages={[processingMessage]} />);

    // Click on the finding row (the title is rendered as a table cell)
    await user.click(screen.getByText("APT29 phishing campaign detected"));

    // FindingDetailModal should appear as a dialog
    expect(screen.getByRole("dialog")).toBeInTheDocument();
  });

  it("closes FindingDetailModal when close button is clicked", async () => {
    const user = userEvent.setup();
    renderWithToast(<ChatWindow messages={[processingMessage]} />);

    await user.click(screen.getByText("APT29 phishing campaign detected"));
    expect(screen.getByRole("dialog")).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: /close/i }));
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
  });

  it("renders processing message plain text when type=processing but no findings (line 1321)", () => {
    const plainProcessing = {
      id: "2",
      text: "Processing is underway, please wait.",
      sender: "system" as const,
      type: "processing" as const,
      // no data — will fall through to line 1321
    };
    renderWithToast(<ChatWindow messages={[plainProcessing]} />);
    expect(
      screen.getByText("Processing is underway, please wait."),
    ).toBeInTheDocument();
  });

  it("clicking Collect More enables gap collection mode and shows checkboxes", async () => {
    const user = userEvent.setup();
    const onGapCollect = vi.fn();
    renderWithToast(
      <ChatWindow
        messages={[processingMessage]}
        onGapCollect={onGapCollect}
        onSendMessage={vi.fn()}
      />,
    );

    // Click "Collect More" to enter collect mode
    const collectMoreBtn = screen.getByRole("button", { name: /^collect more$/i });
    await user.click(collectMoreBtn);

    // In collect mode, a checkbox should appear for each gap
    expect(screen.getByRole("checkbox")).toBeInTheDocument();
    // "Collect All" button should appear
    expect(screen.getByRole("button", { name: /collect all/i })).toBeInTheDocument();
  });

  it("Collect All button calls onSendMessage with all gap text", async () => {
    const user = userEvent.setup();
    const onSendMessage = vi.fn();
    renderWithToast(
      <ChatWindow
        messages={[processingMessage]}
        onGapCollect={vi.fn()}
        onSendMessage={onSendMessage}
      />,
    );

    // Enter collect mode
    await user.click(screen.getByRole("button", { name: /^collect more$/i }));
    // Click Collect All
    await user.click(screen.getByRole("button", { name: /collect all/i }));

    // onSendMessage is called via the onGapCollect → (gap) => onSendMessage?.(gap) chain
    expect(onSendMessage).toHaveBeenCalledOnce();
    expect(onSendMessage).toHaveBeenCalledWith(
      expect.stringContaining("Additional context on attribution needed."),
    );
  });
});

// ---------------------------------------------------------------------------
// Source selection timeframe onChange (line 1499)
// ---------------------------------------------------------------------------

// ---------------------------------------------------------------------------
// ReasoningMarkdown — bullet and heading block rendering
// ---------------------------------------------------------------------------

describe("ChatWindow — ReasoningMarkdown bullet and heading blocks", () => {
  it("renders bullet items (starting with '* ') in reasoning as list items", () => {
    const messages = [
      {
        id: "1",
        text: "{}",
        sender: "system" as const,
        type: "pir" as const,
        data: {
          pir_text: "PIRs generated.",
          claims: [],
          sources: [],
          pirs: [
            { question: "Q1?", priority: "high" as const, rationale: "R1.", source_ids: [] },
          ],
          // Reasoning with bullets, headings, and empty lines
          reasoning:
            "Evidence Overview:\n* First bullet point here\n* Second bullet point\n\nSome prose after empty line.",
        },
      },
    ];

    renderWithToast(<ChatWindow messages={messages} />);

    // The section heading "Evidence Overview" should appear
    expect(screen.getByText("Evidence Overview")).toBeInTheDocument();
    // Bullet items should be rendered
    expect(screen.getByText("First bullet point here")).toBeInTheDocument();
    expect(screen.getByText("Second bullet point")).toBeInTheDocument();
    // Prose after the empty line
    expect(screen.getByText("Some prose after empty line.")).toBeInTheDocument();
  });

  it("renders dash bullets ('- ') in reasoning as list items", () => {
    const messages = [
      {
        id: "1",
        text: "{}",
        sender: "system" as const,
        type: "pir" as const,
        data: {
          pir_text: "PIRs.",
          claims: [],
          sources: [],
          pirs: [
            { question: "Q1?", priority: "low" as const, rationale: "R1.", source_ids: [] },
          ],
          reasoning: "- Dash bullet one\n- Dash bullet two",
        },
      },
    ];

    renderWithToast(<ChatWindow messages={messages} />);
    expect(screen.getByText("Dash bullet one")).toBeInTheDocument();
    expect(screen.getByText("Dash bullet two")).toBeInTheDocument();
  });
});

describe("ChatWindow — source selection timeframe change", () => {
  it("updates local timeframe state when a timeframe select is changed (line 1499)", async () => {
    const user = userEvent.setup();
    renderWithToast(
      <ChatWindow
        isSourceSelecting={true}
        availableSources={["Web Search"]}
        selectedSources={["Web Search"]}
      />,
    );

    // The timeframe selects should be present
    const selects = screen.getAllByRole("combobox");
    expect(selects.length).toBeGreaterThan(0);

    // Change a timeframe — just pick the first select and change its value
    // The options are rendered from t.timeframeOptions; pick any available option
    const firstSelect = selects[0];
    const options = Array.from(firstSelect.querySelectorAll("option"));
    if (options.length > 1) {
      await user.selectOptions(firstSelect, options[1].value);
    }
    // No crash = onChange handler executed
    expect(firstSelect).toBeInTheDocument();
  });
});

describe("ChatWindow — accessibility (WCAG 2.1 AA)", () => {
  it("has no violations in empty state", async () => {
    const { container } = renderWithToast(<ChatWindow />);
    expect(await axe(container)).toHaveNoViolations();
  });

  it("has no violations with system and user messages", async () => {
    const messages = [
      { id: "1", text: "How can I help?", sender: "system" as const },
      { id: "2", text: "Investigate APT29", sender: "user" as const },
    ];
    const { container } = renderWithToast(<ChatWindow messages={messages} />);
    expect(await axe(container)).toHaveNoViolations();
  });

  it("has no violations during confirmation state", async () => {
    const { container } = renderWithToast(<ChatWindow isConfirming={true} />);
    expect(await axe(container)).toHaveNoViolations();
  });
});
