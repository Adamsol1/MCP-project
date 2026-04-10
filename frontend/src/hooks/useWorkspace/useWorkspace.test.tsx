import { renderHook, act } from "@testing-library/react";
import { describe, it, expect } from "vitest";
import type { ReactNode } from "react";
import { useWorkspace } from "./useWorkspace";
import { WorkspaceProvider } from "../../contexts/WorkspaceContext/WorkspaceContext";
import type { PirData } from "../../types/conversation";

function wrapper({ children }: { children: ReactNode }) {
  return <WorkspaceProvider>{children}</WorkspaceProvider>;
}

describe("useWorkspace", () => {
  it("throws a descriptive error when used outside WorkspaceProvider", () => {
    const consoleError = console.error;
    console.error = () => {};

    expect(() => renderHook(() => useWorkspace())).toThrow(
      "useWorkspace must be used within a WorkspaceProvider",
    );

    console.error = consoleError;
  });

  it("starts with empty workspace data", () => {
    const { result } = renderHook(() => useWorkspace(), { wrapper });

    expect(result.current.highlightedRef).toBeNull();
    expect(result.current.highlightedRefs).toEqual([]);
    expect(result.current.pirData).toBeNull();
    expect(result.current.collectionData).toBeNull();
  });

  it("updates highlighted refs through the exposed setters", () => {
    const { result } = renderHook(() => useWorkspace(), { wrapper });

    act(() => {
      result.current.setHighlightedRef("ref-1");
    });

    expect(result.current.highlightedRef).toBe("ref-1");
    expect(result.current.highlightedRefs).toEqual(["ref-1"]);

    act(() => {
      result.current.setHighlightedRefs(["ref-a", "ref-b"]);
    });

    expect(result.current.highlightedRef).toBe("ref-a");
    expect(result.current.highlightedRefs).toEqual(["ref-a", "ref-b"]);
  });

  it("updates and clears pirData", () => {
    const { result } = renderHook(() => useWorkspace(), { wrapper });
    const pirData: PirData = {
      pir_text: "Test PIR",
      claims: [],
      sources: [],
      pirs: [],
      reasoning: "Test reasoning",
    };

    act(() => {
      result.current.setPirData(pirData);
    });

    expect(result.current.pirData).toEqual(pirData);

    act(() => {
      result.current.setPirData(null);
    });

    expect(result.current.pirData).toBeNull();
  });

  it("updates and clears collectionData", () => {
    const { result } = renderHook(() => useWorkspace(), { wrapper });

    act(() => {
      result.current.setCollectionData({
        collected_data: [],
        source_summary: [],
      });
    });

    expect(result.current.collectionData).toEqual({
      collected_data: [],
      source_summary: [],
    });

    act(() => {
      result.current.setCollectionData(null);
    });

    expect(result.current.collectionData).toBeNull();
  });
});
