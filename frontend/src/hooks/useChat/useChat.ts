import { useEffect, useMemo, useState } from "react";
import {
  getDevDialogueState,
  resetDevDialogueState,
  sendMessage,
  setDevDialogueState,
  type CouncilRunSettings,
  type DialogueApiResponse,
  type DialogueSendOptions,
} from "../../services/dialogue/dialogue";
import type {
  DialogueAction,
  DialoguePhase,
  DialogueStage,
  DialogueSubState,
} from "../../types/dialogue";
import { useConversation } from "../useConversation/useConversation";
import { useToast } from "../useToast/useToast";
import type {
  CollectionPlanData,
  CollectionPlanStep,
  CollectionSummaryData,
  CollectionDisplayData,
  Message,
  PirData,
  ProcessingData,
  SuggestedSourcesData,
  SummaryData,
} from "../../types/conversation";
import type { AnalysisDraftResponse, CouncilNote } from "../../types/analysis";
import { useSettings } from "../../contexts/SettingsContext/SettingsContext";

const DECISION_STAGES: DialogueStage[] = [
  "summary_confirming",
  "pir_confirming",
  "plan_confirming",
  "reviewing",
  "processing",
];

const ACTION_TO_MESSAGE_TYPE: Record<
  DialogueAction,
  NonNullable<Message["type"]>
> = {
  ask_question: "question",
  show_summary: "summary",
  show_pir: "pir",
  max_questions: "summary",
  show_plan: "plan",
  start_collecting: "question",
  show_collection: "collection",
  show_processing: "processing",
  show_analysis: "analysis",
  show_council: "council",
  select_gaps: "question",
  error: "error",
  complete: "complete",
};

function isDecisionStage(stage: DialogueStage): boolean {
  return DECISION_STAGES.includes(stage);
}

function defaultSubStateForStage(stage: DialogueStage): DialogueSubState {
  return isDecisionStage(stage) ? "awaiting_decision" : null;
}

function tryParseJson<T>(raw: string): T | null {
  try {
    return JSON.parse(raw) as T;
  } catch {
    return null;
  }
}

function extractJsonObject(raw: string): Record<string, unknown> | null {
  const direct = tryParseJson<unknown>(raw);
  if (direct && typeof direct === "object" && !Array.isArray(direct)) {
    return direct as Record<string, unknown>;
  }

  const codeBlockMatch = raw.match(/```(?:json)?\s*([\s\S]*?)\s*```/i);
  if (codeBlockMatch?.[1]) {
    const fromCodeBlock = tryParseJson<unknown>(codeBlockMatch[1]);
    if (
      fromCodeBlock &&
      typeof fromCodeBlock === "object" &&
      !Array.isArray(fromCodeBlock)
    ) {
      return fromCodeBlock as Record<string, unknown>;
    }
  }

  const start = raw.indexOf("{");
  const end = raw.lastIndexOf("}");
  if (start >= 0 && end > start) {
    const candidate = raw.slice(start, end + 1);
    const parsed = tryParseJson<unknown>(candidate);
    if (parsed && typeof parsed === "object" && !Array.isArray(parsed)) {
      return parsed as Record<string, unknown>;
    }
  }

  return null;
}

function normalizeSourceLabel(raw: string): string {
  const value = raw.trim();
  const lower = value.toLowerCase();
  if (lower === "otx" || lower.includes("alienvault")) {
    return "AlienVault OTX";
  }
  if (lower.includes("knowledge") && lower.includes("bank")) {
    return "Internal Knowledge Bank";
  }
  if (lower.includes("misp")) {
    return "MISP";
  }
  return value;
}

function parseSourcesFromUnknown(raw: unknown): string[] {
  if (!Array.isArray(raw)) return [];
  const deduped: string[] = [];
  raw.forEach((item) => {
    if (typeof item !== "string") return;
    const normalized = normalizeSourceLabel(item);
    if (!deduped.includes(normalized)) {
      deduped.push(normalized);
    }
  });
  return deduped;
}

