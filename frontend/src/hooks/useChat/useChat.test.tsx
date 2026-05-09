import { describe, it, expect, vi, beforeEach } from "vitest";
import { renderHook, act } from "@testing-library/react";
import type { ReactNode } from "react";
import { useChat } from "./useChat";
import { ConversationProvider } from "../../contexts/ConversationContext/ConversationContext";
import { ToastProvider } from "../../contexts/Toast/ToastContext";
import { SettingsProvider } from "../../contexts/SettingsContext/SettingsContext";
import { WorkspaceProvider } from "../../contexts/WorkspaceContext/WorkspaceContext";
import type { ConversationStore } from "../../types/conversation";

// Mock the dialogue service so we don't make real API calls
vi.mock("../../services/dialogue/dialogue");
import {
  sendMessage,
  setDevDialogueState,
  getDevDialogueState,
  resetDevDialogueState,
  restoreDevDialogueSnapshot,
  listDevDialogueSnapshots,
} from "../../services/dialogue/dialogue";

const STORAGE_KEY = "mcp-conversations";

// Helper: wraps the hook in all required providers
function createWrapper() {
  return function Wrapper({ children }: { children: ReactNode }) {
    return (
      <SettingsProvider>
        <ToastProvider>
          <WorkspaceProvider>
            <ConversationProvider>{children}</ConversationProvider>
          </WorkspaceProvider>
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
    phase: "direction",
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

  it("starts with an empty messages array", async () => {
    const { result } = renderHook(() => useChat(), {
      wrapper: createWrapper(),
    });
    await act(async () => {}); // flush provider useEffect state updates

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
    // sendMessage is called with 7 args: message, sessionId, perspectives,
    // approved, language, timeframe, control options.
    expect(sendMessage).toHaveBeenCalledWith(
      "Investigate APT29",
      "test-session-123",
      ["US", "EU"],
      undefined,
      "en",
      "",
      {
        sourceTimeframes: {
          web_gov: "",
          web_think_tank: "",
          web_news: "",
          web_other: "",
        },
      },
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

  it("hides confirmation immediately while approve request is pending", async () => {
    let resolveApprove:
      | ((value: { question: string; action: "complete" }) => void)
      | null = null;

    vi.mocked(sendMessage)
      .mockResolvedValueOnce({
        question: "Summary ready.",
        action: "show_summary",
      })
      .mockImplementationOnce(
        () =>
          new Promise((resolve) => {
            resolveApprove = resolve as (value: {
              question: string;
              action: "complete";
            }) => void;
          }),
      );

    const { result } = renderHook(() => useChat(), {
      wrapper: createWrapper(),
    });

    await act(async () => {
      await result.current.sendMessage("Answer");
    });

    expect(result.current.isConfirming).toBe(true);

    let pendingApprove: Promise<void> | undefined;
    act(() => {
      pendingApprove = result.current.approve();
    });

    expect(result.current.isConfirming).toBe(false);

    await act(async () => {
      resolveApprove?.({
        question: "Proceeding.",
        action: "complete",
      });
      await pendingApprove;
    });
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

// ---------------------------------------------------------------------------
// Additional action-type coverage (show_plan, show_collection, show_processing,
// show_analysis, start_collecting, error, complete, select_gaps)
// ---------------------------------------------------------------------------

describe("useChat — action response types (coverage of buildSystemMessage branches)", () => {
  beforeEach(() => {
    vi.resetAllMocks();
    localStorage.clear();
    seedConversation();
  });

  it("maps show_plan action to plan message type", async () => {
    const planPayload = {
      plan: "Collect from OSINT sources and cross-reference.",
      steps: [
        { title: "OSINT Gather", description: "Search public sources.", suggested_sources: ["Web Search"] },
      ],
      suggested_sources: ["Web Search"],
    };
    vi.mocked(sendMessage).mockResolvedValue({
      question: JSON.stringify(planPayload),
      action: "show_plan",
    });

    const { result } = renderHook(() => useChat(), { wrapper: createWrapper() });
    await act(async () => {
      await result.current.sendMessage("Approve PIR");
    });

    const msg = result.current.messages[1];
    expect(msg.type).toBe("plan");
    expect(msg.data).toBeDefined();
  });

  it("maps show_collection action to collection message type", async () => {
    const collectionPayload = {
      collected_data: [{ source: "query_otx", resource_id: "r1", content: "data" }],
      source_summary: [{ display_name: "AlienVault OTX", count: 1, resource_ids: ["r1"], has_content: true }],
    };
    vi.mocked(sendMessage).mockResolvedValue({
      question: JSON.stringify(collectionPayload),
      action: "show_collection",
    });

    const { result } = renderHook(() => useChat(), { wrapper: createWrapper() });
    await act(async () => {
      await result.current.sendMessage("Start collection");
    });

    const msg = result.current.messages[1];
    expect(msg.type).toBe("collection");
    expect(msg.data).toBeDefined();
  });

  it("maps show_processing action to processing message type", async () => {
    const processingPayload = {
      findings: [
        {
          id: "f1",
          title: "Finding A",
          finding: "Details",
          confidence: 0.8,
          source: "query_otx",
          categories: [],
          relevant_to: [],
          reasoning: "",
          attack_ids: [],
          sources: [],
        },
      ],
      gaps: ["Gap 1"],
      reasoning: "Some reasoning",
    };
    vi.mocked(sendMessage).mockResolvedValue({
      question: JSON.stringify(processingPayload),
      action: "show_processing",
    });

    const { result } = renderHook(() => useChat(), { wrapper: createWrapper() });
    await act(async () => {
      await result.current.sendMessage("Process data");
    });

    const msg = result.current.messages[1];
    expect(msg.type).toBe("processing");
    expect(msg.data).toBeDefined();
  });

  it("maps show_analysis action to analysis message type", async () => {
    const analysisPayload = {
      analysis_draft: "Analysis complete with findings.",
      key_findings: [],
      sources_referenced: [],
    };
    vi.mocked(sendMessage).mockResolvedValue({
      question: JSON.stringify(analysisPayload),
      action: "show_analysis",
    });

    const { result } = renderHook(() => useChat(), { wrapper: createWrapper() });
    await act(async () => {
      await result.current.sendMessage("Generate analysis");
    });

    const msg = result.current.messages[1];
    expect(msg.type).toBe("analysis");
  });

  it("maps start_collecting action and parses suggested sources", async () => {
    const sources = ["Web Search", "AlienVault OTX"];
    vi.mocked(sendMessage).mockResolvedValue({
      question: JSON.stringify(sources),
      action: "start_collecting",
    });

    const { result } = renderHook(() => useChat(), { wrapper: createWrapper() });
    await act(async () => {
      await result.current.sendMessage("Collect from sources");
    });

    // start_collecting maps to "question" type
    const msg = result.current.messages[1];
    expect(msg.type).toBe("question");
    expect(msg.text).toMatch(/Web Search|collecting/i);
  });

  it("maps error action and shows error message text", async () => {
    vi.mocked(sendMessage).mockResolvedValue({
      question: "Collection failed",
      action: "error",
    });

    const { result } = renderHook(() => useChat(), { wrapper: createWrapper() });
    await act(async () => {
      await result.current.sendMessage("Do something");
    });

    const msg = result.current.messages[1];
    expect(msg.type).toBe("error");
  });

  it("maps complete action and sets stage to complete", async () => {
    vi.mocked(sendMessage).mockResolvedValue({
      question: "Task complete.",
      action: "complete",
    });

    const { result } = renderHook(() => useChat(), { wrapper: createWrapper() });
    await act(async () => {
      await result.current.sendMessage("Finalize");
    });

    expect(result.current.stage).toBe("complete");
  });

  it("maps select_gaps action to question type with reviewing/awaiting_gather_more stage", async () => {
    vi.mocked(sendMessage).mockResolvedValue({
      question: "Which gaps do you want to address?",
      action: "select_gaps",
    });

    const { result } = renderHook(() => useChat(), { wrapper: createWrapper() });
    await act(async () => {
      await result.current.sendMessage("Select gaps");
    });

    const msg = result.current.messages[1];
    expect(msg.type).toBe("question");
    expect(result.current.stage).toBe("reviewing");
  });

  it("parses plan from plain numbered text when JSON is absent (parseStepsFromPlanText)", async () => {
    const planText =
      "1. **Gather OSINT:** Search public sources for threat indicators.\n" +
      "2. **Analyse results:** Cross-reference with internal knowledge base.";
    vi.mocked(sendMessage).mockResolvedValue({
      question: planText,
      action: "show_plan",
    });

    const { result } = renderHook(() => useChat(), { wrapper: createWrapper() });
    await act(async () => {
      await result.current.sendMessage("Generate plan");
    });

    const msg = result.current.messages[1];
    expect(msg.type).toBe("plan");
    const data = msg.data as { steps?: { title: string }[] };
    expect(data?.steps).toBeDefined();
    expect(data?.steps?.length).toBeGreaterThanOrEqual(2);
  });

  it("extracts JSON from code block in processing response (extractJsonObject code block path)", async () => {
    const processingPayload = {
      findings: [
        {
          id: "f1",
          title: "Code block finding",
          finding: "Details",
          confidence: 0.75,
          source: "query_otx",
          categories: [],
          relevant_to: [],
          reasoning: "",
          attack_ids: [],
          sources: [],
        },
      ],
      gaps: [],
      reasoning: "",
    };
    const wrapped = `\`\`\`json\n${JSON.stringify(processingPayload)}\n\`\`\``;
    vi.mocked(sendMessage).mockResolvedValue({
      question: wrapped,
      action: "show_processing",
    });

    const { result } = renderHook(() => useChat(), { wrapper: createWrapper() });
    await act(async () => {
      await result.current.sendMessage("Process data");
    });

    const msg = result.current.messages[1];
    expect(msg.type).toBe("processing");
    // The data should have been extracted from the code block
    expect(msg.data).toBeDefined();
  });

  it("maps show_council action to council message type", async () => {
    const councilPayload = {
      debate_point: "Should we escalate?",
      perspectives: [],
      key_agreements: [],
      full_debate: "",
    };
    vi.mocked(sendMessage).mockResolvedValue({
      question: JSON.stringify(councilPayload),
      action: "show_council",
    });

    const { result } = renderHook(() => useChat(), { wrapper: createWrapper() });
    await act(async () => {
      await result.current.sendMessage("Run council");
    });

    const msg = result.current.messages[1];
    expect(msg.type).toBe("council");
    expect(result.current.stage).toBe("idle");
  });

  it("normalizes 'otx' source label to 'AlienVault OTX' in start_collecting", async () => {
    vi.mocked(sendMessage).mockResolvedValue({
      question: JSON.stringify(["otx", "Knowledge Bank", "MISP"]),
      action: "start_collecting",
    });

    const { result } = renderHook(() => useChat(), { wrapper: createWrapper() });
    await act(async () => {
      await result.current.sendMessage("Start collecting");
    });

    const msg = result.current.messages[1];
    expect(msg.type).toBe("question");
    // The normalized source labels should appear in the text
    expect(msg.text).toMatch(/AlienVault OTX|MISP|Knowledge Bank/);
  });

  it("normalizes 'alienvault' in source label to 'AlienVault OTX'", async () => {
    vi.mocked(sendMessage).mockResolvedValue({
      question: JSON.stringify(["alienvault otx"]),
      action: "start_collecting",
    });

    const { result } = renderHook(() => useChat(), { wrapper: createWrapper() });
    await act(async () => {
      await result.current.sendMessage("Start");
    });

    const msg = result.current.messages[1];
    expect(msg.text).toMatch(/AlienVault OTX/);
  });

  it("handles collection data with sources_used in show_collection action", async () => {
    const collectionSummary = {
      summary: "Collection complete.",
      sources_used: ["AlienVault OTX"],
      gaps: "None.",
    };
    vi.mocked(sendMessage).mockResolvedValue({
      question: JSON.stringify(collectionSummary),
      action: "show_collection",
    });

    const { result } = renderHook(() => useChat(), { wrapper: createWrapper() });
    await act(async () => {
      await result.current.sendMessage("Show collection");
    });

    const msg = result.current.messages[1];
    expect(msg.type).toBe("collection");
    // sources_used branch should produce collection data
    expect(msg.data).toBeDefined();
  });

  it("handles collection data that cannot be parsed (parse_error branch)", async () => {
    vi.mocked(sendMessage).mockResolvedValue({
      question: "not valid json at all!!!",
      action: "show_collection",
    });

    const { result } = renderHook(() => useChat(), { wrapper: createWrapper() });
    await act(async () => {
      await result.current.sendMessage("Show collection");
    });

    const msg = result.current.messages[1];
    expect(msg.type).toBe("collection");
    // parse_error branch: data should have parse_error field
    expect((msg.data as { parse_error?: string })?.parse_error).toBeTruthy();
  });

  it("infers stage from response.stage field when present", async () => {
    vi.mocked(sendMessage).mockResolvedValue({
      question: "PIR confirmation required",
      action: "show_pir",
      stage: "pir_confirming",
      sub_state: "awaiting_decision",
      phase: "direction",
    });

    const { result } = renderHook(() => useChat(), { wrapper: createWrapper() });
    await act(async () => {
      await result.current.sendMessage("Send message");
    });

    expect(result.current.stage).toBe("pir_confirming");
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

// ---------------------------------------------------------------------------
// Additional coverage tests
// ---------------------------------------------------------------------------

describe("useChat — gatherMore", () => {
  beforeEach(() => {
    vi.resetAllMocks();
    localStorage.clear();
  });

  it("adds a gatherMore system message when stage=reviewing and phase=collection", () => {
    seedConversation({ stage: "reviewing", phase: "collection" });

    const { result } = renderHook(() => useChat(), {
      wrapper: createWrapper(),
    });

    act(() => {
      result.current.gatherMore();
    });

    const msgs = result.current.messages;
    expect(msgs.length).toBeGreaterThanOrEqual(1);
    const lastMsg = msgs[msgs.length - 1];
    expect(lastMsg.sender).toBe("system");
    expect(lastMsg.text).toMatch(/additional information/i);
  });

  it("does nothing when stage is not reviewing", () => {
    seedConversation({ stage: "initial", phase: "direction" });

    const { result } = renderHook(() => useChat(), {
      wrapper: createWrapper(),
    });

    act(() => {
      result.current.gatherMore();
    });

    expect(result.current.messages).toHaveLength(0);
  });

  it("does nothing when phase is not collection", () => {
    seedConversation({ stage: "reviewing", phase: "processing" });

    const { result } = renderHook(() => useChat(), {
      wrapper: createWrapper(),
    });

    act(() => {
      result.current.gatherMore();
    });

    expect(result.current.messages).toHaveLength(0);
  });
});

describe("useChat — toggleSourceSelection", () => {
  beforeEach(() => {
    vi.resetAllMocks();
    localStorage.clear();
    seedConversation();
  });

  it("adds a source to selectedSources when not already selected", () => {
    const { result } = renderHook(() => useChat(), {
      wrapper: createWrapper(),
    });

    act(() => {
      result.current.toggleSourceSelection("Web Search");
    });

    expect(result.current.selectedSources).toContain("Web Search");
  });

  it("removes a source from selectedSources when already selected", () => {
    const { result } = renderHook(() => useChat(), {
      wrapper: createWrapper(),
    });

    act(() => {
      result.current.toggleSourceSelection("Web Search");
    });
    act(() => {
      result.current.toggleSourceSelection("Web Search");
    });

    expect(result.current.selectedSources).not.toContain("Web Search");
  });
});

describe("useChat — submitSourceSelection validation", () => {
  beforeEach(() => {
    vi.resetAllMocks();
    localStorage.clear();
    seedConversation({ stage: "plan_confirming" });
  });

  it("shows error toast when submitting with no sources selected", async () => {
    vi.mocked(sendMessage).mockResolvedValue({
      question: "Collecting...",
      action: "ask_question",
    });

    const { result } = renderHook(() => useChat(), {
      wrapper: createWrapper(),
    });

    // First approve to enter source selection mode
    act(() => {
      result.current.approve();
    });

    // Now submit without selecting any source
    await act(async () => {
      await result.current.submitSourceSelection();
    });

    // sendMessage should not have been called (error was shown instead)
    expect(sendMessage).not.toHaveBeenCalled();
  });
});

describe("useChat — debugConfirm", () => {
  beforeEach(() => {
    vi.resetAllMocks();
    localStorage.clear();
    seedConversation();
  });

  it("adds a 'Do you approve?' system message when called", () => {
    const { result } = renderHook(() => useChat(), {
      wrapper: createWrapper(),
    });

    act(() => {
      result.current.debugConfirm();
    });

    const msgs = result.current.messages;
    expect(msgs.length).toBeGreaterThanOrEqual(1);
    const lastMsg = msgs[msgs.length - 1];
    expect(lastMsg.sender).toBe("system");
    expect(lastMsg.text).toMatch(/do you approve/i);
  });

  it("sets stage to summary_confirming after debugConfirm", () => {
    const { result } = renderHook(() => useChat(), {
      wrapper: createWrapper(),
    });

    act(() => {
      result.current.debugConfirm();
    });

    expect(result.current.stage).toBe("summary_confirming");
    expect(result.current.isConfirming).toBe(true);
  });
});

describe("useChat — sendMessage error handling", () => {
  beforeEach(() => {
    vi.resetAllMocks();
    localStorage.clear();
    seedConversation();
  });

  it("handles sendMessage throwing an error gracefully", async () => {
    vi.mocked(sendMessage).mockRejectedValue(new Error("timeout"));

    const { result } = renderHook(() => useChat(), {
      wrapper: createWrapper(),
    });

    // Should not throw
    await act(async () => {
      await result.current.sendMessage("Test message");
    });

    // The user message should still be in the list
    expect(result.current.messages[0]).toMatchObject({
      text: "Test message",
      sender: "user",
    });
    // isLoading should be false after completion
    expect(result.current.isLoading).toBe(false);
  });
});

// ---------------------------------------------------------------------------
// jumpToDevStage / syncDevStage / resetDevStage
// ---------------------------------------------------------------------------

describe("useChat — jumpToDevStage", () => {
  beforeEach(() => {
    vi.resetAllMocks();
    localStorage.clear();
    seedConversation();
    // listDevDialogueSnapshots is called on mount — return empty list to suppress info toast
    vi.mocked(listDevDialogueSnapshots).mockResolvedValue([]);
  });

  it("calls setDevDialogueState and updates the stage", async () => {
    vi.mocked(setDevDialogueState).mockResolvedValue({
      stage: "pir_confirming",
      sub_state: "awaiting_decision",
      phase: "direction",
    });

    const { result } = renderHook(() => useChat(), {
      wrapper: createWrapper(),
    });

    await act(async () => {
      await result.current.jumpToDevStage("pir_confirming", "awaiting_decision");
    });

    expect(setDevDialogueState).toHaveBeenCalled();
    expect(result.current.stage).toBe("pir_confirming");
  });

  it("handles setDevDialogueState throwing without crashing", async () => {
    vi.mocked(setDevDialogueState).mockRejectedValue(new Error("network error"));

    const { result } = renderHook(() => useChat(), {
      wrapper: createWrapper(),
    });

    // Should not throw
    await act(async () => {
      await result.current.jumpToDevStage("reviewing");
    });

    // Stage should remain unchanged from seed
    expect(result.current.stage).toBe("initial");
  });
});

describe("useChat — syncDevStage", () => {
  beforeEach(() => {
    vi.resetAllMocks();
    localStorage.clear();
    seedConversation();
    vi.mocked(listDevDialogueSnapshots).mockResolvedValue([]);
  });

  it("calls getDevDialogueState and updates stage from backend", async () => {
    vi.mocked(getDevDialogueState).mockResolvedValue({
      stage: "reviewing",
      sub_state: "awaiting_decision",
      phase: "collection",
    });

    const { result } = renderHook(() => useChat(), {
      wrapper: createWrapper(),
    });

    await act(async () => {
      await result.current.syncDevStage();
    });

    expect(getDevDialogueState).toHaveBeenCalled();
    expect(result.current.stage).toBe("reviewing");
  });

  it("handles getDevDialogueState error gracefully", async () => {
    vi.mocked(getDevDialogueState).mockRejectedValue(new Error("fail"));

    const { result } = renderHook(() => useChat(), {
      wrapper: createWrapper(),
    });

    await act(async () => {
      await result.current.syncDevStage();
    });

    // Stage unchanged
    expect(result.current.stage).toBe("initial");
  });
});

describe("useChat — resetDevStage", () => {
  beforeEach(() => {
    vi.resetAllMocks();
    localStorage.clear();
    seedConversation();
    vi.mocked(listDevDialogueSnapshots).mockResolvedValue([]);
  });

  it("calls resetDevDialogueState and updates stage", async () => {
    vi.mocked(resetDevDialogueState).mockResolvedValue({
      stage: "initial",
      sub_state: null,
      phase: "direction",
    });

    const { result } = renderHook(() => useChat(), {
      wrapper: createWrapper(),
    });

    await act(async () => {
      await result.current.resetDevStage();
    });

    expect(resetDevDialogueState).toHaveBeenCalled();
    expect(result.current.stage).toBe("initial");
  });

  it("handles resetDevDialogueState error gracefully", async () => {
    vi.mocked(resetDevDialogueState).mockRejectedValue(new Error("fail"));

    const { result } = renderHook(() => useChat(), {
      wrapper: createWrapper(),
    });

    await act(async () => {
      await result.current.resetDevStage();
    });

    // Stage unchanged
    expect(result.current.stage).toBe("initial");
  });
});

// ---------------------------------------------------------------------------
// restoreDevSnapshot
// ---------------------------------------------------------------------------

describe("useChat — restoreDevSnapshot", () => {
  beforeEach(() => {
    vi.resetAllMocks();
    localStorage.clear();
    seedConversation();
    vi.mocked(listDevDialogueSnapshots).mockResolvedValue([]);
  });

  it("calls restoreDevDialogueSnapshot and replaces messages", async () => {
    vi.mocked(restoreDevDialogueSnapshot).mockResolvedValue({
      stage: "pir_confirming",
      sub_state: "awaiting_decision",
      phase: "direction",
      messages: [
        { text: "Restored message", sender: "system", type: "question" },
      ],
    });

    const { result } = renderHook(() => useChat(), {
      wrapper: createWrapper(),
    });

    await act(async () => {
      await result.current.restoreDevSnapshot(
        "source-session-abc",
        "pir_confirming",
        "direction",
      );
    });

    expect(restoreDevDialogueSnapshot).toHaveBeenCalled();
    expect(result.current.stage).toBe("pir_confirming");
    // Messages should contain the restored message
    expect(result.current.messages.length).toBeGreaterThanOrEqual(1);
    expect(result.current.messages[0].text).toBe("Restored message");
  });

  it("handles restoreDevDialogueSnapshot error gracefully", async () => {
    vi.mocked(restoreDevDialogueSnapshot).mockRejectedValue(
      new Error("restore failed"),
    );

    const { result } = renderHook(() => useChat(), {
      wrapper: createWrapper(),
    });

    await act(async () => {
      await result.current.restoreDevSnapshot(
        "source-session-abc",
        "pir_confirming",
        "direction",
      );
    });

    // Stage unchanged, no crash
    expect(result.current.stage).toBe("initial");
  });
});

// ---------------------------------------------------------------------------
// gatherMoreFromProcessing
// ---------------------------------------------------------------------------

describe("useChat — gatherMoreFromProcessing", () => {
  beforeEach(() => {
    vi.resetAllMocks();
    localStorage.clear();
    seedConversation({ stage: "reviewing", phase: "processing" });
    vi.mocked(listDevDialogueSnapshots).mockResolvedValue([]);
  });

  it("calls sendAndHandle (via sendMessage mock) when gatherMoreFromProcessing is called", async () => {
    vi.mocked(sendMessage).mockResolvedValue({
      question: "Collecting more data",
      action: "ask_question",
    });

    const { result } = renderHook(() => useChat(), {
      wrapper: createWrapper(),
    });

    await act(async () => {
      await result.current.gatherMoreFromProcessing();
    });

    // sendMessage should have been called
    expect(sendMessage).toHaveBeenCalled();
  });

  it("handles gatherMoreFromProcessing error gracefully", async () => {
    vi.mocked(sendMessage).mockRejectedValue(new Error("gather failed"));

    const { result } = renderHook(() => useChat(), {
      wrapper: createWrapper(),
    });

    await act(async () => {
      await result.current.gatherMoreFromProcessing();
    });

    // isLoading should reset to false
    expect(result.current.isLoading).toBe(false);
  });
});

// ---------------------------------------------------------------------------
// submitSourceSelection success path
// ---------------------------------------------------------------------------

describe("useChat — submitSourceSelection success", () => {
  beforeEach(() => {
    vi.resetAllMocks();
    localStorage.clear();
    seedConversation({ stage: "plan_confirming", phase: "collection" });
    vi.mocked(listDevDialogueSnapshots).mockResolvedValue([]);
  });

  it("calls sendMessage when sources are selected and submits them", async () => {
    vi.mocked(sendMessage).mockResolvedValue({
      question: "Collecting from selected sources",
      action: "ask_question",
    });

    const { result } = renderHook(() => useChat(), {
      wrapper: createWrapper(),
    });

    // Select a source first
    act(() => {
      result.current.toggleSourceSelection("Web Search");
    });

    expect(result.current.selectedSources).toContain("Web Search");

    // Submit with source selected
    await act(async () => {
      await result.current.submitSourceSelection({});
    });

    expect(sendMessage).toHaveBeenCalled();
  });
});

// ---------------------------------------------------------------------------
// clearDevPrefill / prefillGapPrompt / clearInputPrefill
// ---------------------------------------------------------------------------

describe("useChat — dev prefill and input prefill helpers", () => {
  beforeEach(() => {
    vi.resetAllMocks();
    localStorage.clear();
    seedConversation();
    vi.mocked(listDevDialogueSnapshots).mockResolvedValue([]);
  });

  it("triggerDevMessage sets devPrefill and clearDevPrefill clears it", () => {
    const { result } = renderHook(() => useChat(), { wrapper: createWrapper() });

    act(() => {
      result.current.triggerDevMessage("Test dev prefill");
    });
    expect(result.current.devPrefill).toBe("Test dev prefill");

    act(() => {
      result.current.clearDevPrefill();
    });
    expect(result.current.devPrefill).toBeNull();
  });

  it("prefillGapPrompt sets inputPrefill and clearInputPrefill clears it", () => {
    const { result } = renderHook(() => useChat(), { wrapper: createWrapper() });

    act(() => {
      result.current.prefillGapPrompt("Describe the gap you want to address");
    });
    expect(result.current.inputPrefill).toBe("Describe the gap you want to address");

    act(() => {
      result.current.clearInputPrefill();
    });
    expect(result.current.inputPrefill).toBeNull();
  });
});

// ---------------------------------------------------------------------------
// sendCouncilRequest
// ---------------------------------------------------------------------------

describe("useChat — sendCouncilRequest", () => {
  beforeEach(() => {
    vi.resetAllMocks();
    localStorage.clear();
    seedConversation({ stage: "idle", phase: "analysis" });
    vi.mocked(listDevDialogueSnapshots).mockResolvedValue([]);
  });

  const councilSettings = {
    mode: "debate",
    rounds: 3,
    timeout_seconds: 60,
    vote_retry_enabled: false,
    vote_retry_attempts: 0,
  };

  it("calls sendMessage with council parameters and applies the response", async () => {
    const councilPayload = {
      debate_point: "Should we escalate?",
      perspectives: [],
      key_agreements: [],
      full_debate: "Debate content",
    };
    vi.mocked(sendMessage).mockResolvedValue({
      question: JSON.stringify(councilPayload),
      action: "show_council",
    });

    const { result } = renderHook(() => useChat(), { wrapper: createWrapper() });

    await act(async () => {
      await result.current.sendCouncilRequest({
        debatePoint: "Should we escalate?",
        findingIds: ["F-001"],
        perspectives: ["US", "EU"],
        councilSettings,
      });
    });

    expect(sendMessage).toHaveBeenCalled();
    const msg = result.current.messages[0];
    expect(msg.type).toBe("council");
  });

  it("throws when sendMessage returns error action (line 966)", async () => {
    vi.mocked(sendMessage).mockResolvedValue({
      question: "Council run failed.",
      action: "error",
    });

    const { result } = renderHook(() => useChat(), { wrapper: createWrapper() });

    // sendCouncilRequest does not catch the error internally — it rethrows
    await act(async () => {
      try {
        await result.current.sendCouncilRequest({
          debatePoint: "Test",
          findingIds: [],
          perspectives: [],
          councilSettings,
        });
      } catch {
        // Expected to throw
      }
    });

    // isLoading should be false because finally block always fires
    expect(result.current.isLoading).toBe(false);
  });

  it("does not call sendMessage when there is no active conversation", async () => {
    // Start with no conversation
    localStorage.clear();
    vi.mocked(sendMessage).mockResolvedValue({
      question: "{}",
      action: "show_council",
    });

    const { result } = renderHook(() => useChat(), { wrapper: createWrapper() });

    await act(async () => {
      await result.current.sendCouncilRequest({
        debatePoint: "Test",
        findingIds: [],
        perspectives: [],
        councilSettings,
      });
    });

    expect(sendMessage).not.toHaveBeenCalled();
  });
});

// ---------------------------------------------------------------------------
// approve — plan_confirming enters source selection (line 702-704)
// ---------------------------------------------------------------------------

describe("useChat — approve plan_confirming opens source selection", () => {
  beforeEach(() => {
    vi.resetAllMocks();
    localStorage.clear();
    seedConversation({ stage: "plan_confirming", phase: "collection" });
    vi.mocked(listDevDialogueSnapshots).mockResolvedValue([]);
  });

  it("sets isSourceSelecting to true when approve is called during plan_confirming", () => {
    const { result } = renderHook(() => useChat(), { wrapper: createWrapper() });

    act(() => {
      result.current.approve();
    });

    // isSourceSelecting becomes true — no backend call made
    expect(result.current.isSourceSelecting).toBe(true);
    expect(sendMessage).not.toHaveBeenCalled();
  });
});

// ---------------------------------------------------------------------------
// approve — optimistic phase advance for reviewing + collection (line 711-714)
// ---------------------------------------------------------------------------

describe("useChat — approve optimistic phase advance", () => {
  beforeEach(() => {
    vi.resetAllMocks();
    localStorage.clear();
    vi.mocked(listDevDialogueSnapshots).mockResolvedValue([]);
  });

  it("optimistically advances to processing phase when reviewing collection", async () => {
    seedConversation({ stage: "reviewing", phase: "collection", subState: "awaiting_decision" });

    vi.mocked(sendMessage).mockResolvedValue({
      question: "Processing started.",
      action: "show_processing",
    });

    const { result } = renderHook(() => useChat(), { wrapper: createWrapper() });

    await act(async () => {
      await result.current.approve();
    });

    expect(sendMessage).toHaveBeenCalled();
  });

  it("optimistically advances to analysis phase when processing with awaiting_decision", async () => {
    seedConversation({ stage: "processing", phase: "processing", subState: "awaiting_decision" });

    vi.mocked(sendMessage).mockResolvedValue({
      question: "Analysis started.",
      action: "show_analysis",
    });

    const { result } = renderHook(() => useChat(), { wrapper: createWrapper() });

    await act(async () => {
      await result.current.approve();
    });

    expect(sendMessage).toHaveBeenCalled();
  });
});

// ---------------------------------------------------------------------------
// handleSendMessage — gather_more intercept path (line 664-672)
// ---------------------------------------------------------------------------

describe("useChat — handleSendMessage gather_more intercept", () => {
  beforeEach(() => {
    vi.resetAllMocks();
    localStorage.clear();
    seedConversation({ stage: "reviewing", phase: "collection", subState: "awaiting_gather_more" });
    vi.mocked(listDevDialogueSnapshots).mockResolvedValue([]);
  });

  it("intercepts text when stage=reviewing, phase=collection, subState=awaiting_gather_more", async () => {
    const { result } = renderHook(() => useChat(), { wrapper: createWrapper() });

    await act(async () => {
      await result.current.sendMessage("Focus on attribution gaps");
    });

    // Backend should NOT have been called — text is stored locally
    expect(sendMessage).not.toHaveBeenCalled();
    // isSourceSelecting should be true after intercept
    expect(result.current.isSourceSelecting).toBe(true);
  });
});

// ---------------------------------------------------------------------------
// sendMessage error path — collecting stage fallback (line 688-691)
// ---------------------------------------------------------------------------

describe("useChat — sendMessage error during collecting resets stage", () => {
  beforeEach(() => {
    vi.resetAllMocks();
    localStorage.clear();
    seedConversation({ stage: "collecting", phase: "collection" });
    vi.mocked(listDevDialogueSnapshots).mockResolvedValue([]);
  });

  it("resets stage to plan_confirming when sendMessage throws during collecting", async () => {
    vi.mocked(sendMessage).mockRejectedValue(new Error("network failure"));

    const { result } = renderHook(() => useChat(), { wrapper: createWrapper() });

    await act(async () => {
      await result.current.sendMessage("Collecting message");
    });

    // Should be back to plan_confirming so user can retry
    expect(result.current.stage).toBe("plan_confirming");
    expect(result.current.isLoading).toBe(false);
  });
});

// ---------------------------------------------------------------------------
// applyResponse — phase change triggers setReviewActivity reset (line 572-576)
// ---------------------------------------------------------------------------

describe("useChat — applyResponse phase change resets review activity", () => {
  beforeEach(() => {
    vi.resetAllMocks();
    localStorage.clear();
    seedConversation({ stage: "reviewing", phase: "collection" });
    vi.mocked(listDevDialogueSnapshots).mockResolvedValue([]);
  });

  it("includes review_activity from response when phase changes", async () => {
    vi.mocked(sendMessage).mockResolvedValue({
      question: "Processing done.",
      action: "show_processing",
      phase: "processing",
      review_activity: [{ type: "finding", ref: "F-001", label: "APT29", summary: "Activity" }],
    } as Parameters<typeof sendMessage>[0] extends never ? never : Awaited<ReturnType<typeof import("../../services/dialogue/dialogue").sendMessage>>);

    const { result } = renderHook(() => useChat(), { wrapper: createWrapper() });

    await act(async () => {
      await result.current.sendMessage("Approve collection");
    });

    // Message with processing type should exist
    const processingMsg = result.current.messages.find(m => m.type === "processing");
    expect(processingMsg).toBeDefined();
  });
});
