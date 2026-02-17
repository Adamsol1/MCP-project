import { describe, it, expect, vi, beforeEach } from "vitest";
import { renderHook, act } from "@testing-library/react";
import type { ReactNode } from "react";
import { useChat } from "./useChat";
import { ConversationProvider } from "../contexts/ConversationContext";
import type { ConversationStore } from "../types/conversation";

// Mock the dialogue service so we don't make real API calls
vi.mock("../services/dialogue");
import { sendMessage } from "../services/dialogue";

const STORAGE_KEY = "mcp-conversations";

// Helper: wraps the hook in a ConversationProvider so it has context
function createWrapper() {
  return function Wrapper({ children }: { children: ReactNode }) {
    return <ConversationProvider>{children}</ConversationProvider>;
  };
}

// Pre-seeds localStorage with an active conversation before the provider mounts.
// The provider reads from localStorage on init, so this must be called BEFORE renderHook.
function seedConversation(overrides: Record<string, unknown> = {}) {
  const conv = {
    id: "test-conv-1",
    title: "New conversation",
    messages: [],
    perspectives: ["NEUTRAL"],
    sessionId: "test-session-123",
    isConfirming: false,
    createdAt: 1000,
    updatedAt: 1000,
    ...overrides,
  };
  const store: ConversationStore = {
    conversations: [conv],
    activeConversationId: conv.id,
  };
  localStorage.setItem(STORAGE_KEY, JSON.stringify(store));
  return conv;
}