function parseStepsFromPlanText(plan: string): CollectionPlanStep[] | undefined {
  // Split on numbered list boundaries: "N." at the start of a line
  const chunks = plan.split(/(?=^\d+\.[ \t])/m).map((s) => s.trim()).filter(Boolean);
  if (chunks.length < 2) return undefined;

  const steps: CollectionPlanStep[] = [];
  for (const chunk of chunks) {
    // Extract bold title: "N. **Title:**"
    const boldMatch = chunk.match(/^\d+\.\s+\*\*([^*]+?)\*\*:?\s*([\s\S]*)$/);
    // Extract plain title: "N. Title:"  (colon required to avoid false positives)
    const plainMatch = chunk.match(/^\d+\.\s+([^\n:]{3,80}):\s*([\s\S]*)$/);

    const m = boldMatch ?? plainMatch;
    if (!m) continue;

    const title = m[1].trim().replace(/:$/, "");
    // Flatten sub-bullets into a single readable description
    const rawDesc = m[2].trim();
    const description = rawDesc
      .replace(/\*\*([^*]+)\*\*/g, "$1")   // strip bold markers
      .replace(/^\s*[\*\-]\s+/gm, "")       // strip bullet chars
      .replace(/\n+/g, " ")                  // collapse newlines
      .trim();

    if (title && description) steps.push({ title, description });
  }

  return steps.length > 0 ? steps : undefined;
}

function parsePlanData(raw: string): CollectionPlanData {
  const parsed = extractJsonObject(raw);
  if (!parsed) {
    return { plan: raw, steps: parseStepsFromPlanText(raw), suggested_sources: [] };
  }

  const planValue = parsed.plan;
  const plan =
    typeof planValue === "string"
      ? planValue
      : JSON.stringify(planValue ?? parsed, null, 2);

  const rawSteps = parsed.steps;
  const jsonSteps: CollectionPlanStep[] | undefined = Array.isArray(rawSteps)
    ? (rawSteps as unknown[]).filter(
        (s): s is CollectionPlanStep =>
          typeof (s as CollectionPlanStep)?.title === "string" &&
          typeof (s as CollectionPlanStep)?.description === "string",
      )
    : undefined;

  const steps =
    jsonSteps && jsonSteps.length > 0
      ? jsonSteps
      : parseStepsFromPlanText(plan);

  return {
    plan,
    steps,
    suggested_sources: parseSourcesFromUnknown(parsed.suggested_sources),
  };
}

function parseSuggestedSources(raw: string): string[] {
  const parsed = tryParseJson<unknown>(raw);
  if (
    Array.isArray(parsed) &&
    parsed.every((item) => typeof item === "string")
  ) {
    return parseSourcesFromUnknown(parsed);
  }
  const planData = parsePlanData(raw);
  if (planData.suggested_sources.length > 0) {
    return planData.suggested_sources;
  }
  return [];
}

function resolveMessageType(
  response: DialogueApiResponse,
): Message["type"] | undefined {
  return (ACTION_TO_MESSAGE_TYPE as Record<string, NonNullable<Message["type"]>>)[response.action];
}

function inferStageFromResponse(
  response: DialogueApiResponse,
  fallbackStage: DialogueStage,
  fallbackSubState: DialogueSubState,
): {
  stage: DialogueStage;
  subState: DialogueSubState;
} {
  if (response.stage) {
    return {
      stage: response.stage,
      subState: response.sub_state ?? defaultSubStateForStage(response.stage),
    };
  }

  if (
    response.action === "show_summary" ||
    response.action === "max_questions"
  ) {
    return { stage: "summary_confirming", subState: "awaiting_decision" };
  }
  if (response.action === "show_pir") {
    return { stage: "pir_confirming", subState: "awaiting_decision" };
  }
  if (response.action === "show_plan") {
    return { stage: "plan_confirming", subState: "awaiting_decision" };
  }
  if (response.action === "start_collecting") {
    return { stage: "collecting", subState: null };
  }
  if (response.action === "show_collection") {
    return { stage: "reviewing", subState: "awaiting_decision" };
  }
  if (response.action === "show_processing") {
    return { stage: "processing", subState: "awaiting_decision" };
  }
  if (response.action === "show_analysis") {
    return { stage: "pending", subState: null };
  }
  if (response.action === "show_council") {
    return { stage: "idle", subState: null };
  }
  if (response.action === "select_gaps") {
    return { stage: "reviewing", subState: "awaiting_gather_more" };
  }
  if (response.action === "complete") {
    return { stage: "complete", subState: null };
  }
  if (response.action === "ask_question") {
    return { stage: "gathering", subState: null };
  }
  return { stage: fallbackStage, subState: fallbackSubState };
}

