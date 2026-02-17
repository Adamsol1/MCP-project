import type { Conversation, ConversationStore } from "../types/conversation";

// Single localStorage key for all conversation data.
// The entire ConversationStore is serialized as one JSON string.
const STORAGE_KEY = "mcp-conversations";

// Default empty store returned when localStorage is empty or corrupted
const DEFAULT_STORE: ConversationStore = {
  conversations: [],
  activeConversationId: null,
};

/**
 * Reads the conversation store from localStorage.
 * @returns The parsed store if valid, or a default empty store if
 * localStorage has no data (first visit) or the JSON is corrupted/invalid.
 */
export function loadConversationStore(): ConversationStore {
  const rawConversations = localStorage.getItem(STORAGE_KEY);
  if (rawConversations) {
    try {
      return JSON.parse(rawConversations);
    } catch {
      return { ...DEFAULT_STORE };
    }
  }
  return { ...DEFAULT_STORE };
}

/**
 * Persists the full conversation store to localStorage.
 * Called on every state mutation to prevent data loss if the tab is closed.
 * @param store - The complete conversation store to serialize and save.
 */
export function saveConversationStore(store: ConversationStore) {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(store));
}

/**
 * Creates a new Conversation object with generated UUIDs and timestamps.
 * The title starts as "New conversation" and gets updated to the first user message later.
 * @param perspectives - Optional array of perspective strings. Defaults to `["NEUTRAL"]`.
 * @returns A new Conversation with unique id and sessionId.
 */
export function createConversation(perspectives?: string[]): Conversation {
  const timeNow = Date.now();
  return {
    id: crypto.randomUUID(),
    title: "New conversation",
    messages: [],
    perspectives: perspectives ?? ["NEUTRAL"], // Use provided perspectives or default
    sessionId: crypto.randomUUID(), // Unique backend session ID for this conversation
    isConfirming: false,
    createdAt: timeNow,
    updatedAt: timeNow, // Same as createdAt initially, updated when messages are added
  };
}
