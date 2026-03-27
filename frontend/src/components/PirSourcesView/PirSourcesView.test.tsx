/**
 * PirSourcesView — Direction phase view inside IntelligencePanel.
 *
 * Reads pirData and highlightedRefs from WorkspaceContext and renders
 * SourceList. Owns no state — the panel is a pure projection of context.
 *
 * Run with: cd frontend && npx vitest PirSourcesView.test
 */

import { screen, act } from "@testing-library/react";
import { describe, it, expect } from "vitest";
import userEvent from "@testing-library/user-event";
import { useEffect } from "react";
import PirSourcesView from "./PirSourcesView";
import { WorkspaceProvider, useWorkspace } from "../../contexts/WorkspaceContext/WorkspaceContext";
import { renderWithSettings } from "../../test/renderWithProviders";
import type { PirData } from "../../types/conversation";

// ── Seeder helpers ─────────────────────────────────────────────────────────────
// Sets pirData or highlightedRefs in context on mount so tests can start
// with pre-populated state without needing a button click.

function PirDataSeeder({ pirData }: { pirData: PirData }) {
  const { setPirData } = useWorkspace();
  useEffect(() => { setPirData(pirData); }, []);
  return null;
}

function HighlightSeeder({ ref }: { ref: string }) {
  const { setHighlightedRefs } = useWorkspace();
  useEffect(() => { setHighlightedRefs([ref]); }, []);
  return null;
}

// Displays the current highlightedRefs as a comma-joined string (or "empty").
function HighlightedRefsDisplay() {
  const { highlightedRefs } = useWorkspace();
  return <span data-testid="refs">{highlightedRefs.join(",") || "empty"}</span>;
}

// ── Fixtures ──────────────────────────────────────────────────────────────────

const pirDataWithSources: PirData = {
  pir_text: "Norway threat assessment.",
  claims: [],
  sources: [
    {
      id: "geopolitical/norway_russia",
      ref: "[1]",
      source_type: "kb",
      citation: {
        author: "Threat Intelligence System",
        year: "2025",
        title: "Norwegian-Russian Geopolitical Relations",
        publisher: "Internal Knowledge Bank",
      },
    },
    {
      id: "sectors/energy",
      ref: "[2]",
      source_type: "kb",
      citation: {
        author: "Threat Intelligence System",
        year: "2025",
        title: "Energy Sector Threat Landscape",
        publisher: "Internal Knowledge Bank",
      },
    },
  ],
  pirs: [],
  reasoning: "",
};

const pirDataNoSources: PirData = {
  pir_text: "No sources yet.",
  claims: [],
  sources: [],
  pirs: [],
  reasoning: "",
};

// ── Group 1: Empty state ──────────────────────────────────────────────────────

describe("PirSourcesView — empty state", () => {
  it("shows a placeholder when pirData is null (no PIR generated yet)", () => {
    renderWithSettings(
      <WorkspaceProvider>
        <PirSourcesView />
      </WorkspaceProvider>,
    );

    expect(screen.getByText(/no sources/i)).toBeInTheDocument();
  });

  it("shows a placeholder when pirData has no sources", async () => {
    renderWithSettings(
      <WorkspaceProvider>
        <PirDataSeeder pirData={pirDataNoSources} />
        <PirSourcesView />
      </WorkspaceProvider>,
    );

    await act(async () => {});

    expect(screen.getByText(/no sources/i)).toBeInTheDocument();
  });
});

// ── Group 2: Source rendering ─────────────────────────────────────────────────

describe("PirSourcesView — source rendering", () => {
  it("renders sources from context pirData in APA7th format", async () => {
    renderWithSettings(
      <WorkspaceProvider>
        <PirDataSeeder pirData={pirDataWithSources} />
        <PirSourcesView />
      </WorkspaceProvider>,
    );

    await act(async () => {});

    expect(
      screen.getByText(/Norwegian-Russian Geopolitical Relations/)
    ).toBeInTheDocument();
    expect(
      screen.getByText(/Energy Sector Threat Landscape/)
    ).toBeInTheDocument();
  });

  it("renders the ref marker for each source", async () => {
    renderWithSettings(
      <WorkspaceProvider>
        <PirDataSeeder pirData={pirDataWithSources} />
        <PirSourcesView />
      </WorkspaceProvider>,
    );

    await act(async () => {});

    expect(screen.getByText("[1]")).toBeInTheDocument();
    expect(screen.getByText("[2]")).toBeInTheDocument();
  });
});

// ── Group 3: Hover updates context ────────────────────────────────────────────

describe("PirSourcesView — hover updates context", () => {
  it("hovering a source card sets highlightedRefs in context", async () => {
    const user = userEvent.setup();

    renderWithSettings(
      <WorkspaceProvider>
        <PirDataSeeder pirData={pirDataWithSources} />
        <PirSourcesView />
        <HighlightedRefsDisplay />
      </WorkspaceProvider>,
    );

    await act(async () => {});

    const sourceCard = screen
      .getByText(/Norwegian-Russian Geopolitical Relations/)
      .closest("li")!;
    await user.hover(sourceCard);

    expect(screen.getByTestId("refs")).toHaveTextContent("[1]");
  });

  it("mouse leave on a source card clears highlightedRefs in context", async () => {
    const user = userEvent.setup();

    renderWithSettings(
      <WorkspaceProvider>
        <PirDataSeeder pirData={pirDataWithSources} />
        <PirSourcesView />
        <HighlightedRefsDisplay />
      </WorkspaceProvider>,
    );

    await act(async () => {});

    const sourceCard = screen
      .getByText(/Norwegian-Russian Geopolitical Relations/)
      .closest("li")!;
    await user.hover(sourceCard);
    await user.unhover(sourceCard);

    expect(screen.getByTestId("refs")).toHaveTextContent("empty");
  });
});

// ── Group 4: Highlight driven by context ─────────────────────────────────────

describe("PirSourcesView — highlight state from context", () => {
  it("source card is highlighted when context highlightedRefs includes its ref", async () => {
    renderWithSettings(
      <WorkspaceProvider>
        <PirDataSeeder pirData={pirDataWithSources} />
        <HighlightSeeder ref="[1]" />
        <PirSourcesView />
      </WorkspaceProvider>,
    );

    await act(async () => {});

    const sourceCard = screen
      .getByText(/Norwegian-Russian Geopolitical Relations/)
      .closest("li")!;
    expect(sourceCard).toHaveClass("text-primary");
  });

  it("only the matching card is highlighted when multiple sources exist", async () => {
    renderWithSettings(
      <WorkspaceProvider>
        <PirDataSeeder pirData={pirDataWithSources} />
        <HighlightSeeder ref="[1]" />
        <PirSourcesView />
      </WorkspaceProvider>,
    );

    await act(async () => {});

    const card1 = screen
      .getByText(/Norwegian-Russian Geopolitical Relations/)
      .closest("li")!;
    const card2 = screen
      .getByText(/Energy Sector Threat Landscape/)
      .closest("li")!;

    expect(card1).toHaveClass("text-primary");
    expect(card2).not.toHaveClass("text-primary");
  });
});