function inferPhaseFromResponse(
  response: DialogueApiResponse,
  stage: DialogueStage,
  fallbackPhase: DialoguePhase,
): DialoguePhase {
  if (response.phase) {
    return response.phase;
  }

  switch (stage) {
    case "planning":
    case "plan_confirming":
    case "source_selecting":
    case "collecting":
      return "collection";
    case "reviewing":
      return response.action === "show_collection" || response.action === "select_gaps"
        ? "collection"
        : "processing";
    case "processing":
    case "complete":
      return "processing";
    case "initial":
    case "gathering":
    case "summary_confirming":
    case "pir_confirming":
    default:
      return fallbackPhase;
  }
}

function buildSystemMessage(response: DialogueApiResponse): Message {
  const message: Message = {
    id: crypto.randomUUID(),
    text: response.question,
    sender: "system",
  };

  const messageType = resolveMessageType(response);
  if (messageType) {
    message.type = messageType;
  }

  switch (messageType) {
    case "question":
      if (response.action === "start_collecting") {
        const sources = parseSuggestedSources(response.question);
        message.text =
          sources.length > 0
            ? `Collecting from: ${sources.join(", ")}`
            : "Collecting from selected sources...";
      }
      break;

    case "summary":
    case "pir": {
      const parsed = tryParseJson<SummaryData | PirData | CollectionSummaryData>(
        response.question,
      );
      if (parsed) {
        message.data = parsed;
      }
      break;
    }

    case "plan":
      message.data = parsePlanData(response.question);
      break;

    case "collection": {
      const parsed = tryParseJson<unknown>(response.question);
      if (parsed && typeof parsed === "object" && parsed !== null) {
        if (
          "collected_data" in parsed &&
          Array.isArray((parsed as Record<string, unknown>).collected_data)
        ) {
          message.data = parsed as CollectionDisplayData;
        } else if ("sources_used" in parsed) {
          message.data = parsed as CollectionSummaryData;
        }
      }
      // Prevent raw JSON dump in chat — if parsing failed or structure didn't match,
      // create a minimal display payload with parse_error so the component handles it.
      if (!message.data) {
        message.data = {
          collected_data: [],
          source_summary: [],
          parse_error: "Collection data could not be parsed for display.",
        } as CollectionDisplayData;
      }
      message.text = "Collection complete";
      break;
    }

    case "processing": {
      message.text = "Processing complete — results are ready for review.";
      const parsed = extractJsonObject(response.question) as ProcessingData | null;
      if (parsed && "findings" in parsed) {
        message.data = parsed;
      }
      break;
    }

    case "analysis": {
      const parsed = tryParseJson<AnalysisDraftResponse>(response.question);
      if (parsed) {
        message.data = parsed;
      }
      message.text = "Analysis complete";
      break;
    }

    case "council": {
      const parsed = tryParseJson<CouncilNote>(response.question);
      if (parsed) {
        message.data = parsed;
      }
      message.text = "Council deliberation complete";
      break;
    }

    case "suggested_sources": {
      const sources = parseSuggestedSources(response.question);
      if (sources.length > 0) {
        message.data = sources as SuggestedSourcesData;
        message.text = `Suggested sources: ${sources.join(", ")}`;
      }
      break;
    }
  }

  return message;
}

function getFeedbackPrompt(stage: DialogueStage): string {
  if (stage === "summary_confirming") {
    return "What would you like to change in the summary?";
  }
  if (stage === "pir_confirming") {
    return "What would you like to change in the PIRs?";
  }
  if (stage === "plan_confirming") {
    return "What should be changed in the collection plan?";
  }
  return "What should be modified in the collected summary?";
}

