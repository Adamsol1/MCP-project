import { render, screen } from "@testing-library/react";
import { describe, it, expect, vi } from "vitest";
import userEvent from "@testing-library/user-event";
import ChatWindow from "./ChatWindow";

// describe() groups related tests together under a label
describe("ChatWindow", () => {
  // it() defines a single test case - what behavior we expect
  it("renders a greeting message", () => {
    // render() mounts the component in a virtual DOM (jsdom)
    render(<ChatWindow />);

    // screen.getByText() searches the rendered output for text content
    // The /regex/i syntax is case-insensitive matching
    expect(screen.getByText(/ready to start?/i)).toBeInTheDocument();
  });

  it("renders a message input field", () => {
    render(<ChatWindow />); // Render component

    const input = screen.getByPlaceholderText(/ask anything/i);
    expect(input).toBeInTheDocument();
  });

  it("renders send button", () => {
    render(<ChatWindow />);

    // getByRole() finds elements by their ARIA role
    const sendButton = screen.getByRole("button", { name: /send/i });
    expect(sendButton).toBeInTheDocument();
  });

  it("disables send button when input is empty", () => {
    render(<ChatWindow />);

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
    render(<ChatWindow />);

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
    render(<ChatWindow onSendMessage={handleSend} />);

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
    render(<ChatWindow onSendMessage={vi.fn()} />);

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
    render(<ChatWindow onSendMessage={handleSend} />);

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

    render(<ChatWindow messages={messages} />);

    expect(screen.getByText("Hello, how can I help?")).toBeInTheDocument();
    expect(screen.getByText("Investigate APT29")).toBeInTheDocument();
  });

  it("applies different styles for user and system messages", () => {
    const messages = [
      { id: "1", text: "System message", sender: "system" as const },
      { id: "2", text: "User message", sender: "user" as const },
    ];

    render(<ChatWindow messages={messages} />);

    // data-sender is a custom data attribute we use to mark message origin
    // This lets us (and CSS) distinguish between user and system messages
    const systemMsg = screen.getByText("System message").closest("div");
    const userMsg = screen.getByText("User message").closest("div");

    expect(systemMsg).toHaveAttribute("data-sender", "system");
    expect(userMsg).toHaveAttribute("data-sender", "user");
  });

  it("hides greeting when messages are present", () => {
    const messages = [
      { id: "1", text: "Hello", sender: "system" as const },
    ];

    render(<ChatWindow messages={messages} />);

    // queryByText returns null instead of throwing when not found
    // (unlike getByText which throws). Use queryBy* when you expect
    // an element NOT to exist.
    expect(screen.queryByText(/ready to start/i)).not.toBeInTheDocument();
  });

  // ---------- S2.5.2: Approve button ----------

  it("shows Approve button when isConfirming is true", () => {
    // When the dialogue flow reaches confirmation, the user should see
    // an Approve button to accept the summary and proceed.
    render(<ChatWindow isConfirming={true} />);

    const approveBtn = screen.getByRole("button", { name: /approve/i });
    expect(approveBtn).toBeInTheDocument();
  });

  it("calls onApprove when Approve button is clicked", async () => {
    const user = userEvent.setup();
    const handleApprove = vi.fn();

    render(<ChatWindow isConfirming={true} onApprove={handleApprove} />);

    const approveBtn = screen.getByRole("button", { name: /approve/i });
    await user.click(approveBtn);

    expect(handleApprove).toHaveBeenCalledTimes(1);
  });

  it("does not show Approve button when isConfirming is false", () => {
    render(<ChatWindow isConfirming={false} />);

    // queryByRole returns null instead of throwing when not found
    expect(
      screen.queryByRole("button", { name: /approve/i })
    ).not.toBeInTheDocument();
  });

  // ---------- S2.5.4: Reject button with feedback ----------

  it("shows Reject button when isConfirming is true", () => {
    render(<ChatWindow isConfirming={true} />);

    const rejectBtn = screen.getByRole("button", { name: /reject/i });
    expect(rejectBtn).toBeInTheDocument();
  });

  it("calls onReject when Reject button is clicked", async () => {
    const user = userEvent.setup();
    const handleReject = vi.fn();

    render(<ChatWindow isConfirming={true} onReject={handleReject} />);

    const rejectBtn = screen.getByRole("button", { name: /reject/i });
    await user.click(rejectBtn);

    expect(handleReject).toHaveBeenCalledTimes(1);
  });

  it("does not show Reject button when isConfirming is false", () => {
    render(<ChatWindow isConfirming={false} />);

    expect(
      screen.queryByRole("button", { name: /reject/i })
    ).not.toBeInTheDocument();
  });

  // ---------- S2.5.5: Validation - prevent skipping approval ----------

  it("hides text input and send button when isConfirming is true", () => {
    // The user MUST click Approve or Reject — they cannot bypass
    // the decision by typing a free message.
    render(<ChatWindow isConfirming={true} />);

    expect(
      screen.queryByPlaceholderText(/ask anything/i)
    ).not.toBeInTheDocument();
    expect(
      screen.queryByRole("button", { name: /send/i })
    ).not.toBeInTheDocument();
  });

  it("shows text input and send button when isConfirming is false", () => {
    // Normal state: the user can type and send messages
    render(<ChatWindow isConfirming={false} />);

    expect(screen.getByPlaceholderText(/ask anything/i)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /send/i })).toBeInTheDocument();
  });
});
