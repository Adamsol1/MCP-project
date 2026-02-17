import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { Sidebar } from "./Sidebar";
import type { Conversation } from "../../types/conversation";

// Helper: creates a minimal conversation object for testing
function makeConversation(overrides: Partial<Conversation> = {}): Conversation {
  return {
    id: crypto.randomUUID(),
    title: "New conversation",
    messages: [],
    perspectives: ["NEUTRAL"],
    sessionId: crypto.randomUUID(),
    isConfirming: false,
    createdAt: Date.now(),
    updatedAt: Date.now(),
    ...overrides,
  };
}

describe("Sidebar", () => {
  // ---------- Rendering ----------

  it("renders a 'New Chat' button", () => {
    render(
      <Sidebar
        conversations={[]}
        activeConversationId={null}
        onNewChat={vi.fn()}
        onSwitchConversation={vi.fn()}
        onDeleteConversation={vi.fn()}
      />,
    );

    expect(
      screen.getByRole("button", { name: /new chat/i }),
    ).toBeInTheDocument();
  });

  it("renders conversation titles in the list", () => {
    const conversations = [
      makeConversation({ id: "c1", title: "Investigate APT29" }),
      makeConversation({ id: "c2", title: "Analyze ransomware" }),
    ];

    render(
      <Sidebar
        conversations={conversations}
        activeConversationId="c1"
        onNewChat={vi.fn()}
        onSwitchConversation={vi.fn()}
        onDeleteConversation={vi.fn()}
      />,
    );

    expect(screen.getByText("Investigate APT29")).toBeInTheDocument();
    expect(screen.getByText("Analyze ransomware")).toBeInTheDocument();
  });

  it("shows empty state when there are no conversations", () => {
    render(
      <Sidebar
        conversations={[]}
        activeConversationId={null}
        onNewChat={vi.fn()}
        onSwitchConversation={vi.fn()}
        onDeleteConversation={vi.fn()}
      />,
    );

    expect(screen.getByText(/no conversations/i)).toBeInTheDocument();
  });

  it("highlights the active conversation", () => {
    const conversations = [
      makeConversation({ id: "c1", title: "Active chat" }),
      makeConversation({ id: "c2", title: "Other chat" }),
    ];

    render(
      <Sidebar
        conversations={conversations}
        activeConversationId="c1"
        onNewChat={vi.fn()}
        onSwitchConversation={vi.fn()}
        onDeleteConversation={vi.fn()}
      />,
    );

    const activeItem = screen.getByText("Active chat").closest("[role='button']");
    expect(activeItem).toHaveAttribute("data-active", "true");

    const otherItem = screen.getByText("Other chat").closest("[role='button']");
    expect(otherItem).toHaveAttribute("data-active", "false");
  });

  // ---------- Interactions ----------

  it("calls onNewChat when 'New Chat' button is clicked", async () => {
    const onNewChat = vi.fn();
    const user = userEvent.setup();

    render(
      <Sidebar
        conversations={[]}
        activeConversationId={null}
        onNewChat={onNewChat}
        onSwitchConversation={vi.fn()}
        onDeleteConversation={vi.fn()}
      />,
    );

    await user.click(screen.getByRole("button", { name: /new chat/i }));

    expect(onNewChat).toHaveBeenCalledOnce();
  });

  it("calls onSwitchConversation with the conversation id when clicked", async () => {
    const onSwitch = vi.fn();
    const user = userEvent.setup();
    const conversations = [
      makeConversation({ id: "c1", title: "First chat" }),
      makeConversation({ id: "c2", title: "Second chat" }),
    ];

    render(
      <Sidebar
        conversations={conversations}
        activeConversationId="c1"
        onNewChat={vi.fn()}
        onSwitchConversation={onSwitch}
        onDeleteConversation={vi.fn()}
      />,
    );

    await user.click(screen.getByText("Second chat"));

    expect(onSwitch).toHaveBeenCalledWith("c2");
  });

  it("calls onDeleteConversation with the conversation id when delete is clicked", async () => {
    const onDelete = vi.fn();
    const user = userEvent.setup();
    const conversations = [
      makeConversation({ id: "c1", title: "Chat to delete" }),
    ];

    render(
      <Sidebar
        conversations={conversations}
        activeConversationId="c1"
        onNewChat={vi.fn()}
        onSwitchConversation={vi.fn()}
        onDeleteConversation={onDelete}
      />,
    );

    // Each conversation item has a delete button
    await user.click(screen.getByText("X"));

    expect(onDelete).toHaveBeenCalledWith("c1");
  });

  it("does not call onSwitchConversation when delete button is clicked", async () => {
    const onSwitch = vi.fn();
    const onDelete = vi.fn();
    const user = userEvent.setup();
    const conversations = [
      makeConversation({ id: "c1", title: "Chat" }),
    ];

    render(
      <Sidebar
        conversations={conversations}
        activeConversationId="c1"
        onNewChat={vi.fn()}
        onSwitchConversation={onSwitch}
        onDeleteConversation={onDelete}
      />,
    );

    await user.click(screen.getByText("X"));

    // Delete click should NOT also trigger switch
    expect(onSwitch).not.toHaveBeenCalled();
    expect(onDelete).toHaveBeenCalledOnce();
  });

  it("sorts conversations by updatedAt descending (newest first)", () => {
    const conversations = [
      makeConversation({ id: "c1", title: "Oldest", updatedAt: 1000 }),
      makeConversation({ id: "c2", title: "Newest", updatedAt: 3000 }),
      makeConversation({ id: "c3", title: "Middle", updatedAt: 2000 }),
    ];

    render(
      <Sidebar
        conversations={conversations}
        activeConversationId="c1"
        onNewChat={vi.fn()}
        onSwitchConversation={vi.fn()}
        onDeleteConversation={vi.fn()}
      />,
    );

    // Get all conversation items in DOM order
    const items = screen.getAllByRole("button", { name: /oldest|newest|middle/i });
    expect(items[0]).toHaveTextContent("Newest");
    expect(items[1]).toHaveTextContent("Middle");
    expect(items[2]).toHaveTextContent("Oldest");
  });
});
