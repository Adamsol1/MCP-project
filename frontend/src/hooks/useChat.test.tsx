import { describe, it, expect, vi, beforeEach } from "vitest";
import { renderHook, act } from "@testing-library/react";
import type { ReactNode } from "react";
import { useChat } from "./useChat";
import { ConversationProvider } from "../contexts/ConversationContext/ConversationContext";
import { ToastProvider } from "../contexts/Toast/ToastContext";
import { SettingsProvider } from "../contexts/SettingsContext/SettingsContext";
import type { ConversationStore } from "../types/conversation";

// Mock the dialogue service so we don't make real API calls
vi.mock("../services/dialogue");
import { sendMessage } from "../services/dialogue";

const STORAGE_KEY = "mcp-conversations";

// Helper: wraps the hook in all required providers
function createWrapper() {
  return function Wrapper({ children }: { children: ReactNode }) {
    return (
      <SettingsProvider>
        <ToastProvider>
          <ConversationProvider>{children}</ConversationProvider>
        </ToastProvider>
      </SettingsProvider>
    );
  };
}

// Pre-seeds localStorage with an active conversation before the provider mounts.
// The provider reads from localStorage on init, so this must be called BEFORE renderHook.
function seedConversation(overrides: Record<string, unknown> = {}) {
  const conv: ConversationStore["conversations"][number] = {
    id: "test-conv-1",
    title: "New conversation",
    messages: [],
    perspectives: ["NEUTRAL"],
    sessionId: "test-session-123",
    isConfirming: false,
    stage: "initial",
    subState: null,
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
      action: "ask_question",
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
      action: "ask_question",
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
      action: "ask_question",
    });

    const { result } = renderHook(() => useChat(), {
      wrapper: createWrapper(),
    });

    await act(async () => {
      await result.current.sendMessage("Investigate APT29");
    });

    // Now checks the exact sessionId from the seeded conversation
    // sendMessage is called with 6 args: message, sessionId, perspectives, approved, language, timeframe
    expect(sendMessage).toHaveBeenCalledWith(
      "Investigate APT29",
      "test-session-123",
      ["US", "EU"],
      undefined,
      "en",
      "",
    );
  });

  it("auto-creates a conversation and sends the message when no conversation exists", async () => {
    // Start with no conversation in localStorage — simulates a first-time visitor
    // or a user who deleted all conversations.
    localStorage.clear();

    vi.mocked(sendMessage).mockResolvedValue({
      question: "What is the scope of your investigation?",
      action: "ask_question",
    });

    const { result } = renderHook(() => useChat(), {
      wrapper: createWrapper(),
    });

    // activeConversation is null at this point — no conversations exist
    await act(async () => {
      await result.current.sendMessage("Investigate APT29");
    });

    // The message should have been added to the auto-created conversation
    expect(result.current.messages).toHaveLength(2);
    expect(result.current.messages[0]).toMatchObject({
      text: "Investigate APT29",
      sender: "user",
    });
    expect(result.current.messages[1]).toMatchObject({
      text: "What is the scope of your investigation?",
      sender: "system",
    });
  });

  it("keeps the same session id across multiple messages", async () => {
    vi.mocked(sendMessage).mockResolvedValue({
      question: "Any response",
      action: "ask_question",
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
        action: "ask_question",
      })
      .mockResolvedValueOnce({
        question: "What timeframe?",
        action: "ask_question",
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

  it("sets isConfirming to true when backend returns show_summary action", async () => {
    vi.mocked(sendMessage).mockResolvedValue({
      question: "Here is your investigation summary. Do you approve?",
      action: "show_summary",
    });

    const { result } = renderHook(() => useChat(), {
      wrapper: createWrapper(),
    });

    await act(async () => {
      await result.current.sendMessage("Last 6 months");
    });

    expect(result.current.isConfirming).toBe(true);
  });

  it("keeps isConfirming false when backend returns ask_question action", async () => {
    vi.mocked(sendMessage).mockResolvedValue({
      question: "What is the scope?",
      action: "ask_question",
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
        action: "show_summary",
      })
      .mockResolvedValueOnce({
        question: "Approved. Proceeding to next phase.",
        action: "complete",
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
        action: "show_summary",
      })
      .mockResolvedValueOnce({
        question: "Proceeding.",
        action: "complete",
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
      action: "show_summary",
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
      action: "show_summary",
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
      action: "show_summary",
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

describe("buildSystemMessage — structured response parsing", () => {
  beforeEach(() => {
    vi.resetAllMocks();
    localStorage.clear();
    seedConversation();
  });

  it("stores type and parsed data when backend returns a summary response", async () => {
    const summaryPayload = {
      summary: "Investigation focused on APT29 targeting EU infrastructure.",
    };
    vi.mocked(sendMessage).mockResolvedValue({
      question: JSON.stringify(summaryPayload),
      action: "show_summary",
    });

    const { result } = renderHook(() => useChat(), {
      wrapper: createWrapper(),
    });
    await act(async () => {
      await result.current.sendMessage("Investigate APT29");
    });

    const systemMessage = result.current.messages[1];
    expect(systemMessage.type).toBe("summary");
    expect(systemMessage.data).toEqual(summaryPayload);
    // Raw text is still preserved as the fallback for plain rendering
    expect(systemMessage.text).toBe(JSON.stringify(summaryPayload));
  });

  it("stores type and parsed data when backend returns a pir response", async () => {
    const pirPayload = {
      result: "These PIRs address the investigation requirements.",
      pirs: [
        {
          question: "What TTPs has APT29 used against EU targets?",
          priority: "high",
          rationale: "Core intelligence requirement for the investigation.",
        },
      ],
      reasoning: "Selected based on scope and context provided.",
    };
    vi.mocked(sendMessage).mockResolvedValue({
      question: JSON.stringify(pirPayload),
      action: "show_pir",
    });

    const { result } = renderHook(() => useChat(), {
      wrapper: createWrapper(),
    });
    await act(async () => {
      await result.current.sendMessage("Approve summary");
    });

    const systemMessage = result.current.messages[1];
    expect(systemMessage.type).toBe("pir");
    expect(systemMessage.data).toEqual(pirPayload);
  });

  it("stores type but no data when backend returns a question response", async () => {
    vi.mocked(sendMessage).mockResolvedValue({
      question: "What is the scope of your investigation?",
      action: "ask_question",
    });

    const { result } = renderHook(() => useChat(), {
      wrapper: createWrapper(),
    });
    await act(async () => {
      await result.current.sendMessage("Investigate APT29");
    });

    const systemMessage = result.current.messages[1];
    expect(systemMessage.type).toBe("question");
    expect(systemMessage.data).toBeUndefined();
  });

  it("stores raw text and no data when summary response contains invalid JSON", async () => {
    const malformedJson = "This is not valid JSON {{{";
    vi.mocked(sendMessage).mockResolvedValue({
      question: malformedJson,
      action: "show_summary",
    });

    const { result } = renderHook(() => useChat(), {
      wrapper: createWrapper(),
    });
    await act(async () => {
      await result.current.sendMessage("Investigate APT29");
    });

    const systemMessage = result.current.messages[1];
    expect(systemMessage.type).toBe("summary");
    expect(systemMessage.data).toBeUndefined();
    // Raw text is still displayed so the user sees something
    expect(systemMessage.text).toBe(malformedJson);
  });

  it("approve() also stores structured data from the backend response", async () => {
    const pirPayload = {
      result: "Summary of PIRs.",
      pirs: [{ question: "Q1?", priority: "high", rationale: "R1." }],
      reasoning: "Reasoning behind selection.",
    };
    vi.mocked(sendMessage)
      .mockResolvedValueOnce({
        question: JSON.stringify({ summary: "Investigation context summary." }),
        action: "show_summary",
      })
      .mockResolvedValueOnce({
        question: JSON.stringify(pirPayload),
        action: "show_pir",
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

    // approve() is silent — no user message added, just the system PIR reply
    // messages: [0] user "Answer", [1] system summary, [2] system pir
    const pirMessage = result.current.messages.at(-1);
    expect(pirMessage?.type).toBe("pir");
    expect(pirMessage?.data).toEqual(pirPayload);
  });
});

describe("action-first response handling", () => {
  beforeEach(() => {
    vi.resetAllMocks();
    localStorage.clear();
    seedConversation();
  });

  it("maps max_questions action to summary message rendering", async () => {
    const summaryPayload = {
      summary: "Reached max questions. Please confirm current direction.",
    };
    vi.mocked(sendMessage).mockResolvedValue({
      question: JSON.stringify(summaryPayload),
      action: "max_questions",
    });

    const { result } = renderHook(() => useChat(), {
      wrapper: createWrapper(),
    });
    await act(async () => {
      await result.current.sendMessage("Continue");
    });

    const systemMessage = result.current.messages[1];
    expect(systemMessage.type).toBe("summary");
    expect(systemMessage.data).toEqual(summaryPayload);
    expect(result.current.stage).toBe("summary_confirming");
    expect(result.current.isConfirming).toBe(true);
  });

  it("infers pir_confirming stage from show_pir action when stage is omitted", async () => {
    const pirPayload = {
      result: "Generated PIRs",
      pirs: [{ question: "Q1", priority: "high", rationale: "R1" }],
      reasoning: "Reasoning",
    };
    vi.mocked(sendMessage).mockResolvedValue({
      question: JSON.stringify(pirPayload),
      action: "show_pir",
    });

    const { result } = renderHook(() => useChat(), {
      wrapper: createWrapper(),
    });
    await act(async () => {
      await result.current.sendMessage("Approve summary");
    });

    expect(result.current.stage).toBe("pir_confirming");
    expect(result.current.isConfirming).toBe(true);
    expect(result.current.messages[1].type).toBe("pir");
  });

  it("keeps summary-confirming behavior for show_summary action", async () => {
    vi.mocked(sendMessage).mockResolvedValue({
      question: "Summary response",
      action: "show_summary",
    });

    const { result } = renderHook(() => useChat(), {
      wrapper: createWrapper(),
    });
    await act(async () => {
      await result.current.sendMessage("Summary path");
    });

    expect(result.current.stage).toBe("summary_confirming");
    expect(result.current.isConfirming).toBe(true);
    expect(result.current.messages[1].type).toBe("summary");
  });
});
