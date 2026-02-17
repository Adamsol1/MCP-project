import { describe, it, expect, beforeEach } from "vitest";
import { renderHook, act } from "@testing-library/react";
import type { ReactNode } from "react";
import { useConversation } from "../hooks/useConversation";
import { ConversationProvider } from "./ConversationContext";
import type { ConversationStore } from "../types/conversation";

const STORAGE_KEY = "mcp-conversations";

// Helper: wraps the hook in a ConversationProvider so it has access to context
function createWrapper() {
  return function Wrapper({ children }: { children: ReactNode }) {
    return <ConversationProvider>{children}</ConversationProvider>;
  };
}

describe("ConversationContext", () => {
  beforeEach(() => {
    localStorage.clear();
  });

  // ---------- Initialization ----------

  describe("initialization", () => {
    it("starts with empty conversations when localStorage is empty", () => {
      const { result } = renderHook(() => useConversation(), {
        wrapper: createWrapper(),
      });

      expect(result.current.conversations).toEqual([]);
      expect(result.current.activeConversation).toBeNull();
    });

    it("loads existing conversations from localStorage", () => {
      // Pre-seed localStorage before the provider mounts
      const existingStore: ConversationStore = {
        conversations: [
          {
            id: "conv-1",
            title: "Existing conversation",
            messages: [{ id: "m1", text: "Hello", sender: "user" }],
            perspectives: ["US"],
            sessionId: "session-1",
            isConfirming: false,
            createdAt: 1000,
            updatedAt: 2000,
          },
        ],
        activeConversationId: "conv-1",
      };
      localStorage.setItem(STORAGE_KEY, JSON.stringify(existingStore));

      const { result } = renderHook(() => useConversation(), {
        wrapper: createWrapper(),
      });

      expect(result.current.conversations).toHaveLength(1);
      expect(result.current.conversations[0].title).toBe(
        "Existing conversation"
      );
      expect(result.current.activeConversation?.id).toBe("conv-1");
    });
  });

  // ---------- createNewConversation ----------

  describe("createNewConversation", () => {
    it("adds a new conversation to the list", () => {
      const { result } = renderHook(() => useConversation(), {
        wrapper: createWrapper(),
      });

      act(() => {
        result.current.createNewConversation();
      });

      expect(result.current.conversations).toHaveLength(1);
    });

    it("sets the new conversation as active", () => {
      const { result } = renderHook(() => useConversation(), {
        wrapper: createWrapper(),
      });

      act(() => {
        result.current.createNewConversation();
      });

      expect(result.current.activeConversation).not.toBeNull();
      expect(result.current.activeConversation?.id).toBe(
        result.current.conversations[0].id
      );
    });

    it("new conversation has default NEUTRAL perspectives", () => {
      const { result } = renderHook(() => useConversation(), {
        wrapper: createWrapper(),
      });

      act(() => {
        result.current.createNewConversation();
      });

      expect(result.current.activeConversation?.perspectives).toEqual([
        "NEUTRAL",
      ]);
    });

    it("persists to localStorage", () => {
      const { result } = renderHook(() => useConversation(), {
        wrapper: createWrapper(),
      });

      act(() => {
        result.current.createNewConversation();
      });

      const stored = JSON.parse(localStorage.getItem(STORAGE_KEY)!);
      expect(stored.conversations).toHaveLength(1);
      expect(stored.activeConversationId).toBe(
        result.current.conversations[0].id
      );
    });
  });

  // ---------- switchConversation ----------

  describe("switchConversation", () => {
    it("changes the active conversation", () => {
      const { result } = renderHook(() => useConversation(), {
        wrapper: createWrapper(),
      });

      // Create two conversations
      act(() => {
        result.current.createNewConversation();
      });
      const firstId = result.current.conversations[0].id;

      act(() => {
        result.current.createNewConversation();
      });
      const secondId = result.current.conversations[1].id;

      // Active should be the second (most recently created)
      expect(result.current.activeConversation?.id).toBe(secondId);

      // Switch back to the first
      act(() => {
        result.current.switchConversation(firstId);
      });

      expect(result.current.activeConversation?.id).toBe(firstId);
    });

    it("persists to localStorage", () => {
      const { result } = renderHook(() => useConversation(), {
        wrapper: createWrapper(),
      });

      act(() => {
        result.current.createNewConversation();
      });
      const firstId = result.current.conversations[0].id;

      act(() => {
        result.current.createNewConversation();
      });

      act(() => {
        result.current.switchConversation(firstId);
      });

      const stored = JSON.parse(localStorage.getItem(STORAGE_KEY)!);
      expect(stored.activeConversationId).toBe(firstId);
    });
  });

  // ---------- addMessage ----------

  describe("addMessage", () => {
    it("appends message to active conversation", () => {
      const { result } = renderHook(() => useConversation(), {
        wrapper: createWrapper(),
      });

      act(() => {
        result.current.createNewConversation();
      });

      act(() => {
        result.current.addMessage({
          id: "msg-1",
          text: "Investigate APT29",
          sender: "user",
        });
      });

      expect(result.current.activeConversation?.messages).toHaveLength(1);
      expect(result.current.activeConversation?.messages[0].text).toBe(
        "Investigate APT29"
      );
    });

    it("sets title from first user message", () => {
      const { result } = renderHook(() => useConversation(), {
        wrapper: createWrapper(),
      });

      act(() => {
        result.current.createNewConversation();
      });

      // Title should be default before any messages
      expect(result.current.activeConversation?.title).toBe(
        "New conversation"
      );

      act(() => {
        result.current.addMessage({
          id: "msg-1",
          text: "Investigate APT29 targeting EU infrastructure",
          sender: "user",
        });
      });

      // Title should now be derived from the first user message
      expect(result.current.activeConversation?.title).toBe(
        "Investigate APT29 targeting EU infrastructure"
      );
    });

    it("truncates long titles to 50 characters", () => {
      const { result } = renderHook(() => useConversation(), {
        wrapper: createWrapper(),
      });

      act(() => {
        result.current.createNewConversation();
      });

      const longMessage =
        "Investigate advanced persistent threat group 29 activities targeting European Union critical infrastructure";

      act(() => {
        result.current.addMessage({
          id: "msg-1",
          text: longMessage,
          sender: "user",
        });
      });

      // Title should be truncated to 50 chars + "..."
      expect(result.current.activeConversation?.title).toHaveLength(53);
      expect(result.current.activeConversation?.title).toMatch(/\.\.\.$/);
    });

    it("does not update title on system messages", () => {
      const { result } = renderHook(() => useConversation(), {
        wrapper: createWrapper(),
      });

      act(() => {
        result.current.createNewConversation();
      });

      act(() => {
        result.current.addMessage({
          id: "msg-1",
          text: "What is the scope?",
          sender: "system",
        });
      });

      // Title should still be the default since only user messages set the title
      expect(result.current.activeConversation?.title).toBe(
        "New conversation"
      );
    });

    it("does not update title on subsequent user messages", () => {
      const { result } = renderHook(() => useConversation(), {
        wrapper: createWrapper(),
      });

      act(() => {
        result.current.createNewConversation();
      });

      act(() => {
        result.current.addMessage({
          id: "msg-1",
          text: "First message",
          sender: "user",
        });
      });

      act(() => {
        result.current.addMessage({
          id: "msg-2",
          text: "Second message should not change title",
          sender: "user",
        });
      });

      // Title should still be from the first user message
      expect(result.current.activeConversation?.title).toBe("First message");
    });

    it("updates updatedAt timestamp", () => {
      const { result } = renderHook(() => useConversation(), {
        wrapper: createWrapper(),
      });

      act(() => {
        result.current.createNewConversation();
      });

      const createdAt = result.current.activeConversation!.createdAt;

      act(() => {
        result.current.addMessage({
          id: "msg-1",
          text: "Hello",
          sender: "user",
        });
      });

      // updatedAt should be >= createdAt (could be equal if very fast)
      expect(
        result.current.activeConversation!.updatedAt
      ).toBeGreaterThanOrEqual(createdAt);
    });

    it("persists to localStorage", () => {
      const { result } = renderHook(() => useConversation(), {
        wrapper: createWrapper(),
      });

      act(() => {
        result.current.createNewConversation();
      });

      act(() => {
        result.current.addMessage({
          id: "msg-1",
          text: "Test message",
          sender: "user",
        });
      });

      const stored = JSON.parse(localStorage.getItem(STORAGE_KEY)!);
      expect(stored.conversations[0].messages).toHaveLength(1);
    });
  });

  // ---------- setIsConfirming ----------

  describe("setIsConfirming", () => {
    it("sets isConfirming on active conversation", () => {
      const { result } = renderHook(() => useConversation(), {
        wrapper: createWrapper(),
      });

      act(() => {
        result.current.createNewConversation();
      });

      expect(result.current.activeConversation?.isConfirming).toBe(false);

      act(() => {
        result.current.setIsConfirming(true);
      });

      expect(result.current.activeConversation?.isConfirming).toBe(true);
    });

    it("persists to localStorage", () => {
      const { result } = renderHook(() => useConversation(), {
        wrapper: createWrapper(),
      });

      act(() => {
        result.current.createNewConversation();
      });

      act(() => {
        result.current.setIsConfirming(true);
      });

      const stored = JSON.parse(localStorage.getItem(STORAGE_KEY)!);
      expect(stored.conversations[0].isConfirming).toBe(true);
    });
  });

  // ---------- updatePerspectives ----------

  describe("updatePerspectives", () => {
    it("updates perspectives on active conversation", () => {
      const { result } = renderHook(() => useConversation(), {
        wrapper: createWrapper(),
      });

      act(() => {
        result.current.createNewConversation();
      });

      act(() => {
        result.current.updatePerspectives(["US", "EU", "NORWAY"]);
      });

      expect(result.current.activeConversation?.perspectives).toEqual([
        "US",
        "EU",
        "NORWAY",
      ]);
    });

    it("persists to localStorage", () => {
      const { result } = renderHook(() => useConversation(), {
        wrapper: createWrapper(),
      });

      act(() => {
        result.current.createNewConversation();
      });

      act(() => {
        result.current.updatePerspectives(["CHINA", "RUSSIA"]);
      });

      const stored = JSON.parse(localStorage.getItem(STORAGE_KEY)!);
      expect(stored.conversations[0].perspectives).toEqual([
        "CHINA",
        "RUSSIA",
      ]);
    });
  });

  // ---------- deleteConversation ----------

  describe("deleteConversation", () => {
    it("removes conversation from list", () => {
      const { result } = renderHook(() => useConversation(), {
        wrapper: createWrapper(),
      });

      act(() => {
        result.current.createNewConversation();
      });
      const convId = result.current.conversations[0].id;

      act(() => {
        result.current.deleteConversation(convId);
      });

      expect(result.current.conversations).toHaveLength(0);
    });

    it("switches active to most recent remaining conversation", () => {
      const { result } = renderHook(() => useConversation(), {
        wrapper: createWrapper(),
      });

      act(() => {
        result.current.createNewConversation();
      });
      const firstId = result.current.conversations[0].id;

      act(() => {
        result.current.createNewConversation();
      });
      const secondId = result.current.conversations[1].id;

      // Delete the second (active) conversation
      act(() => {
        result.current.deleteConversation(secondId);
      });

      // Should fall back to the first
      expect(result.current.activeConversation?.id).toBe(firstId);
    });

    it("sets activeConversationId to null when last conversation is deleted", () => {
      const { result } = renderHook(() => useConversation(), {
        wrapper: createWrapper(),
      });

      act(() => {
        result.current.createNewConversation();
      });
      const convId = result.current.conversations[0].id;

      act(() => {
        result.current.deleteConversation(convId);
      });

      expect(result.current.activeConversation).toBeNull();
    });

    it("persists to localStorage", () => {
      const { result } = renderHook(() => useConversation(), {
        wrapper: createWrapper(),
      });

      act(() => {
        result.current.createNewConversation();
      });
      const convId = result.current.conversations[0].id;

      act(() => {
        result.current.deleteConversation(convId);
      });

      const stored = JSON.parse(localStorage.getItem(STORAGE_KEY)!);
      expect(stored.conversations).toHaveLength(0);
    });
  });

  // ---------- useConversation outside provider ----------

  describe("useConversation hook", () => {
    it("throws when used outside ConversationProvider", () => {
      // Suppress React error boundary console output during this test
      const spy = vi.spyOn(console, "error").mockImplementation(() => {});

      expect(() => {
        renderHook(() => useConversation());
      }).toThrow("useConversation must be used within a ConversationProvider");

      spy.mockRestore();
    });
  });
});