describe("useChat", () => {
  beforeEach(() => {
    vi.resetAllMocks();
    localStorage.clear();
    seedConversation(); // Default conversation for all tests
  });

  it("starts with an empty messages array", () => {
    const { result } = renderHook(() => useChat(), {
      wrapper: createWrapper(),
    });

    expect(result.current.messages).toEqual([]);
  });

  it("adds a user message when sendMessage is called", async () => {
    vi.mocked(sendMessage).mockResolvedValue({
      question: "What is the scope?",
      type: "scope",
      is_final: false,
    });

    const { result } = renderHook(() => useChat(), {
      wrapper: createWrapper(),
    });

    await act(async () => {
      await result.current.sendMessage("Investigate APT29");
    });

    expect(result.current.messages[0]).toMatchObject({
      text: "Investigate APT29",
      sender: "user",
    });
    expect(result.current.messages[0].id).toBeDefined();
  });

  it("adds a system response after the user message", async () => {
    vi.mocked(sendMessage).mockResolvedValue({
      question: "What is the scope of your investigation?",
      type: "scope",
      is_final: false,
    });

    const { result } = renderHook(() => useChat(), {
      wrapper: createWrapper(),
    });

    await act(async () => {
      await result.current.sendMessage("Investigate APT29");
    });

    expect(result.current.messages).toHaveLength(2);
    expect(result.current.messages[1]).toMatchObject({
      text: "What is the scope of your investigation?",
      sender: "system",
    });
  });

  it("calls the dialogue service with the message, session id, and perspectives", async () => {
    // Seed a conversation with specific perspectives
    localStorage.clear();
    seedConversation({ perspectives: ["US", "EU"] });

    vi.mocked(sendMessage).mockResolvedValue({
      question: "What is the scope?",
      type: "scope",
      is_final: false,
    });

    const { result } = renderHook(() => useChat(), {
      wrapper: createWrapper(),
    });

    await act(async () => {
      await result.current.sendMessage("Investigate APT29");
    });

    // Now checks the exact sessionId from the seeded conversation
    expect(sendMessage).toHaveBeenCalledWith(
      "Investigate APT29",
      "test-session-123",
      ["US", "EU"],
      undefined,
    );
  });

  it("keeps the same session id across multiple messages", async () => {
    vi.mocked(sendMessage).mockResolvedValue({
      question: "Any response",
      type: "scope",
      is_final: false,
    });

    const { result } = renderHook(() => useChat(), {
      wrapper: createWrapper(),
    });

    await act(async () => {
      await result.current.sendMessage("First message");
    });
    await act(async () => {
      await result.current.sendMessage("Second message");
    });

    const firstCallSessionId = vi.mocked(sendMessage).mock.calls[0][1];
    const secondCallSessionId = vi.mocked(sendMessage).mock.calls[1][1];
    expect(firstCallSessionId).toBe(secondCallSessionId);
  });

  it("accumulates messages over multiple exchanges", async () => {
    vi.mocked(sendMessage)
      .mockResolvedValueOnce({
        question: "What is the scope?",
        type: "scope",
        is_final: false,
      })
      .mockResolvedValueOnce({
        question: "What timeframe?",
        type: "timeframe",
        is_final: false,
      });

    const { result } = renderHook(() => useChat(), {
      wrapper: createWrapper(),
    });

    await act(async () => {
      await result.current.sendMessage("Investigate APT29");
    });
    await act(async () => {
      await result.current.sendMessage("Last 6 months");
    });

    expect(result.current.messages).toHaveLength(4);
    expect(result.current.messages[0].text).toBe("Investigate APT29");
    expect(result.current.messages[1].text).toBe("What is the scope?");
    expect(result.current.messages[2].text).toBe("Last 6 months");
    expect(result.current.messages[3].text).toBe("What timeframe?");
  });

  // ---------- S2.5.2: Approve / S2.5.4: Reject / S2.5.5: Validation ----------

  it("starts with isConfirming as false", () => {
    const { result } = renderHook(() => useChat(), {
      wrapper: createWrapper(),
    });

    expect(result.current.isConfirming).toBe(false);
  });

  it("sets isConfirming to true when backend returns is_final true", async () => {
    vi.mocked(sendMessage).mockResolvedValue({
      question: "Here is your investigation summary. Do you approve?",
      type: "confirmation",
      is_final: true,
    });

    const { result } = renderHook(() => useChat(), {
      wrapper: createWrapper(),
    });

    await act(async () => {
      await result.current.sendMessage("Last 6 months");
    });

    expect(result.current.isConfirming).toBe(true);
  });

  it("keeps isConfirming false when backend returns is_final false", async () => {
    vi.mocked(sendMessage).mockResolvedValue({
      question: "What is the scope?",
      type: "scope",
      is_final: false,
    });

    const { result } = renderHook(() => useChat(), {
      wrapper: createWrapper(),
    });

    await act(async () => {
      await result.current.sendMessage("Investigate APT29");
    });

    expect(result.current.isConfirming).toBe(false);
  });

  it("sends 'approve' to backend when approve is called", async () => {
    vi.mocked(sendMessage)
      .mockResolvedValueOnce({
        question: "Summary ready. Approve?",
        type: "confirmation",
        is_final: true,
      })
      .mockResolvedValueOnce({
        question: "Approved. Proceeding to next phase.",
        type: "complete",
        is_final: false,
      });

    const { result } = renderHook(() => useChat(), {
      wrapper: createWrapper(),
    });

    await act(async () => {
      await result.current.sendMessage("Some answer");
    });

    expect(result.current.isConfirming).toBe(true);

    await act(async () => {
      await result.current.approve();
    });

    // The second call to the service should include approved: true (4th argument)
    expect(vi.mocked(sendMessage).mock.calls[1][3]).toBe(true);
  });

  it("sets isConfirming to false after approve", async () => {
    vi.mocked(sendMessage)
      .mockResolvedValueOnce({
        question: "Summary ready.",
        type: "confirmation",
        is_final: true,
      })
      .mockResolvedValueOnce({
        question: "Proceeding.",
        type: "complete",
        is_final: false,
      });

    const { result } = renderHook(() => useChat(), {
      wrapper: createWrapper(),
    });

    await act(async () => {
      await result.current.sendMessage("Answer");
    });
    await act(async () => {
      await result.current.approve();
    });

    expect(result.current.isConfirming).toBe(false);
  });

  it("adds a frontend-only feedback message when reject is called", async () => {
    vi.mocked(sendMessage).mockResolvedValueOnce({
      question: "Summary ready. Approve?",
      type: "confirmation",
      is_final: true,
    });

    const { result } = renderHook(() => useChat(), {
      wrapper: createWrapper(),
    });

    await act(async () => {
      await result.current.sendMessage("Answer");
    });

    // 2 messages so far: user + system summary
    expect(result.current.messages).toHaveLength(2);

    act(() => {
      result.current.reject();
    });

    // reject() adds a frontend-only system message — no backend call
    expect(result.current.messages).toHaveLength(3);
    expect(result.current.messages[2]).toMatchObject({
      text: expect.stringMatching(/what would you like to change/i),
      sender: "system",
    });
  });

  it("sets isConfirming to false after reject so user can type feedback", async () => {
    vi.mocked(sendMessage).mockResolvedValueOnce({
      question: "Summary ready.",
      type: "confirmation",
      is_final: true,
    });

    const { result } = renderHook(() => useChat(), {
      wrapper: createWrapper(),
    });

    await act(async () => {
      await result.current.sendMessage("Answer");
    });

    expect(result.current.isConfirming).toBe(true);

    act(() => {
      result.current.reject();
    });

    expect(result.current.isConfirming).toBe(false);
  });

  it("does not call backend when reject is called", async () => {
    vi.mocked(sendMessage).mockResolvedValueOnce({
      question: "Summary ready.",
      type: "confirmation",
      is_final: true,
    });

    const { result } = renderHook(() => useChat(), {
      wrapper: createWrapper(),
    });

    await act(async () => {
      await result.current.sendMessage("Answer");
    });

    vi.mocked(sendMessage).mockClear();

    act(() => {
      result.current.reject();
    });

    expect(sendMessage).not.toHaveBeenCalled();
  });
});
