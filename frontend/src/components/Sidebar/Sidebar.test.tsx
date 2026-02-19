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

// Helper: renders Sidebar with sensible defaults so each test only specifies
// what it actually cares about.
function renderSidebar(
  props: Partial<React.ComponentProps<typeof Sidebar>> = {},
) {
  return render(
    <Sidebar
      conversations={[]}
      activeConversationId={null}
      onNewChat={vi.fn()}
      onSwitchConversation={vi.fn()}
      onDeleteConversation={vi.fn()}
      onRenameConversation={vi.fn()}
      {...props}
    />,
  );
}

describe("Sidebar", () => {
  // ---------- Rendering ----------

  it("renders a 'New Chat' button", () => {
    renderSidebar();
    expect(
      screen.getByRole("button", { name: /new chat/i }),
    ).toBeInTheDocument();
  });

  it("renders conversation titles in the list", () => {
    const conversations = [
      makeConversation({ id: "c1", title: "Investigate APT29" }),
      makeConversation({ id: "c2", title: "Analyze ransomware" }),
    ];

    renderSidebar({ conversations, activeConversationId: "c1" });

    expect(screen.getByText("Investigate APT29")).toBeInTheDocument();
    expect(screen.getByText("Analyze ransomware")).toBeInTheDocument();
  });

  it("shows empty state when there are no conversations", () => {
    renderSidebar();
    expect(screen.getByText(/no conversations/i)).toBeInTheDocument();
  });

  it("highlights the active conversation", () => {
    const conversations = [
      makeConversation({ id: "c1", title: "Active chat" }),
      makeConversation({ id: "c2", title: "Other chat" }),
    ];

    renderSidebar({ conversations, activeConversationId: "c1" });

    // Use closest("[data-active]") to find the container that carries the attribute
    const activeItem = screen
      .getByText("Active chat")
      .closest("[data-active]");
    expect(activeItem).toHaveAttribute("data-active", "true");

    const otherItem = screen.getByText("Other chat").closest("[data-active]");
    expect(otherItem).toHaveAttribute("data-active", "false");
  });

  // ---------- Basic Interactions ----------

  it("calls onNewChat when 'New Chat' button is clicked", async () => {
    const onNewChat = vi.fn();
    const user = userEvent.setup();

    renderSidebar({ onNewChat });

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

    renderSidebar({
      conversations,
      activeConversationId: "c1",
      onSwitchConversation: onSwitch,
    });

    await user.click(screen.getByText("Second chat"));

    expect(onSwitch).toHaveBeenCalledWith("c2");
  });

  it("calls onDeleteConversation with the conversation id via options menu", async () => {
    // Previously this test clicked an "X" button.
    // The X button is replaced by a "..." options menu revealed on hover.
    const onDelete = vi.fn();
    const user = userEvent.setup();
    const conversations = [
      makeConversation({ id: "c1", title: "Chat to delete" }),
    ];

    renderSidebar({
      conversations,
      activeConversationId: "c1",
      onDeleteConversation: onDelete,
    });

    await user.hover(screen.getByText("Chat to delete"));
    await user.click(screen.getByRole("button", { name: /chat options/i }));
    await user.click(screen.getByRole("menuitem", { name: /delete/i }));

    expect(onDelete).toHaveBeenCalledWith("c1");
  });

  it("does not call onSwitchConversation when delete is selected from options menu", async () => {
    // Previously relied on stopPropagation on an X button.
    // Now uses the options menu — selecting Delete must still not trigger switch.
    const onSwitch = vi.fn();
    const onDelete = vi.fn();
    const user = userEvent.setup();
    const conversations = [makeConversation({ id: "c1", title: "Chat" })];

    renderSidebar({
      conversations,
      activeConversationId: "c1",
      onSwitchConversation: onSwitch,
      onDeleteConversation: onDelete,
    });

    await user.hover(screen.getByText("Chat"));
    await user.click(screen.getByRole("button", { name: /chat options/i }));
    await user.click(screen.getByRole("menuitem", { name: /delete/i }));

    expect(onSwitch).not.toHaveBeenCalled();
    expect(onDelete).toHaveBeenCalledOnce();
  });

  it("sorts conversations by updatedAt descending (newest first)", () => {
    const conversations = [
      makeConversation({ id: "c1", title: "Oldest", updatedAt: 1000 }),
      makeConversation({ id: "c2", title: "Newest", updatedAt: 3000 }),
      makeConversation({ id: "c3", title: "Middle", updatedAt: 2000 }),
    ];

    renderSidebar({ conversations, activeConversationId: "c1" });

    // Get all conversation items in DOM order
    const items = screen.getAllByRole("button", {
      name: /oldest|newest|middle/i,
    });
    expect(items[0]).toHaveTextContent("Newest");
    expect(items[1]).toHaveTextContent("Middle");
    expect(items[2]).toHaveTextContent("Oldest");
  });

  // ---------- Options Menu ----------
  // The options button ("...") is hidden until the user hovers a chat item,
  // then clicking it opens a dropdown with "Rename" and "Delete" actions.

  it("does not show the options button when no chat item is hovered", () => {
    const conversations = [makeConversation({ id: "c1", title: "My chat" })];

    renderSidebar({ conversations });

    // The "..." button should not be in the DOM at all before any hover
    expect(
      screen.queryByRole("button", { name: /chat options/i }),
    ).not.toBeInTheDocument();
  });

  it("shows the options button when hovering a chat item", async () => {
    const user = userEvent.setup();
    const conversations = [makeConversation({ id: "c1", title: "My chat" })];

    renderSidebar({ conversations });

    await user.hover(screen.getByText("My chat"));

    expect(
      screen.getByRole("button", { name: /chat options/i }),
    ).toBeInTheDocument();
  });

  it("opens a dropdown with Rename and Delete when the options button is clicked", async () => {
    const user = userEvent.setup();
    const conversations = [makeConversation({ id: "c1", title: "My chat" })];

    renderSidebar({ conversations });

    await user.hover(screen.getByText("My chat"));
    await user.click(screen.getByRole("button", { name: /chat options/i }));

    expect(
      screen.getByRole("menuitem", { name: /rename/i }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("menuitem", { name: /delete/i }),
    ).toBeInTheDocument();
  });

  it("closes the dropdown when clicking outside of it", async () => {
    const user = userEvent.setup();
    const conversations = [makeConversation({ id: "c1", title: "My chat" })];

    renderSidebar({ conversations });

    await user.hover(screen.getByText("My chat"));
    await user.click(screen.getByRole("button", { name: /chat options/i }));

    // Confirm dropdown is open
    expect(
      screen.getByRole("menuitem", { name: /rename/i }),
    ).toBeInTheDocument();

    // Click somewhere outside
    await user.click(document.body);

    expect(
      screen.queryByRole("menuitem", { name: /rename/i }),
    ).not.toBeInTheDocument();
  });

  // ---------- Rename ----------
  // Selecting "Rename" from the dropdown switches the chat item into an inline
  // edit mode: the title text is replaced by a text input pre-filled with the
  // current title. Pressing Enter confirms; Escape cancels.

  it("switches to rename mode (shows a text input) when Rename is selected", async () => {
    const user = userEvent.setup();
    const conversations = [makeConversation({ id: "c1", title: "My chat" })];

    renderSidebar({ conversations });

    await user.hover(screen.getByText("My chat"));
    await user.click(screen.getByRole("button", { name: /chat options/i }));
    await user.click(screen.getByRole("menuitem", { name: /rename/i }));

    const input = screen.getByRole("textbox");
    expect(input).toBeInTheDocument();
    // Input must be pre-filled with the existing title
    expect(input).toHaveValue("My chat");
  });

  it("calls onRenameConversation with id and new title when Enter is pressed", async () => {
    const onRename = vi.fn();
    const user = userEvent.setup();
    const conversations = [makeConversation({ id: "c1", title: "My chat" })];

    renderSidebar({ conversations, onRenameConversation: onRename });

    await user.hover(screen.getByText("My chat"));
    await user.click(screen.getByRole("button", { name: /chat options/i }));
    await user.click(screen.getByRole("menuitem", { name: /rename/i }));

    const input = screen.getByRole("textbox");
    await user.clear(input);
    await user.type(input, "Updated title");
    await user.keyboard("{Enter}");

    expect(onRename).toHaveBeenCalledWith("c1", "Updated title");
  });

  it("does not call onRenameConversation when rename is cancelled with Escape", async () => {
    const onRename = vi.fn();
    const user = userEvent.setup();
    const conversations = [makeConversation({ id: "c1", title: "My chat" })];

    renderSidebar({ conversations, onRenameConversation: onRename });

    await user.hover(screen.getByText("My chat"));
    await user.click(screen.getByRole("button", { name: /chat options/i }));
    await user.click(screen.getByRole("menuitem", { name: /rename/i }));

    await user.type(screen.getByRole("textbox"), " extra text");
    await user.keyboard("{Escape}");

    expect(onRename).not.toHaveBeenCalled();
  });

  it("restores the original title and exits rename mode after pressing Escape", async () => {
    const user = userEvent.setup();
    const conversations = [makeConversation({ id: "c1", title: "My chat" })];

    renderSidebar({ conversations });

    await user.hover(screen.getByText("My chat"));
    await user.click(screen.getByRole("button", { name: /chat options/i }));
    await user.click(screen.getByRole("menuitem", { name: /rename/i }));

    // Partially edit then cancel
    await user.keyboard("{Escape}");

    // Input should be gone and the original title should be visible
    expect(screen.queryByRole("textbox")).not.toBeInTheDocument();
    expect(screen.getByText("My chat")).toBeInTheDocument();
  });
});
