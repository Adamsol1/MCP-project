import { useEffect, useMemo, useState } from "react";
import {
  getDevDialogueState,
  resetDevDialogueState,
  sendMessage,
  setDevDialogueState,
  type DialogueApiResponse,
  type DialogueSendOptions,
} from "../services/dialogue";
import type {
  DialogueAction,
  DialogueStage,
  DialogueSubState,
} from "../types/dialogue";
import { useConversation } from "./useConversation";
import { useToast } from "./useToast";
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
} from "../types/conversation";
import { useSettings } from "../contexts/SettingsContext/SettingsContext";

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

function parsePlanData(raw: string): CollectionPlanData {
  const parsed = extractJsonObject(raw);
  if (!parsed) {
    return { plan: raw, suggested_sources: [] };
  }

  const planValue = parsed.plan;
  const plan =
    typeof planValue === "string"
      ? planValue
      : JSON.stringify(planValue ?? parsed, null, 2);

  const rawSteps = parsed.steps;
  const steps: CollectionPlanStep[] | undefined =
    Array.isArray(rawSteps)
      ? (rawSteps as unknown[]).filter(
          (s): s is CollectionPlanStep =>
            typeof (s as CollectionPlanStep)?.title === "string" &&
            typeof (s as CollectionPlanStep)?.description === "string",
        )
      : undefined;

  return {
    plan,
    steps: steps && steps.length > 0 ? steps : undefined,
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
  return ACTION_TO_MESSAGE_TYPE[response.action];
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

  if (response.action === "start_collecting") {
    const sources = parseSuggestedSources(response.question);
    if (sources.length > 0) {
      message.text = `Collecting from: ${sources.join(", ")}`;
    } else {
      message.text = "Collecting from selected sources...";
    }
    return message;
  }

  if (messageType === "summary" || messageType === "pir") {
    const parsed = tryParseJson<SummaryData | PirData | CollectionSummaryData>(
      response.question,
    );
    if (parsed) {
      message.data = parsed;
    }
  }

  if (messageType === "collection") {
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
  }

  if (messageType === "plan") {
    message.data = parsePlanData(response.question);
  }

  if (messageType === "processing") {
    const parsed = tryParseJson<ProcessingData>(response.question);
    if (parsed) {
      message.data = parsed;
    }
  }

  if (messageType === "suggested_sources") {
    const sources = parseSuggestedSources(response.question);
    if (sources.length > 0) {
      message.data = sources as SuggestedSourcesData;
      message.text = `Suggested sources: ${sources.join(", ")}`;
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

export function useChat() {
  const { activeConversation, createNewConversation, addMessage, setStage } =
    useConversation();
  const { settings } = useSettings();
  const { success, info, error } = useToast();
  const [isLoading, setIsLoading] = useState(false);
  const [isDecisionPending, setIsDecisionPending] = useState(false);
  const [devPrefill, setDevPrefill] = useState<string | null>(null);
  const [suggestedSources, setSuggestedSources] = useState<string[]>([]);
  const [selectedSources, setSelectedSources] = useState<string[]>([]);
  const [localSourceContext, setLocalSourceContext] = useState<"plan" | "gather_more" | null>(null);
  const [pendingGatherMoreText, setPendingGatherMoreText] = useState<string | null>(null);

  const messages = activeConversation?.messages ?? [];
  const stage = activeConversation?.stage ?? "initial";
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
      if (message.type === "plan" && message.data && "suggested_sources" in message.data) {
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
  ) => {
    addMessage(buildSystemMessage(response), conversationId);

    const next = inferStageFromResponse(
      response,
      fallbackStage,
      fallbackSubState,
    );
    setStage(next.stage, next.subState);
  };

  const sendAndHandle = async (
    conversationId: string,
    sessionId: string,
    message: string,
    approved: boolean | undefined,
    options: DialogueSendOptions,
    fallbackStage: DialogueStage,
    fallbackSubState: DialogueSubState,
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

    applyResponse(response, conversationId, fallbackStage, fallbackSubState);

    if (response.action !== "start_collecting") {
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
    applyResponse(collectResponse, conversationId, "collecting", null);
  };

  const handleSendMessage = async (text: string, approved?: boolean) => {
    const conversation = activeConversation ?? createNewConversation();

    addMessage(
      { id: crypto.randomUUID(), text, sender: "user" },
      conversation.id,
    );

    // Intercept gather_more text — store locally and show source selection instead of backend call
    if (stage === "reviewing" && subState === "awaiting_gather_more") {
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
        conversation.perspectives,
      );
    } catch (e) {
      error(`Message failed: ${e instanceof Error ? e.message : String(e)}`);
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
        activeConversation.perspectives,
      );
      success("Request approved");
    } catch (e) {
      error(`Approval failed: ${e instanceof Error ? e.message : String(e)}`);
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
        activeConversation.perspectives,
      );
    } catch (e) {
      error(`Gather more failed: ${e instanceof Error ? e.message : String(e)}`);
    } finally {
      setIsLoading(false);
    }
  };

  const gatherMore = () => {
    if (!activeConversation || stage !== "reviewing") {
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
        activeConversation.perspectives,
      );
    } catch (e) {
      error(
        `Failed to start collection: ${
          e instanceof Error ? e.message : String(e)
        }`,
      );
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
    const conversation = activeConversation ?? createNewConversation();
    addMessage(
      {
        id: crypto.randomUUID(),
        text: "Summary: Investigate APT29 activity targeting EU infrastructure over the last 6 months. Do you approve?",
        sender: "system",
      },
      conversation.id,
    );
    setStage("summary_confirming", "awaiting_decision");
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
      setStage(response.stage, response.sub_state);
      info(`Moved to stage: ${response.stage}`);
    } catch {
      error("Failed to set dev stage");
    }
  };

  const syncDevStage = async () => {
    if (!activeConversation) return;
    try {
      const response = await getDevDialogueState(activeConversation.sessionId);
      setStage(response.stage, response.sub_state);
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
      setStage(response.stage, response.sub_state);
      info("Reset stage to initial");
    } catch {
      error("Failed to reset dev stage");
    }
  };

  return {
    messages,
    sendMessage: handleSendMessage,
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
