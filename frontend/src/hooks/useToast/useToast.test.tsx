/**
 * useToast hook tests.
 *
 * useToast is a thin context accessor — these tests verify:
 *  1. The hook throws a descriptive error when called outside a ToastProvider.
 *  2. The hook returns the full context value when inside a ToastProvider.
 *  3. The convenience methods (success, error, warning, info) produce toasts
 *     with the correct type.
 *  4. addToast with explicit options overrides defaults.
 *  5. removeToast removes the correct toast by id.
 *
 * Run with: cd frontend && npx vitest useToast.test
 */

import { renderHook, act } from "@testing-library/react";
import { describe, it, expect } from "vitest";
import { useToast } from "./useToast";
import { ToastProvider } from "../../contexts/Toast/ToastContext";
import type { ReactNode } from "react";

// ── Wrapper helper ────────────────────────────────────────────────────────────

function wrapper({ children }: { children: ReactNode }) {
  return <ToastProvider>{children}</ToastProvider>;
}

// ── Group 1: Hook safety ──────────────────────────────────────────────────────

describe("useToast — hook safety", () => {
  it("throws a descriptive error when used outside ToastProvider", () => {
    const consoleError = console.error;
    console.error = () => {};

    expect(() => renderHook(() => useToast())).toThrow(
      "useToast must be used within a ToastProvider",
    );

    console.error = consoleError;
  });
});

// ── Group 2: Initial state ────────────────────────────────────────────────────

describe("useToast — initial state", () => {
  it("returns an empty toasts array on mount", () => {
    const { result } = renderHook(() => useToast(), { wrapper });

    expect(result.current.toasts).toEqual([]);
  });

  it("exposes addToast, removeToast, success, error, warning, and info as functions", () => {
    const { result } = renderHook(() => useToast(), { wrapper });

    expect(typeof result.current.addToast).toBe("function");
    expect(typeof result.current.removeToast).toBe("function");
    expect(typeof result.current.success).toBe("function");
    expect(typeof result.current.error).toBe("function");
    expect(typeof result.current.warning).toBe("function");
    expect(typeof result.current.info).toBe("function");
  });
});

// ── Group 3: addToast ─────────────────────────────────────────────────────────

describe("useToast — addToast", () => {
  it("adds a toast to the list", () => {
    const { result } = renderHook(() => useToast(), { wrapper });

    act(() => {
      result.current.addToast("Hello world");
    });

    expect(result.current.toasts).toHaveLength(1);
    expect(result.current.toasts[0].message).toBe("Hello world");
  });

  it("defaults toast type to 'info' when no type option is given", () => {
    const { result } = renderHook(() => useToast(), { wrapper });

    act(() => {
      result.current.addToast("Default type");
    });

    expect(result.current.toasts[0].type).toBe("info");
  });

  it("defaults duration to 5000ms when no duration option is given", () => {
    const { result } = renderHook(() => useToast(), { wrapper });

    act(() => {
      result.current.addToast("Default duration");
    });

    expect(result.current.toasts[0].duration).toBe(5000);
  });

  it("respects explicit type and duration options", () => {
    const { result } = renderHook(() => useToast(), { wrapper });

    act(() => {
      result.current.addToast("Custom toast", {
        type: "warning",
        duration: 3000,
      });
    });

    expect(result.current.toasts[0].type).toBe("warning");
    expect(result.current.toasts[0].duration).toBe(3000);
  });

  it("returns a unique id string", () => {
    const { result } = renderHook(() => useToast(), { wrapper });

    let id1: string;
    let id2: string;

    act(() => {
      id1 = result.current.addToast("First");
      id2 = result.current.addToast("Second");
    });

    expect(typeof id1!).toBe("string");
    expect(id1!).not.toBe(id2!);
  });

  it("appends multiple toasts in order", () => {
    const { result } = renderHook(() => useToast(), { wrapper });

    act(() => {
      result.current.addToast("First");
      result.current.addToast("Second");
      result.current.addToast("Third");
    });

    expect(result.current.toasts).toHaveLength(3);
    expect(result.current.toasts.map((t) => t.message)).toEqual([
      "First",
      "Second",
      "Third",
    ]);
  });
});

// ── Group 4: removeToast ──────────────────────────────────────────────────────

describe("useToast — removeToast", () => {
  it("removes the toast with the matching id", () => {
    const { result } = renderHook(() => useToast(), { wrapper });

    let id: string;
    act(() => {
      id = result.current.addToast("To be removed");
      result.current.addToast("To stay");
    });

    act(() => {
      result.current.removeToast(id!);
    });

    expect(result.current.toasts).toHaveLength(1);
    expect(result.current.toasts[0].message).toBe("To stay");
  });

  it("is a no-op when the id does not match any toast", () => {
    const { result } = renderHook(() => useToast(), { wrapper });

    act(() => {
      result.current.addToast("Existing toast");
    });

    act(() => {
      result.current.removeToast("non-existent-id");
    });

    expect(result.current.toasts).toHaveLength(1);
  });
});

// ── Group 5: Convenience methods ─────────────────────────────────────────────

describe("useToast — convenience methods", () => {
  it.each([
    ["success", "success"],
    ["error", "error"],
    ["warning", "warning"],
    ["info", "info"],
  ] as const)("%s() creates a toast with type '%s'", (method, expectedType) => {
    const { result } = renderHook(() => useToast(), { wrapper });

    act(() => {
      result.current[method](`${method} message`);
    });

    expect(result.current.toasts[0].type).toBe(expectedType);
    expect(result.current.toasts[0].message).toBe(`${method} message`);
  });

  it("convenience methods accept an optional custom duration", () => {
    const { result } = renderHook(() => useToast(), { wrapper });

    act(() => {
      result.current.success("Quick success", 1000);
    });

    expect(result.current.toasts[0].duration).toBe(1000);
  });

  it("convenience methods return the new toast id", () => {
    const { result } = renderHook(() => useToast(), { wrapper });

    let id: string;
    act(() => {
      id = result.current.error("Something went wrong");
    });

    expect(typeof id!).toBe("string");
    expect(result.current.toasts[0].id).toBe(id!);
  });
});
