import type { Conversation, ConversationStore } from "../types/conversation";
import type { DialogueStage, DialogueSubState } from "../types/dialogue";

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
    rawStage === "complete"
  ) {
    return rawStage;
  }
  return isConfirming ? "summary_confirming" : "initial";
}

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

function normalizeConversation(raw: Conversation): Conversation {
  const stage = coerceStage(raw.stage, raw.isConfirming);
  const subState = coerceSubState(raw.subState);
  return {
    ...raw,
    stage,
    subState,
    isConfirming:
      (stage === "summary_confirming" ||
        stage === "pir_confirming" ||
        stage === "plan_confirming" ||
        stage === "reviewing") &&
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
    title: "New conversation",
    messages: [],
    perspectives: perspectives ?? ["NEUTRAL"],
    sessionId: crypto.randomUUID(), // Separate UUID used to identify this session on the backend.
    isConfirming: false,
    stage: "initial",
    subState: null,
    createdAt: timeNow,
    updatedAt: timeNow, // Same as createdAt on creation; updated on every mutation.
  };
}
