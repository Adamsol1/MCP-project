/**
 * WorkspaceContext — shared state for the intelligence workspace.
 *
 * Provides highlightedRefs, pirData, activePhase, and collectionData across
 * the chat↔panel boundary so bidirectional hover works even when CitationText
 * (in the chat) and SourceList (in the panel) are siblings.
 *
 * Run with: cd frontend && npx vitest WorkspaceContext.test
 */

import { render, screen, act } from "@testing-library/react";
import { describe, it, expect } from "vitest";
import { WorkspaceProvider, useWorkspace } from "./WorkspaceContext";
import type { CollectionDisplayData, PirData } from "../../types/conversation";

// ── Test consumer helpers ─────────────────────────────────────────────────────
// Minimal components that render one context value each into the DOM.
// Real components will consume the context the same way.

function HighlightedRefsDisplay() {
  const { highlightedRefs } = useWorkspace();
  return <span data-testid="refs">{highlightedRefs.join(",") || "empty"}</span>;
}

function PirDataDisplay() {
  const { pirData } = useWorkspace();
  return <span data-testid="pir">{pirData ? pirData.pir_text : "null"}</span>;
}

function ActivePhaseDisplay() {
  const { activePhase } = useWorkspace();
  return <span data-testid="phase">{activePhase}</span>;
}

function CollectionDataDisplay() {
  const { collectionData } = useWorkspace();
  return (
    <span data-testid="collection">
      {collectionData ? collectionData.collected_data.length.toString() : "null"}
    </span>
  );
}

function SetHighlightedRefsButton({ refs }: { refs: string[] }) {
  const { setHighlightedRefs } = useWorkspace();
  return <button onClick={() => setHighlightedRefs(refs)}>set refs</button>;
}

function ClearHighlightedRefsButton() {
  const { setHighlightedRefs } = useWorkspace();
  return <button onClick={() => setHighlightedRefs([])}>clear refs</button>;
}

function SetPirDataButton({ pirData }: { pirData: PirData }) {
  const { setPirData } = useWorkspace();
  return <button onClick={() => setPirData(pirData)}>set pir</button>;
}

function ClearPirDataButton() {
  const { setPirData } = useWorkspace();
  return <button onClick={() => setPirData(null)}>clear pir</button>;
}

function SetActivePhaseButton({ phase }: { phase: string }) {
  const { setActivePhase } = useWorkspace();
  return (
    // The cast satisfies TypeScript — tests cover all valid phase values below.
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    <button onClick={() => setActivePhase(phase as any)}>set phase</button>
  );
}

function SetCollectionDataButton({ data }: { data: CollectionDisplayData }) {
  const { setCollectionData } = useWorkspace();
  return <button onClick={() => setCollectionData(data)}>set collection</button>;
}

function ClearCollectionDataButton() {
  const { setCollectionData } = useWorkspace();
  return <button onClick={() => setCollectionData(null)}>clear collection</button>;
}

// ── Fixtures ──────────────────────────────────────────────────────────────────

const samplePirData: PirData = {
  pir_text: "Norway threat assessment.",
  claims: [],
  sources: [],
  pirs: [],
  reasoning: "",
};

const sampleCollectionData: CollectionDisplayData = {
  collected_data: [
    {
      source: "web",
      resource_id: null,
      content: "Sample collected content",
    },
  ],
  source_summary: [
    {
      display_name: "Web",
      count: 1,
      resource_ids: [],
      has_content: true,
    },
  ],
};

// ── Group 1: Default values ───────────────────────────────────────────────────

describe("WorkspaceContext — default values", () => {
  it("highlightedRefs defaults to an empty array", () => {
    render(
      <WorkspaceProvider>
        <HighlightedRefsDisplay />
      </WorkspaceProvider>,
    );

    expect(screen.getByTestId("refs")).toHaveTextContent("empty");
  });

  it("pirData defaults to null", () => {
    render(
      <WorkspaceProvider>
        <PirDataDisplay />
      </WorkspaceProvider>,
    );

    expect(screen.getByTestId("pir")).toHaveTextContent("null");
  });

  it("activePhase defaults to 'direction'", () => {
    render(
      <WorkspaceProvider>
        <ActivePhaseDisplay />
      </WorkspaceProvider>,
    );

    expect(screen.getByTestId("phase")).toHaveTextContent("direction");
  });

  it("collectionData defaults to null", () => {
    render(
      <WorkspaceProvider>
        <CollectionDataDisplay />
      </WorkspaceProvider>,
    );

    expect(screen.getByTestId("collection")).toHaveTextContent("null");
  });
});

// ── Group 2: highlightedRefs updates ─────────────────────────────────────────

