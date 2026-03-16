import { render, screen } from "@testing-library/react";
import { describe, it, expect, vi } from "vitest";
import userEvent from "@testing-library/user-event";
import type { ReactNode } from "react";
import ChatWindow from "./ChatWindow";
import { ToastProvider } from "../../contexts/Toast/ToastContext";
import { WorkspaceProvider } from "../../contexts/WorkspaceContext/WorkspaceContext";

// ChatWindow renders ToastContainer (needs ToastProvider) and PirMessage
// calls useWorkspace (needs WorkspaceProvider).
function renderWithToast(ui: ReactNode) {
  return render(
    <WorkspaceProvider>
      <ToastProvider>{ui}</ToastProvider>
    </WorkspaceProvider>
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

    const input = screen.getByPlaceholderText(/ask anything/i);
    expect(input).toBeInTheDocument();
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

    const input = screen.getByPlaceholderText(/ask anything/i);
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

    const input = screen.getByPlaceholderText(/ask anything/i);
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

    const input = screen.getByPlaceholderText(/ask anything/i);
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

    const input = screen.getByPlaceholderText(/ask anything/i);
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

    expect(screen.getByText(/1\. High/)).toBeInTheDocument();
    expect(screen.getByText(/2\. Medium/)).toBeInTheDocument();
    expect(screen.getByText(/3\. Low/)).toBeInTheDocument();
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

    const boldEl = screen.getByText("Scope");
    expect(boldEl.tagName).toBe("STRONG");
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

    // Each numbered point should appear as its own element in the DOM
    expect(screen.getByText(/1\. First point here/)).toBeInTheDocument();
    expect(screen.getByText(/2\. Second point here/)).toBeInTheDocument();
    expect(screen.getByText(/3\. Third point here/)).toBeInTheDocument();
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
      screen.queryByPlaceholderText(/ask anything/i),
    ).not.toBeInTheDocument();
    expect(
      screen.queryByRole("button", { name: /send/i }),
    ).not.toBeInTheDocument();
  });

  it("shows text input and send button when isConfirming is false", () => {
    // Normal state: the user can type and send messages
    renderWithToast(<ChatWindow isConfirming={false} />);

    expect(screen.getByPlaceholderText(/ask anything/i)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /send/i })).toBeInTheDocument();
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
              publisher: "Internal Knowledge Bank",
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
