/**
 * WorkspaceContext — shared state for the intelligence workspace.
 *
 * Provides highlightedRef, pirData, and activePhase across the
 * chat↔panel boundary so bidirectional hover works even when
 * CitationText (in the chat) and SourceList (in the panel) are siblings.
 *
 * Run with: cd frontend && npx vitest WorkspaceContext.test
 */

import { render, screen, act } from "@testing-library/react";
import { describe, it, expect } from "vitest";
import { WorkspaceProvider, useWorkspace } from "./WorkspaceContext";
import type { PirData } from "../../types/conversation";


// ── Test consumer helpers ─────────────────────────────────────────────────────
// Minimal components that render one context value each into the DOM.
// Real components will consume the context the same way.

function HighlightedRefDisplay() {
  const { highlightedRef } = useWorkspace();
  return <span data-testid="ref">{highlightedRef ?? "null"}</span>;
}

function PirDataDisplay() {
  const { pirData } = useWorkspace();
  return <span data-testid="pir">{pirData ? pirData.pir_text : "null"}</span>;
}

function ActivePhaseDisplay() {
  const { activePhase } = useWorkspace();
  return <span data-testid="phase">{activePhase}</span>;
}

function SetHighlightedRefButton() {
  const { setHighlightedRef } = useWorkspace();
  return (
    <button onClick={() => setHighlightedRef("[1]")}>set ref</button>
  );
}

function ClearHighlightedRefButton() {
  const { setHighlightedRef } = useWorkspace();
  return (
    <button onClick={() => setHighlightedRef(null)}>clear ref</button>
  );
}

function SetPirDataButton({ pirData }: { pirData: PirData }) {
  const { setPirData } = useWorkspace();
  return (
    <button onClick={() => setPirData(pirData)}>set pir</button>
  );
}

function SetActivePhaseButton({ phase }: { phase: string }) {
  const { setActivePhase } = useWorkspace();
  return (
    // The cast satisfies TypeScript until the union type is defined in the impl.
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    <button onClick={() => setActivePhase(phase as any)}>set phase</button>
  );
}

// ── Fixture ───────────────────────────────────────────────────────────────────

const samplePirData: PirData = {
  pir_text: "Norway threat assessment.",
  claims: [],
  sources: [],
  pirs: [],
  reasoning: "",
};

// ── Group 1: Default values ───────────────────────────────────────────────────

describe("WorkspaceContext — default values", () => {
  it("highlightedRef defaults to null", () => {
    render(
      <WorkspaceProvider>
        <HighlightedRefDisplay />
      </WorkspaceProvider>
    );

    expect(screen.getByTestId("ref")).toHaveTextContent("null");
  });

  it("pirData defaults to null", () => {
    render(
      <WorkspaceProvider>
        <PirDataDisplay />
      </WorkspaceProvider>
    );

    expect(screen.getByTestId("pir")).toHaveTextContent("null");
  });

  it("activePhase defaults to 'direction'", () => {
    render(
      <WorkspaceProvider>
        <ActivePhaseDisplay />
      </WorkspaceProvider>
    );

    expect(screen.getByTestId("phase")).toHaveTextContent("direction");
  });
});

// ── Group 2: State updates propagate to all consumers ─────────────────────────

describe("WorkspaceContext — state updates", () => {
  it("setHighlightedRef updates highlightedRef", async () => {
    render(
      <WorkspaceProvider>
        <HighlightedRefDisplay />
        <SetHighlightedRefButton />
      </WorkspaceProvider>
    );

    expect(screen.getByTestId("ref")).toHaveTextContent("null");

    await act(async () => {
      screen.getByRole("button", { name: "set ref" }).click();
    });

    expect(screen.getByTestId("ref")).toHaveTextContent("[1]");
  });

  it("setHighlightedRef can clear back to null", async () => {
    render(
      <WorkspaceProvider>
        <HighlightedRefDisplay />
        <SetHighlightedRefButton />
        <ClearHighlightedRefButton />
      </WorkspaceProvider>
    );

    await act(async () => {
      screen.getByRole("button", { name: "set ref" }).click();
    });
    expect(screen.getByTestId("ref")).toHaveTextContent("[1]");

    await act(async () => {
      screen.getByRole("button", { name: "clear ref" }).click();
    });
    expect(screen.getByTestId("ref")).toHaveTextContent("null");
  });

  it("setPirData updates pirData", async () => {
    render(
      <WorkspaceProvider>
        <PirDataDisplay />
        <SetPirDataButton pirData={samplePirData} />
      </WorkspaceProvider>
    );

    expect(screen.getByTestId("pir")).toHaveTextContent("null");

    await act(async () => {
      screen.getByRole("button", { name: "set pir" }).click();
    });

    expect(screen.getByTestId("pir")).toHaveTextContent(
      "Norway threat assessment."
    );
  });

  it("setActivePhase updates activePhase", async () => {
    render(
      <WorkspaceProvider>
        <ActivePhaseDisplay />
        <SetActivePhaseButton phase="collection" />
      </WorkspaceProvider>
    );

    expect(screen.getByTestId("phase")).toHaveTextContent("direction");

    await act(async () => {
      screen.getByRole("button", { name: "set phase" }).click();
    });

    expect(screen.getByTestId("phase")).toHaveTextContent("collection");
  });
});

// ── Group 3: Hook safety ──────────────────────────────────────────────────────

describe("WorkspaceContext — useWorkspace hook", () => {
  it("throws when used outside WorkspaceProvider", () => {
    // React will log an uncaught error to the console during this test.
    // We silence it temporarily so the test output stays clean.
    const consoleError = console.error;
    console.error = () => {};

    expect(() => {
      render(<HighlightedRefDisplay />);
    }).toThrow();

    console.error = consoleError;
  });
});
