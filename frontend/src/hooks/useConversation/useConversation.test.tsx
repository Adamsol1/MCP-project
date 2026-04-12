/**
 * useConversation hook tests.
 *
 * useConversation is a thin context accessor — these tests verify:
 *  1. The hook throws a descriptive error when called outside a ConversationProvider.
 *  2. The hook returns the full context value when inside a ConversationProvider.
 *  3. All expected callbacks are exposed as functions.
 *
 * Run with: cd frontend && npx vitest useConversation.test
 */

import { renderHook, act } from "@testing-library/react";
import { describe, it, expect, beforeEach } from "vitest";
import type { ReactNode } from "react";
import { useConversation } from "./useConversation";
import { ConversationProvider } from "../../contexts/ConversationContext/ConversationContext";

function wrapper({ children }: { children: ReactNode }) {
  return <ConversationProvider>{children}</ConversationProvider>;
}

// ── Group 1: Hook safety ──────────────────────────────────────────────────────

describe("useConversation — hook safety", () => {
  it("throws a descriptive error when used outside ConversationProvider", () => {
    const consoleError = console.error;
    console.error = () => {};

    expect(() => renderHook(() => useConversation())).toThrow(
      "useConversation must be used within a ConversationProvider",
    );

    console.error = consoleError;
  });
});

// ── Group 2: Initial state ────────────────────────────────────────────────────

describe("useConversation — initial state", () => {
  beforeEach(() => {
    localStorage.clear();
  });

  it("returns an empty conversations array on mount", () => {
    const { result } = renderHook(() => useConversation(), { wrapper });

    expect(result.current.conversations).toEqual([]);
  });

  it("returns null activeConversation on mount", () => {
    const { result } = renderHook(() => useConversation(), { wrapper });

    expect(result.current.activeConversation).toBeNull();
  });

  it("exposes all mutation callbacks as functions", () => {
    const { result } = renderHook(() => useConversation(), { wrapper });

    expect(typeof result.current.createNewConversation).toBe("function");
    expect(typeof result.current.switchConversation).toBe("function");
    expect(typeof result.current.deleteConversation).toBe("function");
    expect(typeof result.current.deleteAllConversations).toBe("function");
    expect(typeof result.current.renameConversation).toBe("function");
    expect(typeof result.current.addMessage).toBe("function");
    expect(typeof result.current.setIsConfirming).toBe("function");
    expect(typeof result.current.setStage).toBe("function");
    expect(typeof result.current.updatePerspectives).toBe("function");
  });
});

// ── Group 3: createNewConversation ────────────────────────────────────────────

describe("useConversation — createNewConversation", () => {
  beforeEach(() => {
    localStorage.clear();
  });

  it("adds a conversation and makes it active", () => {
    const { result } = renderHook(() => useConversation(), { wrapper });

    act(() => {
      result.current.createNewConversation();
    });

    expect(result.current.conversations).toHaveLength(1);
    expect(result.current.activeConversation).not.toBeNull();
  });

  it("returns the newly created conversation", () => {
    const { result } = renderHook(() => useConversation(), { wrapper });

    let created: ReturnType<typeof result.current.createNewConversation>;
    act(() => {
      created = result.current.createNewConversation();
    });

    expect(created!.id).toBe(result.current.activeConversation?.id);
  });
});

// ── Group 4: switchConversation ───────────────────────────────────────────────

describe("useConversation — switchConversation", () => {
  beforeEach(() => {
    localStorage.clear();
  });

  it("switches the active conversation to the given id", () => {
    const { result } = renderHook(() => useConversation(), { wrapper });

    let first: ReturnType<typeof result.current.createNewConversation>;
    let second: ReturnType<typeof result.current.createNewConversation>;

    act(() => {
      first = result.current.createNewConversation();
      second = result.current.createNewConversation();
    });

    // second is now active — switch back to first
    act(() => {
      result.current.switchConversation(first!.id);
    });

    expect(result.current.activeConversation?.id).toBe(first!.id);
    expect(result.current.activeConversation?.id).not.toBe(second!.id);
  });
});

// ── Group 5: deleteConversation ───────────────────────────────────────────────

describe("useConversation — deleteConversation", () => {
  beforeEach(() => {
    localStorage.clear();
  });

  it("removes the conversation from the list", () => {
    const { result } = renderHook(() => useConversation(), { wrapper });

    let conv: ReturnType<typeof result.current.createNewConversation>;
    act(() => {
      conv = result.current.createNewConversation();
    });

    act(() => {
      result.current.deleteConversation(conv!.id);
    });

    expect(result.current.conversations).toHaveLength(0);
  });
});
