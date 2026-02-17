import { describe, it, expect, vi, beforeEach } from "vitest";
import { renderHook, act } from "@testing-library/react";
import { useChat } from "./useChat";

// Mock the dialogue service so we don't make real API calls
// The path must match the import path used inside useChat
vi.mock("../services/dialogue");

// We need to import the mocked module AFTER vi.mock() is called
// This gives us access to control what sendMessage returns in each test
import { sendMessage } from "../services/dialogue";

describe("useChat", () => {
  beforeEach(() => {
    // Reset all mocks before each test so they don't leak between tests
    vi.resetAllMocks();
  });

  it("starts with an empty messages array", () => {
    // renderHook() is like render() but for hooks instead of components.
    // Since hooks can only run inside components, renderHook wraps
    // your hook in a test component automatically.
    const { result } = renderHook(() => useChat());

    // result.current gives us the current return value of the hook
    expect(result.current.messages).toEqual([]);
  });

  it("adds a user message when sendMessage is called", async () => {
    // Make the mock service return a fake response
    vi.mocked(sendMessage).mockResolvedValue({
      question: "What is the scope?",
      type: "scope",
      is_final: false,
    });

    const { result } = renderHook(() => useChat());

    // act() wraps state updates - React needs this to batch and apply
    // state changes properly in tests. Without it, React warns that
    // state was updated outside of act().
    await act(async () => {
      await result.current.sendMessage("Investigate APT29");
    });

    // The first message should be the user's message
    expect(result.current.messages[0]).toMatchObject({
      text: "Investigate APT29",
      sender: "user",
    });
    // Each message should have a unique id
    expect(result.current.messages[0].id).toBeDefined();
  });

  it("adds a system response after the user message", async () => {
    vi.mocked(sendMessage).mockResolvedValue({
      question: "What is the scope of your investigation?",
      type: "scope",
      is_final: false,
    });

    const { result } = renderHook(() => useChat());

    await act(async () => {
      await result.current.sendMessage("Investigate APT29");
    });

    // Should now have 2 messages: user + system
    expect(result.current.messages).toHaveLength(2);

    // Second message is the system's response
    expect(result.current.messages[1]).toMatchObject({
      text: "What is the scope of your investigation?",
      sender: "system",
    });
  });

  it("calls the dialogue service with the message, session id, and perspectives", async () => {
    vi.mocked(sendMessage).mockResolvedValue({
      question: "What is the scope?",
      type: "scope",
      is_final: false,
    });

    const { result } = renderHook(() => useChat(["US", "EU"]));

    await act(async () => {
      await result.current.sendMessage("Investigate APT29");
    });

    // Verify the service was called with correct arguments including perspectives
    expect(sendMessage).toHaveBeenCalledWith(
      "Investigate APT29",
      // We don't know the exact session ID, just that it's a string
      expect.any(String),
      ["US", "EU"],
      // approved is undefined for normal messages
      undefined
    );
  });

  it("keeps the same session id across multiple messages", async () => {
    vi.mocked(sendMessage).mockResolvedValue({
      question: "Any response",
      type: "scope",
      is_final: false,
    });

    const { result } = renderHook(() => useChat());

    await act(async () => {
      await result.current.sendMessage("First message");
    });
    await act(async () => {
      await result.current.sendMessage("Second message");
    });

    // Both calls should use the same session ID
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

    const { result } = renderHook(() => useChat());

    await act(async () => {
      await result.current.sendMessage("Investigate APT29");
    });
    await act(async () => {
      await result.current.sendMessage("Last 6 months");
    });

    // 4 messages total: user, system, user, system
    expect(result.current.messages).toHaveLength(4);
    expect(result.current.messages[0].text).toBe("Investigate APT29");
    expect(result.current.messages[1].text).toBe("What is the scope?");
    expect(result.current.messages[2].text).toBe("Last 6 months");
    expect(result.current.messages[3].text).toBe("What timeframe?");
  });

  // ---------- S2.5.2: Approve / S2.5.4: Reject / S2.5.5: Validation ----------

  it("starts with isConfirming as false", () => {
    const { result } = renderHook(() => useChat());

    // Before any messages, there's nothing to confirm
    expect(result.current.isConfirming).toBe(false);
  });

  it("sets isConfirming to true when backend returns is_final true", async () => {
    // When the backend says is_final: true, the gathering phase is done.
    // The hook should signal that we're now in the confirming state.
    vi.mocked(sendMessage).mockResolvedValue({
      question: "Here is your investigation summary. Do you approve?",
      type: "confirmation",
      is_final: true,
    });

    const { result } = renderHook(() => useChat());

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

    const { result } = renderHook(() => useChat());

    await act(async () => {
      await result.current.sendMessage("Investigate APT29");
    });

    expect(result.current.isConfirming).toBe(false);
  });

  it("sends 'approve' to backend when approve is called", async () => {
    // First, get into confirming state
    vi.mocked(sendMessage)
      .mockResolvedValueOnce({
        question: "Summary ready. Approve?",
        type: "confirmation",
        is_final: true,
      })
      // The approve call will also hit the backend
      .mockResolvedValueOnce({
        question: "Approved. Proceeding to next phase.",
        type: "complete",
        is_final: false,
      });

    const { result } = renderHook(() => useChat());

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

    const { result } = renderHook(() => useChat());

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

    const { result } = renderHook(() => useChat());

    await act(async () => {
      await result.current.sendMessage("Answer");
    });

    // 2 messages so far: user + system summary
    expect(result.current.messages).toHaveLength(2);

    await act(async () => {
      result.current.reject();
    });

    // reject() should add a frontend-only system message asking for feedback
    // This does NOT call the backend — it's purely a UI prompt
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

    const { result } = renderHook(() => useChat());

    await act(async () => {
      await result.current.sendMessage("Answer");
    });

    expect(result.current.isConfirming).toBe(true);

    await act(async () => {
      result.current.reject();
    });

    // After rejecting, isConfirming should be false so the text input reappears
    expect(result.current.isConfirming).toBe(false);
  });

  it("does not call backend when reject is called", async () => {
    vi.mocked(sendMessage).mockResolvedValueOnce({
      question: "Summary ready.",
      type: "confirmation",
      is_final: true,
    });

    const { result } = renderHook(() => useChat());

    await act(async () => {
      await result.current.sendMessage("Answer");
    });

    // Reset to track only new calls
    vi.mocked(sendMessage).mockClear();

    await act(async () => {
      result.current.reject();
    });

    // reject() is frontend-only — no backend call
    expect(sendMessage).not.toHaveBeenCalled();
  });
});