export function useChat(initialPerspectives?: string[]) {
  const { activeConversation, createNewConversation, addMessage, setStage } =
    useConversation();
  const { settings } = useSettings();
  const { success, info, error } = useToast();
  const [isLoading, setIsLoading] = useState(false);
  const [isDecisionPending, setIsDecisionPending] = useState(false);
  const [devPrefill, setDevPrefill] = useState<string | null>(null);
  const [suggestedSources, setSuggestedSources] = useState<string[]>([]);
  const [selectedSources, setSelectedSources] = useState<string[]>([]);
  const [localSourceContext, setLocalSourceContext] = useState<
    "plan" | "gather_more" | null
  >(null);
  const [pendingGatherMoreText, setPendingGatherMoreText] = useState<
    string | null
  >(null);

  const messages = useMemo(
    () => activeConversation?.messages ?? [],
    [activeConversation?.messages],
  );
  const stage = activeConversation?.stage ?? "initial";
  const phase = activeConversation?.phase ?? "direction";
  const subState = activeConversation?.subState ?? null;
  const isConfirming =
    isDecisionStage(stage) &&
    subState === "awaiting_decision" &&
    !isDecisionPending;
  const isSourceSelecting = localSourceContext !== null;
  const isCollecting = stage === "collecting";

  const fallbackSuggestedSources = useMemo(() => {
    for (let i = messages.length - 1; i >= 0; i -= 1) {
      const message = messages[i];
      if (message.type === "suggested_sources" && Array.isArray(message.data)) {
        return message.data as SuggestedSourcesData;
      }
      if (
        message.type === "plan" &&
        message.data &&
        "suggested_sources" in message.data
      ) {
        return (message.data as CollectionPlanData).suggested_sources;
      }
    }
    return [] as string[];
  }, [messages]);

  const availableSources =
    suggestedSources.length > 0 ? suggestedSources : fallbackSuggestedSources;

  useEffect(() => {
    if (availableSources.length === 0) {
      setSelectedSources([]);
      return;
    }
    setSelectedSources((previous) => {
      const stillValid = previous.filter((source) =>
        availableSources.includes(source),
      );
      return stillValid.length > 0 ? stillValid : [...availableSources];
    });
  }, [availableSources]);

  useEffect(() => {
    setSuggestedSources([]);
    setSelectedSources([]);
    setLocalSourceContext(null);
    setPendingGatherMoreText(null);
  }, [activeConversation?.id]);

  const applyResponse = (
    response: DialogueApiResponse,
    conversationId: string,
    fallbackStage: DialogueStage,
    fallbackSubState: DialogueSubState,
    fallbackPhase: DialoguePhase,
  ) => {
    addMessage(buildSystemMessage(response), conversationId);

    const next = inferStageFromResponse(
      response,
      fallbackStage,
      fallbackSubState,
    );
    const nextPhase = inferPhaseFromResponse(response, next.stage, fallbackPhase);
    setStage(next.stage, next.subState, nextPhase);
  };

  const sendAndHandle = async (
    conversationId: string,
    sessionId: string,
    message: string,
    approved: boolean | undefined,
    options: DialogueSendOptions,
    fallbackStage: DialogueStage,
    fallbackSubState: DialogueSubState,
    fallbackPhase: DialoguePhase,
    perspectives: string[],
  ) => {
    const response = await sendMessage(
      message,
      sessionId,
      perspectives,
      approved,
      settings.aiLanguage,
      settings.inputParameters.timeframe,
      options,
    );

    if (response.action === "start_collecting") {
      // Skip the "Collecting from: ..." message — the Collection Results card
      // already shows the sources used.  Just advance the stage.
      setStage("collecting", null, "collection");
    } else {
      applyResponse(
        response,
        conversationId,
        fallbackStage,
        fallbackSubState,
        fallbackPhase,
      );
      return;
    }

    const collectResponse = await sendMessage(
      "collect",
      sessionId,
      perspectives,
      undefined,
      settings.aiLanguage,
      settings.inputParameters.timeframe,
    );

    if (collectResponse.action === "error") {
      const errorStage: DialogueStage =
        collectResponse.stage === "collecting"
          ? "plan_confirming"
          : (collectResponse.stage ?? "plan_confirming");
      applyResponse(
        collectResponse,
        conversationId,
        errorStage,
        "awaiting_decision",
        "collection",
      );
    } else {
      applyResponse(collectResponse, conversationId, "collecting", null, "collection");
    }
  };

  const handleSendMessage = async (text: string, approved?: boolean) => {
    const conversation =
      activeConversation ?? createNewConversation(initialPerspectives);

    addMessage(
      { id: crypto.randomUUID(), text, sender: "user" },
      conversation.id,
    );

    // Intercept gather_more text — store locally and show source selection instead of backend call
    if (
      stage === "reviewing" &&
      phase === "collection" &&
      subState === "awaiting_gather_more"
    ) {
      setPendingGatherMoreText(text);
      setLocalSourceContext("gather_more");
      return;
    }

    setIsLoading(true);
    try {
      await sendAndHandle(
        conversation.id,
        conversation.sessionId,
        text,
        approved,
        {},
        stage,
        subState,
        conversation.phase,
        conversation.perspectives,
      );
    } catch (e) {
      error(`Message failed: ${e instanceof Error ? e.message : String(e)}`);
      if (activeConversation?.stage === "collecting") {
        setStage("plan_confirming", "awaiting_decision", "collection");
      }
    } finally {
      setIsLoading(false);
    }
  };

  const approve = async () => {
    if (!activeConversation) return;

    // For plan_confirming: show local source selection instead of calling backend
    if (stage === "plan_confirming") {
      setLocalSourceContext("plan");
      return;
    }

    setIsDecisionPending(true);
    setIsLoading(true);
    try {
      await sendAndHandle(
        activeConversation.id,
        activeConversation.sessionId,
        "approve",
        true,
        {},
        stage,
        subState,
        activeConversation.phase,
        activeConversation.perspectives,
      );
      success("Request approved");
    } catch (e) {
      error(`Approval failed: ${e instanceof Error ? e.message : String(e)}`);
      if (activeConversation?.stage === "collecting") {
        setStage("plan_confirming", "awaiting_decision", "collection");
      }
    } finally {
      setIsLoading(false);
      setIsDecisionPending(false);
    }
  };

  const reject = () => {
    if (!activeConversation || !isDecisionStage(stage)) {
      return;
    }

    addMessage(
      {
        id: crypto.randomUUID(),
        text: getFeedbackPrompt(stage),
        sender: "system",
      },
      activeConversation.id,
    );

    setStage(stage, "awaiting_modifications");
    info("Add your feedback in chat.");
  };

  const gatherMoreFromProcessing = async () => {
    if (!activeConversation) return;
    setIsLoading(true);
    try {
      await sendAndHandle(
        activeConversation.id,
        activeConversation.sessionId,
        "",
        undefined,
        { gatherMore: true },
        stage,
        subState,
        activeConversation.phase,
        activeConversation.perspectives,
      );
    } catch (e) {
      error(
        `Gather more failed: ${e instanceof Error ? e.message : String(e)}`,
      );
    } finally {
      setIsLoading(false);
    }
  };

  const gatherMore = () => {
    if (!activeConversation || stage !== "reviewing" || phase !== "collection") {
      return;
    }

    addMessage(
      {
        id: crypto.randomUUID(),
        text: "What additional information should I gather?",
        sender: "system",
      },
      activeConversation.id,
    );
    setStage("reviewing", "awaiting_gather_more");
    info("Describe what to gather more on.");
  };

  const toggleSourceSelection = (source: string) => {
    setSelectedSources((current) => {
      if (current.includes(source)) {
        return current.filter((item) => item !== source);
      }
      return [...current, source];
    });
  };

  const submitSourceSelection = async () => {
    if (!activeConversation) return;
    if (selectedSources.length === 0) {
      error("Select at least one source to continue.");
      return;
    }

    const isGatherMore = localSourceContext === "gather_more";
    const message = isGatherMore ? (pendingGatherMoreText ?? "") : "approve";
    const approved = isGatherMore ? undefined : true;
    const options = isGatherMore
      ? { gatherMore: true, selectedSources }
      : { selectedSources };

    setLocalSourceContext(null);
    setPendingGatherMoreText(null);

    setIsLoading(true);
    try {
      await sendAndHandle(
        activeConversation.id,
        activeConversation.sessionId,
        message,
        approved,
        options,
        stage,
        subState,
        activeConversation.phase,
        activeConversation.perspectives,
      );
    } catch (e) {
      error(
        `Failed to start collection: ${
          e instanceof Error ? e.message : String(e)
        }`,
      );
      if (activeConversation?.stage === "collecting") {
        setStage("plan_confirming", "awaiting_decision", "collection");
      }
    } finally {
      setIsLoading(false);
    }
  };

  const triggerDevMessage = (text: string) => {
    setDevPrefill(text);
  };

  const clearDevPrefill = () => {
    setDevPrefill(null);
  };

  const debugConfirm = () => {
    const conversation =
      activeConversation ?? createNewConversation(initialPerspectives);
    addMessage(
      {
        id: crypto.randomUUID(),
        text: "Summary: Investigate APT29 activity targeting EU infrastructure over the last 6 months. Do you approve?",
        sender: "system",
      },
      conversation.id,
    );
    setStage("summary_confirming", "awaiting_decision", "direction");
  };

  const jumpToDevStage = async (
    nextStage: DialogueStage,
    nextSubState: DialogueSubState = "awaiting_decision",
  ) => {
    if (!activeConversation) return;
    try {
      const response = await setDevDialogueState(
        activeConversation.sessionId,
        nextStage,
        nextSubState,
      );
      setStage(
        response.stage,
        response.sub_state ?? defaultSubStateForStage(response.stage),
        response.phase,
      );
      info(`Moved to stage: ${response.stage}`);
    } catch {
      error("Failed to set dev stage");
    }
  };

  const syncDevStage = async () => {
    if (!activeConversation) return;
    try {
      const response = await getDevDialogueState(activeConversation.sessionId);
      setStage(
        response.stage,
        response.sub_state ?? defaultSubStateForStage(response.stage),
        response.phase,
      );
      info(`Synced stage: ${response.stage}`);
    } catch {
      error("Failed to sync dev stage");
    }
  };

  const resetDevStage = async () => {
    if (!activeConversation) return;
    try {
      const response = await resetDevDialogueState(
        activeConversation.sessionId,
      );
      setStage(
        response.stage,
        response.sub_state ?? defaultSubStateForStage(response.stage),
        response.phase,
      );
      info("Reset stage to initial");
    } catch {
      error("Failed to reset dev stage");
    }
  };

  const sendCouncilRequest = async (params: {
    debatePoint: string;
    findingIds: string[];
    perspectives: string[];
    councilSettings: CouncilRunSettings;
  }) => {
    if (!activeConversation) return;
    setIsLoading(true);
    try {
      const response = await sendMessage(
        "",
        activeConversation.sessionId,
        activeConversation.perspectives,
        undefined,
        settings.aiLanguage,
        "",
        {
          councilDebatePoint: params.debatePoint,
          councilFindingIds: params.findingIds,
          councilPerspectives: params.perspectives,
          councilSettings: params.councilSettings,
        },
      );
      applyResponse(response, activeConversation.id, "idle", null, "analysis");
    } finally {
      setIsLoading(false);
    }
  };

  return {
    messages,
    sendMessage: handleSendMessage,
    sendCouncilRequest,
    isConfirming,
    stage,
    subState,
    isLoading,
    isSourceSelecting,
    isCollecting,
    availableSources,
    selectedSources,
    approve,
    reject,
    gatherMore,
    gatherMoreFromProcessing,
    toggleSourceSelection,
    submitSourceSelection,
    debugConfirm,
    jumpToDevStage,
    syncDevStage,
    resetDevStage,
    devPrefill,
    triggerDevMessage,
    clearDevPrefill,
  };
}
