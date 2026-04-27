import { useEffect, useMemo, useState } from "react";
import {
  getDevDialogueState,
  listDevDialogueSnapshots,
  resetDevDialogueState,
  restoreDevDialogueSnapshot,
  sendMessage,
  setDevDialogueState,
  type CouncilRunSettings,
  type DialogueApiResponse,
  type DialogueDevSnapshot,
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
import { useWorkspace } from "../../contexts/WorkspaceContext/WorkspaceContext";
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
import type { AnalysisResponse, CouncilNote } from "../../types/analysis";
import { useSettings } from "../../contexts/SettingsContext/SettingsContext";
import { useT, type Translations } from "../../i18n/useT";

let didRequestInitialDevSnapshots = false;

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
    return "Knowledge Bank";
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

  // Aggregate suggested_sources: prefer per-step sources (deduplicated union),
  // fall back to top-level suggested_sources for legacy payloads.
  const stepSources: string[] =
    steps && steps.some((s) => s.suggested_sources && s.suggested_sources.length > 0)
      ? [...new Set(steps.flatMap((s) => s.suggested_sources ?? []))]
      : [];
  const globalSources = parseSourcesFromUnknown(parsed.suggested_sources);
  const suggested_sources = stepSources.length > 0 ? stepSources : globalSources;

  return {
    plan,
    steps,
    suggested_sources,
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

function translateBackendError(raw: string, t: Translations): string {
  const mapping: Record<string, string> = {
    "Collection failed": t.collectionFailed,
  };
  return mapping[raw.trim()] ?? raw;
}

function buildSystemMessage(
  response: DialogueApiResponse,
  t: Translations,
): Message {
  const text =
    response.action === "error"
      ? translateBackendError(response.question, t)
      : response.question;
  const message: Message = {
    id: crypto.randomUUID(),
    text,
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
            ? t.collectingFrom(sources.join(", "))
            : t.collectingFromSelected;
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
      message.text = t.collectionComplete;
      break;
    }

    case "processing": {
      message.text = t.processingComplete;
      const parsed = extractJsonObject(response.question) as ProcessingData | null;
      if (parsed && "findings" in parsed) {
        message.data = parsed;
      }
      break;
    }

    case "analysis": {
      const parsed = tryParseJson<AnalysisResponse>(response.question);
      if (parsed) {
        message.data = parsed;
      }
      message.text = t.analysisComplete;
      break;
    }

    case "council": {
      const parsed = tryParseJson<CouncilNote>(response.question);
      if (parsed) {
        message.data = parsed;
      }
      message.text = t.councilDeliberationComplete;
      break;
    }

    case "suggested_sources": {
      const sources = parseSuggestedSources(response.question);
      if (sources.length > 0) {
        message.data = sources as SuggestedSourcesData;
        message.text = t.suggestedSourcesText(sources.join(", "));
      }
      break;
    }
  }

  return message;
}

function getFeedbackPrompt(stage: DialogueStage, t: Translations): string {
  if (stage === "summary_confirming") {
    return t.feedbackSummary;
  }
  if (stage === "pir_confirming") {
    return t.feedbackPir;
  }
  if (stage === "plan_confirming") {
    return t.feedbackPlan;
  }
  return t.feedbackCollection;
}

export function useChat(initialPerspectives?: string[]) {
  const {
    activeConversation,
    createNewConversation,
    addMessage,
    replaceMessages,
    setStage,
  } = useConversation();
  const { settings } = useSettings();
  const t = useT();
  const { success, info, error } = useToast();
  const { setReviewActivity } = useWorkspace();
  const [loadingIds, setLoadingIds] = useState<Set<string>>(new Set());
  const [decisionPendingIds, setDecisionPendingIds] = useState<Set<string>>(new Set());

  const setIsLoading = (id: string, value: boolean) => {
    setLoadingIds((prev) => {
      const next = new Set(prev);
      value ? next.add(id) : next.delete(id);
      return next;
    });
  };

  const setIsDecisionPending = (id: string, value: boolean) => {
    setDecisionPendingIds((prev) => {
      const next = new Set(prev);
      value ? next.add(id) : next.delete(id);
      return next;
    });
  };

  const isLoading = loadingIds.has(activeConversation?.id ?? "");
  const isDecisionPending = decisionPendingIds.has(activeConversation?.id ?? "");

  const [devPrefill, setDevPrefill] = useState<string | null>(null);
  const [inputPrefill, setInputPrefill] = useState<string | null>(null);
  const [suggestedSources, setSuggestedSources] = useState<string[]>([]);
  const [selectedSources, setSelectedSources] = useState<string[]>([]);
  const [localSourceContext, setLocalSourceContext] = useState<
    "plan" | "gather_more" | null
  >(null);
  const [pendingGatherMoreText, setPendingGatherMoreText] = useState<
    string | null
  >(null);
  const [devSnapshots, setDevSnapshots] = useState<DialogueDevSnapshot[]>([]);
  const [isDevSnapshotsLoading, setIsDevSnapshotsLoading] = useState(false);

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
    if (response.action !== "complete") {
      addMessage(buildSystemMessage(response, t), conversationId);
    }

    const next = inferStageFromResponse(response, fallbackStage, fallbackSubState);
    const nextPhase = inferPhaseFromResponse(response, next.stage, fallbackPhase);

    // Reset review activity when phase changes, then apply new data if present
    if (nextPhase !== fallbackPhase) {
      setReviewActivity(response.review_activity ?? []);
    } else if (response.review_activity && response.review_activity.length > 0) {
      setReviewActivity(response.review_activity);
    }

    setStage(conversationId, next.stage, next.subState, nextPhase);
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
    // Inject per-tier timeframes from settings if not already set by the caller.
    const effectiveOptions: DialogueSendOptions = {
      ...options,
      sourceTimeframes:
        options.sourceTimeframes ?? { ...settings.inputParameters.sourceTimeframes },
    };

    const response = await sendMessage(
      message,
      sessionId,
      perspectives,
      approved,
      settings.aiLanguage,
      settings.inputParameters.timeframe,
      effectiveOptions,
    );

    if (response.action === "start_collecting") {
      // Skip the "Collecting from: ..." message — the Collection Results card
      // already shows the sources used.  Just advance the stage.
      setStage(conversationId, "collecting", null, "collection");
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
      { sourceTimeframes: effectiveOptions.sourceTimeframes },
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
    const conversationId = conversation.id;

    addMessage(
      { id: crypto.randomUUID(), text, sender: "user" },
      conversationId,
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

    setIsLoading(conversationId, true);
    try {
      await sendAndHandle(
        conversationId,
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
      error(t.messageFailed(e instanceof Error ? e.message : String(e)));
      if (activeConversation?.stage === "collecting") {
        setStage(conversationId, "plan_confirming", "awaiting_decision", "collection");
      }
    } finally {
      setIsLoading(conversationId, false);
    }
  };

  const approve = async () => {
    if (!activeConversation) return;
    const conversationId = activeConversation.id;

    // For plan_confirming: show local source selection instead of calling backend
    if (stage === "plan_confirming") {
      setLocalSourceContext("plan");
      return;
    }

    setIsDecisionPending(conversationId, true);
    setIsLoading(conversationId, true);

    // Optimistically advance the phase so the stage tracker updates immediately
    if (stage === "reviewing" && activeConversation.phase === "collection") {
      setStage(conversationId, "pending", null, "processing");
    } else if (stage === "processing" && subState === "awaiting_decision") {
      setStage(conversationId, "pending", null, "analysis");
    }

    try {
      await sendAndHandle(
        conversationId,
        activeConversation.sessionId,
        "approve",
        true,
        {},
        stage,
        subState,
        activeConversation.phase,
        activeConversation.perspectives,
      );
      // Only show toast if the user is still viewing the same conversation
      if (activeConversation?.id === conversationId) {
        success(t.requestApproved);
      }
    } catch (e) {
      if (activeConversation?.id === conversationId) {
        error(t.approvalFailed(e instanceof Error ? e.message : String(e)));
        if (activeConversation.stage === "collecting") {
          setStage(conversationId, "plan_confirming", "awaiting_decision", "collection");
        }
      }
    } finally {
      setIsLoading(conversationId, false);
      setIsDecisionPending(conversationId, false);
    }
  };

  const reject = () => {
    if (!activeConversation || !isDecisionStage(stage)) {
      return;
    }

    addMessage(
      {
        id: crypto.randomUUID(),
        text: getFeedbackPrompt(stage, t),
        sender: "system",
      },
      activeConversation.id,
    );

    setStage(activeConversation.id, stage, "awaiting_modifications");
    info(t.addFeedbackInChat);
  };

  const gatherMoreFromProcessing = async () => {
    if (!activeConversation) return;
    const conversationId = activeConversation.id;
    setIsLoading(conversationId, true);
    try {
      await sendAndHandle(
        conversationId,
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
      error(t.gatherMoreFailed(e instanceof Error ? e.message : String(e)));
    } finally {
      setIsLoading(conversationId, false);
    }
  };

  const gatherMore = () => {
    if (!activeConversation || stage !== "reviewing" || phase !== "collection") {
      return;
    }

    addMessage(
      {
        id: crypto.randomUUID(),
        text: t.gatherMoreQuestion,
        sender: "system",
      },
      activeConversation.id,
    );
    setStage(activeConversation.id, "reviewing", "awaiting_gather_more");
    info(t.gatherMoreInfo);
  };

  const toggleSourceSelection = (source: string) => {
    setSelectedSources((current) => {
      if (current.includes(source)) {
        return current.filter((item) => item !== source);
      }
      return [...current, source];
    });
  };

  const submitSourceSelection = async (sourceTimeframes: Record<string, string> = {}) => {
    if (!activeConversation) return;
    if (selectedSources.length === 0) {
      error(t.selectAtLeastOneSource);
      return;
    }

    const isGatherMore = localSourceContext === "gather_more";
    const message = isGatherMore ? (pendingGatherMoreText ?? "") : "approve";
    const approved = isGatherMore ? undefined : true;
    const options = isGatherMore
      ? { gatherMore: true, selectedSources, sourceTimeframes }
      : { selectedSources, sourceTimeframes };

    setLocalSourceContext(null);
    setPendingGatherMoreText(null);

    const conversationId = activeConversation.id;
    setIsLoading(conversationId, true);
    try {
      await sendAndHandle(
        conversationId,
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
      error(t.startCollectionFailed(e instanceof Error ? e.message : String(e)));
      if (activeConversation?.stage === "collecting") {
        setStage(conversationId, "plan_confirming", "awaiting_decision", "collection");
      }
    } finally {
      setIsLoading(conversationId, false);
    }
  };

  const triggerDevMessage = (text: string) => {
    setDevPrefill(text);
  };

  const clearDevPrefill = () => {
    setDevPrefill(null);
  };

  const prefillGapPrompt = (message: string) => {
    setInputPrefill(message);
  };

  const clearInputPrefill = () => {
    setInputPrefill(null);
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
    setStage(conversation.id, "summary_confirming", "awaiting_decision", "direction");
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
        activeConversation.id,
        response.stage,
        response.sub_state ?? defaultSubStateForStage(response.stage),
        response.phase,
      );
      info(t.setDevStage(response.stage));
    } catch {
      error(t.setDevStageFailed);
    }
  };

  const syncDevStage = async () => {
    if (!activeConversation) return;
    try {
      const response = await getDevDialogueState(activeConversation.sessionId);
      setStage(
        activeConversation.id,
        response.stage,
        response.sub_state ?? defaultSubStateForStage(response.stage),
        response.phase,
      );
      info(t.syncDevStage(response.stage));
    } catch {
      error(t.syncDevStageFailed);
    }
  };

  const resetDevStage = async () => {
    if (!activeConversation) return;
    try {
      const response = await resetDevDialogueState(
        activeConversation.sessionId,
      );
      setStage(
        activeConversation.id,
        response.stage,
        response.sub_state ?? defaultSubStateForStage(response.stage),
        response.phase,
      );
      info(t.resetStageInfo);
    } catch {
      error(t.resetStageFailed);
    }
  };

  const sendCouncilRequest = async (params: {
    debatePoint: string;
    findingIds: string[];
    perspectives: string[];
    councilSettings: CouncilRunSettings;
  }) => {
    if (!activeConversation) return;
    const conversationId = activeConversation.id;
    setIsLoading(conversationId, true);
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
      if (response.action === "error") {
        throw new Error(response.question || "Council run failed.");
      }
      applyResponse(response, conversationId, "idle", null, "analysis");
    } finally {
      setIsLoading(conversationId, false);
    }
  };

  const refreshDevSnapshots = async () => {
    setIsDevSnapshotsLoading(true);
    try {
      const snapshots = await listDevDialogueSnapshots();
      setDevSnapshots(snapshots);
      if (snapshots.length === 0) {
        info(t.noPreviousBackendRuns);
      }
    } catch (e) {
      const status =
        typeof e === "object" && e !== null && "response" in e
          ? (e as { response?: { status?: number } }).response?.status
          : undefined;
      error(
        status === 404
          ? t.previousRunsEndpointMissing
          : t.previousRunsFailed,
      );
    } finally {
      setIsDevSnapshotsLoading(false);
    }
  };

  useEffect(() => {
    if (didRequestInitialDevSnapshots) return;
    didRequestInitialDevSnapshots = true;
    void refreshDevSnapshots();
    // Dev snapshot loading is intentionally one-shot on mount.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const restoreDevSnapshot = async (
    sourceSessionId: string,
    targetStage: DialogueStage,
    targetPhase: DialoguePhase,
  ) => {
    const conversation =
      activeConversation ?? createNewConversation(initialPerspectives);
    setIsDevSnapshotsLoading(true);
    try {
      const response = await restoreDevDialogueSnapshot(
        sourceSessionId,
        conversation.sessionId,
        targetStage,
        targetPhase,
      );
      replaceMessages(
        conversation.id,
        response.messages.map((message) => ({
          ...message,
          id: crypto.randomUUID(),
        })),
      );
      setStage(
        conversation.id,
        response.stage,
        response.sub_state ?? defaultSubStateForStage(response.stage),
        response.phase,
      );
      success(t.loadedPreviousRun(sourceSessionId.slice(0, 8)));
    } catch (e) {
      error(
        t.restorePreviousRunFailed(e instanceof Error ? e.message : String(e)),
      );
    } finally {
      setIsDevSnapshotsLoading(false);
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
    devSnapshots,
    isDevSnapshotsLoading,
    refreshDevSnapshots,
    restoreDevSnapshot,
    devPrefill,
    triggerDevMessage,
    clearDevPrefill,
    inputPrefill,
    prefillGapPrompt,
    clearInputPrefill,
  };
}