describe("WorkspaceContext — highlightedRefs", () => {
  it("setHighlightedRefs updates the ref list", async () => {
    render(
      <WorkspaceProvider>
        <HighlightedRefsDisplay />
        <SetHighlightedRefsButton refs={["[1]", "[2]"]} />
      </WorkspaceProvider>,
    );

    expect(screen.getByTestId("refs")).toHaveTextContent("empty");

    await act(async () => {
      screen.getByRole("button", { name: "set refs" }).click();
    });

    expect(screen.getByTestId("refs")).toHaveTextContent("[1],[2]");
  });

  it("setHighlightedRefs can clear back to an empty array", async () => {
    render(
      <WorkspaceProvider>
        <HighlightedRefsDisplay />
        <SetHighlightedRefsButton refs={["[1]"]} />
        <ClearHighlightedRefsButton />
      </WorkspaceProvider>,
    );

    await act(async () => {
      screen.getByRole("button", { name: "set refs" }).click();
    });
    expect(screen.getByTestId("refs")).toHaveTextContent("[1]");

    await act(async () => {
      screen.getByRole("button", { name: "clear refs" }).click();
    });
    expect(screen.getByTestId("refs")).toHaveTextContent("empty");
  });

  it("setHighlightedRefs replaces the previous list entirely", async () => {
    render(
      <WorkspaceProvider>
        <HighlightedRefsDisplay />
        <SetHighlightedRefsButton refs={["[1]", "[2]"]} />
      </WorkspaceProvider>,
    );

    await act(async () => {
      screen.getByRole("button", { name: "set refs" }).click();
    });
    expect(screen.getByTestId("refs")).toHaveTextContent("[1],[2]");

    // Re-render with a different ref list to verify replacement (not append)
    render(
      <WorkspaceProvider>
        <HighlightedRefsDisplay />
        <SetHighlightedRefsButton refs={["[3]"]} />
      </WorkspaceProvider>,
    );

    await act(async () => {
      screen.getAllByRole("button", { name: "set refs" })[1].click();
    });
    expect(screen.getAllByTestId("refs")[1]).toHaveTextContent("[3]");
  });
});

// ── Group 3: pirData updates ──────────────────────────────────────────────────

describe("WorkspaceContext — pirData", () => {
  it("setPirData updates pirData", async () => {
    render(
      <WorkspaceProvider>
        <PirDataDisplay />
        <SetPirDataButton pirData={samplePirData} />
      </WorkspaceProvider>,
    );

    expect(screen.getByTestId("pir")).toHaveTextContent("null");

    await act(async () => {
      screen.getByRole("button", { name: "set pir" }).click();
    });

    expect(screen.getByTestId("pir")).toHaveTextContent(
      "Norway threat assessment.",
    );
  });

  it("setPirData can be cleared back to null", async () => {
    render(
      <WorkspaceProvider>
        <PirDataDisplay />
        <SetPirDataButton pirData={samplePirData} />
        <ClearPirDataButton />
      </WorkspaceProvider>,
    );

    await act(async () => {
      screen.getByRole("button", { name: "set pir" }).click();
    });
    expect(screen.getByTestId("pir")).toHaveTextContent(
      "Norway threat assessment.",
    );

    await act(async () => {
      screen.getByRole("button", { name: "clear pir" }).click();
    });
    expect(screen.getByTestId("pir")).toHaveTextContent("null");
  });
});

// ── Group 4: activePhase updates ─────────────────────────────────────────────

describe("WorkspaceContext — activePhase", () => {
  it.each(["direction", "collection", "processing", "analysis"] as const)(
    "setActivePhase accepts phase '%s'",
    async (phase) => {
      render(
        <WorkspaceProvider>
          <ActivePhaseDisplay />
          <SetActivePhaseButton phase={phase} />
        </WorkspaceProvider>,
      );

      await act(async () => {
        screen.getByRole("button", { name: "set phase" }).click();
      });

      expect(screen.getByTestId("phase")).toHaveTextContent(phase);
    },
  );
});

// ── Group 5: collectionData updates ──────────────────────────────────────────

describe("WorkspaceContext — collectionData", () => {
  it("setCollectionData updates collectionData", async () => {
    render(
      <WorkspaceProvider>
        <CollectionDataDisplay />
        <SetCollectionDataButton data={sampleCollectionData} />
      </WorkspaceProvider>,
    );

    expect(screen.getByTestId("collection")).toHaveTextContent("null");

    await act(async () => {
      screen.getByRole("button", { name: "set collection" }).click();
    });

    expect(screen.getByTestId("collection")).toHaveTextContent("1");
  });

  it("setCollectionData can be cleared back to null", async () => {
    render(
      <WorkspaceProvider>
        <CollectionDataDisplay />
        <SetCollectionDataButton data={sampleCollectionData} />
        <ClearCollectionDataButton />
      </WorkspaceProvider>,
    );

    await act(async () => {
      screen.getByRole("button", { name: "set collection" }).click();
    });
    expect(screen.getByTestId("collection")).toHaveTextContent("1");

    await act(async () => {
      screen.getByRole("button", { name: "clear collection" }).click();
    });
    expect(screen.getByTestId("collection")).toHaveTextContent("null");
  });
});

// ── Group 6: useWorkspace hook safety ─────────────────────────────────────────

describe("WorkspaceContext — useWorkspace hook", () => {
  it("throws a descriptive error when used outside WorkspaceProvider", () => {
    // React will log an uncaught error to the console during this test.
    // We silence it temporarily so the test output stays clean.
    const consoleError = console.error;
    console.error = () => {};

    expect(() => {
      render(<HighlightedRefsDisplay />);
    }).toThrow("useWorkspace must be used within a WorkspaceProvider");

    console.error = consoleError;
  });
});
