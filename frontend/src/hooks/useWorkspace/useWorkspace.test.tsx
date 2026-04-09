/**
 * useWorkspace hook tests.
 *
 * useWorkspace is a thin context accessor — these tests verify:
 *  1. The hook throws a descriptive error when called outside a WorkspaceProvider.
 *  2. The hook returns the full context value when inside a WorkspaceProvider.
 *  3. State setters update values correctly.
 *
 * Run with: cd frontend && npx vitest useWorkspace.test
 */

import { renderHook, act } from "@testing-library/react";
import { describe, it, expect } from "vitest";
import type { ReactNode } from "react";
import { useWorkspace } from "./useWorkspace";
import { WorkspaceProvider } from "../../contexts/WorkspaceContext/WorkspaceContext";

function wrapper({ children }: { children: ReactNode }) {
  return <WorkspaceProvider>{children}</WorkspaceProvider>;
}

// ── Group 1: Hook safety ──────────────────────────────────────────────────────

describe("useWorkspace — hook safety", () => {
  it("throws a descriptive error when used outside WorkspaceProvider", () => {
    const consoleError = console.error;
    console.error = () => {};

    expect(() => renderHook(() => useWorkspace())).toThrow(
      "useWorkspace must be used within a WorkspaceProvider",
    );

    console.error = consoleError;
  });
});

// ── Group 2: Initial state ────────────────────────────────────────────────────

describe("useWorkspace — initial state", () => {
  it("starts with activePhase set to 'direction'", () => {
    const { result } = renderHook(() => useWorkspace(), { wrapper });

    expect(result.current.activePhase).toBe("direction");
  });

  it("starts with null highlightedRef", () => {
    const { result } = renderHook(() => useWorkspace(), { wrapper });

    expect(result.current.highlightedRef).toBeNull();
  });

  it("starts with an empty highlightedRefs array", () => {
    const { result } = renderHook(() => useWorkspace(), { wrapper });

    expect(result.current.highlightedRefs).toEqual([]);
  });

  it("starts with null pirData", () => {
    const { result } = renderHook(() => useWorkspace(), { wrapper });

    expect(result.current.pirData).toBeNull();
  });

  it("starts with null collectionData", () => {
    const { result } = renderHook(() => useWorkspace(), { wrapper });

    expect(result.current.collectionData).toBeNull();
  });

  it("exposes all setters as functions", () => {
    const { result } = renderHook(() => useWorkspace(), { wrapper });

    expect(typeof result.current.setActivePhase).toBe("function");
    expect(typeof result.current.setHighlightedRef).toBe("function");
    expect(typeof result.current.setHighlightedRefs).toBe("function");
    expect(typeof result.current.setPirData).toBe("function");
    expect(typeof result.current.setCollectionData).toBe("function");
  });
});

// ── Group 3: setActivePhase ───────────────────────────────────────────────────

describe("useWorkspace — setActivePhase", () => {
  it.each(["direction", "collection", "processing", "analysis"] as const)(
    "sets activePhase to '%s'",
    (phase) => {
      const { result } = renderHook(() => useWorkspace(), { wrapper });

      act(() => {
        result.current.setActivePhase(phase);
      });

      expect(result.current.activePhase).toBe(phase);
    },
  );
});

// ── Group 4: setHighlightedRef ────────────────────────────────────────────────

describe("useWorkspace — setHighlightedRef", () => {
  it("sets highlightedRef and populates highlightedRefs", () => {
    const { result } = renderHook(() => useWorkspace(), { wrapper });

    act(() => {
      result.current.setHighlightedRef("ref-1");
    });

    expect(result.current.highlightedRef).toBe("ref-1");
    expect(result.current.highlightedRefs).toEqual(["ref-1"]);
  });

  it("clears highlightedRef when set to null", () => {
    const { result } = renderHook(() => useWorkspace(), { wrapper });

    act(() => {
      result.current.setHighlightedRef("ref-1");
    });
    act(() => {
      result.current.setHighlightedRef(null);
    });

    expect(result.current.highlightedRef).toBeNull();
    expect(result.current.highlightedRefs).toEqual([]);
  });
});

// ── Group 5: setHighlightedRefs ───────────────────────────────────────────────

describe("useWorkspace — setHighlightedRefs", () => {
  it("sets multiple highlighted refs", () => {
    const { result } = renderHook(() => useWorkspace(), { wrapper });

    act(() => {
      result.current.setHighlightedRefs(["ref-a", "ref-b", "ref-c"]);
    });

    expect(result.current.highlightedRefs).toEqual(["ref-a", "ref-b", "ref-c"]);
    expect(result.current.highlightedRef).toBe("ref-a");
  });
});

// ── Group 6: setPirData ───────────────────────────────────────────────────────

import type { PirData } from "../../types/conversation";

const mockPirData: PirData = {
  pir_text: "Test PIR",
  claims: [],
  sources: [],
  pirs: [],
  reasoning: "Test reasoning",
};

describe("useWorkspace — setPirData", () => {
  it("updates pirData", () => {
    const { result } = renderHook(() => useWorkspace(), { wrapper });

    act(() => {
      result.current.setPirData(mockPirData);
    });

    expect(result.current.pirData).toEqual(mockPirData);
  });

  it("clears pirData when set to null", () => {
    const { result } = renderHook(() => useWorkspace(), { wrapper });

    act(() => {
      result.current.setPirData(mockPirData);
    });
    act(() => {
      result.current.setPirData(null);
    });

    expect(result.current.pirData).toBeNull();
  });
});
