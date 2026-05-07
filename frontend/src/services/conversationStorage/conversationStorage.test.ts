import { describe, it, expect, beforeEach } from "vitest";
import {
  loadConversationStore,
  saveConversationStore,
  createConversation,
} from "./conversationStorage";
import type { ConversationStore } from "../../types/conversation";

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
            stage: "initial",
            phase: "direction",
            subState: null,
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
            stage: "initial",
            phase: "direction",
            subState: null,
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
        /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/,
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

    it("creates a conversation with an empty string title", () => {
      const conv = createConversation();

      expect(conv.title).toBe("");
    });

    it("creates a conversation with a UUID sessionId", () => {
      const conv = createConversation();

      expect(conv.sessionId).toMatch(
        /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/,
      );
    });

    it("creates a conversation with isConfirming set to false", () => {
      const conv = createConversation();

      expect(conv.isConfirming).toBe(false);
    });

    it("creates a conversation with stage set to initial", () => {
      const conv = createConversation();
      expect(conv.stage).toBe("initial");
    });

    it("creates a conversation with phase set to direction", () => {
      const conv = createConversation();
      expect(conv.phase).toBe("direction");
    });

    it("creates a conversation with subState set to null", () => {
      const conv = createConversation();
      expect(conv.subState).toBeNull();
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

  // ---------- normalizeConversation / coerceStage (via loadConversationStore) ----------

  describe("loadConversationStore — normalizeConversation coercion", () => {
    function seedStore(overrides: Record<string, unknown>) {
      const conv = {
        id: "c1",
        title: "Test",
        messages: [],
        perspectives: ["NEUTRAL"],
        sessionId: "s1",
        isConfirming: false,
        stage: "initial",
        phase: "direction",
        subState: null,
        createdAt: 1000,
        updatedAt: 1000,
        ...overrides,
      };
      localStorage.setItem(STORAGE_KEY, JSON.stringify({
        conversations: [conv],
        activeConversationId: "c1",
      }));
    }

    // coerceStage — invalid stage, isConfirming = false → "initial"
    it("coerces an unrecognised stage to 'initial' when isConfirming is false", () => {
      seedStore({ stage: "totally_invalid_stage", isConfirming: false });
      const store = loadConversationStore();
      expect(store.conversations[0].stage).toBe("initial");
    });

    // coerceStage — invalid stage, isConfirming = true → "summary_confirming"
    it("coerces an unrecognised stage to 'summary_confirming' when isConfirming is true", () => {
      seedStore({ stage: "bogus", isConfirming: true });
      const store = loadConversationStore();
      expect(store.conversations[0].stage).toBe("summary_confirming");
    });

    // inferPhaseFromConversation — reviewing with collection message → "collection"
    it("infers phase 'collection' for reviewing stage when messages contain collection type", () => {
      seedStore({
        stage: "reviewing",
        phase: undefined, // omit so coercePhase falls back to inferPhaseFromConversation
        messages: [{ id: "m1", text: "data", sender: "system", type: "collection" }],
      });
      const store = loadConversationStore();
      expect(store.conversations[0].phase).toBe("collection");
    });

    // inferPhaseFromConversation — reviewing with no collection message → "processing"
    it("infers phase 'processing' for reviewing stage when no collection message", () => {
      seedStore({
        stage: "reviewing",
        phase: undefined,
        messages: [],
      });
      const store = loadConversationStore();
      expect(store.conversations[0].phase).toBe("processing");
    });

    // inferPhaseFromConversation — complete with analysis message → "analysis"
    it("infers phase 'analysis' for complete stage when messages contain analysis type", () => {
      seedStore({
        stage: "complete",
        phase: undefined,
        messages: [{ id: "m1", text: "done", sender: "system", type: "analysis" }],
      });
      const store = loadConversationStore();
      expect(store.conversations[0].phase).toBe("analysis");
    });

    // inferPhaseFromConversation — complete with council message → "analysis"
    it("infers phase 'analysis' for idle stage when messages contain council type", () => {
      seedStore({
        stage: "idle",
        phase: undefined,
        messages: [{ id: "m1", text: "council", sender: "system", type: "council" }],
      });
      const store = loadConversationStore();
      expect(store.conversations[0].phase).toBe("analysis");
    });

    // inferPhaseFromConversation — complete with no analysis/council → "processing"
    it("infers phase 'processing' for pending stage when no analysis/council messages", () => {
      seedStore({
        stage: "pending",
        phase: undefined,
        messages: [],
      });
      const store = loadConversationStore();
      expect(store.conversations[0].phase).toBe("processing");
    });

    // inferPhaseFromConversation — plan_confirming → "collection"
    it("infers phase 'collection' for plan_confirming stage", () => {
      seedStore({ stage: "plan_confirming", phase: undefined });
      const store = loadConversationStore();
      expect(store.conversations[0].phase).toBe("collection");
    });

    // inferPhaseFromConversation — processing → "processing"
    it("infers phase 'processing' for processing stage", () => {
      seedStore({ stage: "processing", phase: undefined });
      const store = loadConversationStore();
      expect(store.conversations[0].phase).toBe("processing");
    });

    // coercePhase — unknown phase triggers inferPhaseFromConversation
    it("falls back to inferred phase when stored phase is unrecognised", () => {
      seedStore({ stage: "gathering", phase: "completely_unknown_phase" });
      const store = loadConversationStore();
      // gathering → direction (via inferPhaseFromConversation default)
      expect(store.conversations[0].phase).toBe("direction");
    });

    // coerceSubState — unrecognised subState → null
    it("coerces an unrecognised subState to null", () => {
      seedStore({ subState: "some_unknown_sub_state" });
      const store = loadConversationStore();
      expect(store.conversations[0].subState).toBeNull();
    });

    // coerceSubState — valid "awaiting_modifications" is preserved
    it("preserves valid subState 'awaiting_modifications'", () => {
      seedStore({ stage: "summary_confirming", subState: "awaiting_modifications" });
      const store = loadConversationStore();
      expect(store.conversations[0].subState).toBe("awaiting_modifications");
    });

    // coerceSubState — valid "awaiting_gather_more" is preserved
    it("preserves valid subState 'awaiting_gather_more'", () => {
      seedStore({ stage: "reviewing", subState: "awaiting_gather_more" });
      const store = loadConversationStore();
      expect(store.conversations[0].subState).toBe("awaiting_gather_more");
    });
  });
});
