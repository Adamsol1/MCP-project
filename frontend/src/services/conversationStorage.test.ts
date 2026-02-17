import { describe, it, expect, beforeEach } from "vitest";
import {
  loadConversationStore,
  saveConversationStore,
  createConversation,
} from "./conversationStorage";
import type { ConversationStore } from "../types/conversation";

const STORAGE_KEY = "mcp-conversations";

describe("conversationStorage", () => {
  // Clear localStorage before each test so they don't affect each other
  beforeEach(() => {
    localStorage.clear();
  });

  // ---------- loadConversationStore ----------

  describe("loadConversationStore", () => {
    it("returns default empty store when localStorage is empty", () => {
      const store = loadConversationStore();

      expect(store.conversations).toEqual([]);
      expect(store.activeConversationId).toBeNull();
    });

    it("returns parsed store when localStorage has valid data", () => {
      // Pre-seed localStorage with a valid store
      const existingStore: ConversationStore = {
        conversations: [
          {
            id: "test-123",
            title: "Test conversation",
            messages: [{ id: "m1", text: "Hello", sender: "user" }],
            perspectives: ["US", "EU"],
            sessionId: "session-456",
            isConfirming: false,
            createdAt: 1000,
            updatedAt: 2000,
          },
        ],
        activeConversationId: "test-123",
      };
      localStorage.setItem(STORAGE_KEY, JSON.stringify(existingStore));

      const store = loadConversationStore();

      expect(store.conversations).toHaveLength(1);
      expect(store.conversations[0].title).toBe("Test conversation");
      expect(store.activeConversationId).toBe("test-123");
    });

    it("returns default store when localStorage has invalid JSON", () => {
      // Corrupted data should not crash the app
      localStorage.setItem(STORAGE_KEY, "not valid json {{{");

      const store = loadConversationStore();

      expect(store.conversations).toEqual([]);
      expect(store.activeConversationId).toBeNull();
    });
  });

  // ---------- saveConversationStore ----------

  describe("saveConversationStore", () => {
    it("serializes store to localStorage under the correct key", () => {
      const store: ConversationStore = {
        conversations: [],
        activeConversationId: null,
      };

      saveConversationStore(store);

      const raw = localStorage.getItem(STORAGE_KEY);
      expect(raw).not.toBeNull();
      expect(JSON.parse(raw!)).toEqual(store);
    });

    it("overwrites existing data", () => {
      // First save
      saveConversationStore({
        conversations: [],
        activeConversationId: null,
      });

      // Second save with different data
      const updatedStore: ConversationStore = {
        conversations: [
          {
            id: "new-1",
            title: "New",
            messages: [],
            perspectives: ["NEUTRAL"],
            sessionId: "s1",
            isConfirming: false,
            createdAt: 1000,
            updatedAt: 1000,
          },
        ],
        activeConversationId: "new-1",
      };
      saveConversationStore(updatedStore);

      const raw = localStorage.getItem(STORAGE_KEY);
      expect(JSON.parse(raw!).conversations).toHaveLength(1);
      expect(JSON.parse(raw!).activeConversationId).toBe("new-1");
    });
  });

  // ---------- createConversation ----------

  describe("createConversation", () => {
    it("creates a conversation with a unique UUID id", () => {
      const conv = createConversation();

      // UUID v4 format: 8-4-4-4-12 hex characters
      expect(conv.id).toMatch(
        /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/
      );
    });

    it("creates a conversation with empty messages array", () => {
      const conv = createConversation();

      expect(conv.messages).toEqual([]);
    });

    it("creates a conversation with default NEUTRAL perspectives", () => {
      const conv = createConversation();

      expect(conv.perspectives).toEqual(["NEUTRAL"]);
    });

    it("creates a conversation with provided perspectives", () => {
      const conv = createConversation(["US", "EU", "NORWAY"]);

      expect(conv.perspectives).toEqual(["US", "EU", "NORWAY"]);
    });

    it("creates a conversation with 'New conversation' as title", () => {
      const conv = createConversation();

      expect(conv.title).toBe("New conversation");
    });

    it("creates a conversation with a UUID sessionId", () => {
      const conv = createConversation();

      expect(conv.sessionId).toMatch(
        /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/
      );
    });

    it("creates a conversation with isConfirming set to false", () => {
      const conv = createConversation();

      expect(conv.isConfirming).toBe(false);
    });

    it("creates a conversation with createdAt and updatedAt timestamps", () => {
      const before = Date.now();
      const conv = createConversation();
      const after = Date.now();

      // Timestamps should be between the before and after snapshots
      expect(conv.createdAt).toBeGreaterThanOrEqual(before);
      expect(conv.createdAt).toBeLessThanOrEqual(after);
      expect(conv.updatedAt).toBe(conv.createdAt);
    });

    it("creates unique ids for different conversations", () => {
      const conv1 = createConversation();
      const conv2 = createConversation();

      expect(conv1.id).not.toBe(conv2.id);
      expect(conv1.sessionId).not.toBe(conv2.sessionId);
    });
  });
});
