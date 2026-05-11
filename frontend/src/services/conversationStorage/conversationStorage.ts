import type { Conversation, ConversationStore } from "../../types/conversation";
import type {
  DialoguePhase,
  DialogueStage,
  DialogueSubState,
} from "../../types/dialogue";

/**
 * Single localStorage key under which the entire ConversationStore is stored
 * as a serialised JSON string. Using one key keeps reads and writes atomic.
 */
const STORAGE_KEY = "mcp-conversations";

/** Fallback store returned when localStorage is empty or the data is corrupted. */
const DEFAULT_STORE: ConversationStore = {
  conversations: [],
  activeConversationId: null,
};

/**
 * Validates `rawStage` against the known `DialogueStage` union.
 *
 * When the stored value is unrecognised (e.g. from an old schema), falls back
 * to `"summary_confirming"` if the conversation was mid-confirmation, otherwise
 * `"initial"`, to avoid placing the UI in an undefined state.
 */
function coerceStage(rawStage: unknown, isConfirming: boolean): DialogueStage {
  if (
    rawStage === "initial" ||
    rawStage === "gathering" ||
    rawStage === "summary_confirming" ||
    rawStage === "pir_confirming" ||
    rawStage === "planning" ||
    rawStage === "plan_confirming" ||
    rawStage === "source_selecting" ||
    rawStage === "collecting" ||
    rawStage === "reviewing" ||
    rawStage === "processing" ||
    rawStage === "pending" ||
    rawStage === "idle" ||
    rawStage === "complete"
  ) {
    return rawStage;
  }
  return isConfirming ? "summary_confirming" : "initial";
}

/**
 * Infers the `DialoguePhase` from a conversation's stage and message history
 * when no explicit phase value is stored (e.g. upgrading from an older schema).
 *
 * The `reviewing` stage is ambiguous: it can occur in both the collection and
 * processing phases, so the function inspects message types to disambiguate.
 */
function inferPhaseFromConversation(raw: Conversation, stage: DialogueStage): DialoguePhase {
  switch (stage) {
    case "planning":
    case "plan_confirming":
    case "source_selecting":
    case "collecting":
      return "collection";
    case "reviewing":
      return raw.messages.some((message) => message.type === "collection")
        ? "collection"
        : "processing";
    case "processing":
      return "processing";
    case "pending":
    case "idle":
    case "complete":
      return raw.messages.some((m) => m.type === "analysis" || m.type === "council")
        ? "analysis"
        : "processing";
    case "initial":
    case "gathering":
    case "summary_confirming":
    case "pir_confirming":
    default:
      return "direction";
  }
}

/**
 * Validates `rawPhase` against the known `DialoguePhase` union, falling back to
 * `inferPhaseFromConversation` when the stored value is unrecognised.
 */
function coercePhase(
  rawPhase: unknown,
  rawConversation: Conversation,
  stage: DialogueStage,
): DialoguePhase {
  if (
    rawPhase === "direction" ||
    rawPhase === "collection" ||
    rawPhase === "processing" ||
    rawPhase === "analysis" ||
    rawPhase === "council"
  ) {
    return rawPhase;
  }
  return inferPhaseFromConversation(rawConversation, stage);
}

/**
 * Validates `rawSubState` against the known `DialogueSubState` union.
 * Returns null for any unrecognised value (null is the valid "no sub-state" sentinel).
 */
function coerceSubState(rawSubState: unknown): DialogueSubState {
  if (
    rawSubState === "awaiting_decision" ||
    rawSubState === "awaiting_modifications" ||
    rawSubState === "awaiting_gather_more"
  ) {
    return rawSubState;
  }
  return null;
}

/**
 * Sanitises a raw `Conversation` loaded from localStorage by coercing all
 * enum-like fields through their respective validators and recomputing
 * `isConfirming` from the canonical stage + sub-state rather than trusting
 * the stored boolean, which can be stale after a mid-session page reload.
 */
function normalizeConversation(raw: Conversation): Conversation {
  const stage = coerceStage(raw.stage, raw.isConfirming);
  const phase = coercePhase(raw.phase, raw, stage);
  const subState = coerceSubState(raw.subState);
  return {
    ...raw,
    stage,
    phase,
    subState,
    isConfirming:
      (stage === "summary_confirming" ||
        stage === "pir_confirming" ||
        stage === "plan_confirming" ||
        stage === "reviewing" ||
        stage === "processing") &&
      subState === "awaiting_decision",
  };
}

/**
 * Reads the conversation store from localStorage.
 *
 * Used as the initialiser function for useReducer in ConversationProvider so
 * that conversation history survives page reloads without an extra useEffect.
 *
 * @returns The parsed ConversationStore if the data is valid, or a copy of
 *          DEFAULT_STORE on first visit or if the stored JSON is corrupted.
 */
export function loadConversationStore(): ConversationStore {
  const rawConversations = localStorage.getItem(STORAGE_KEY);
  if (rawConversations) {
    try {
      const parsed = JSON.parse(rawConversations) as ConversationStore;
      return {
        ...parsed,
        conversations: parsed.conversations.map(normalizeConversation),
      };
    } catch {
      return { ...DEFAULT_STORE };
    }
  }
  return { ...DEFAULT_STORE };
}

/**
 * Persists the full conversation store to localStorage.
 *
 * Called by a useEffect in ConversationProvider on every state change so that
 * any mutation (new message, rename, delete) is immediately durable against
 * tab close or page refresh.
 *
 * @param store - The complete ConversationStore to serialise and save.
 */
export function saveConversationStore(store: ConversationStore) {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(store));
}

/**
 * Factory that creates a fresh Conversation object with generated UUIDs and
 * current timestamps.
 *
 * The title starts as "New conversation" — ConversationContext's ADD_MESSAGE
 * reducer case will replace it with the first user message automatically.
 *
 * @param perspectives - Optional starting perspectives. Defaults to ["NEUTRAL"].
 * @returns A new Conversation ready to be inserted into the store.
 */
export function createConversation(perspectives?: string[]): Conversation {
  const timeNow = Date.now();
  return {
    id: crypto.randomUUID(),
    title: "",
    messages: [],
    perspectives: perspectives ?? ["NEUTRAL"],
    sessionId: crypto.randomUUID(), // Separate UUID used to identify this session on the backend.
    isConfirming: false,
    stage: "initial",
    phase: "direction",
    subState: null,
    createdAt: timeNow,
    updatedAt: timeNow, // Same as createdAt on creation; updated on every mutation.
  };
}
