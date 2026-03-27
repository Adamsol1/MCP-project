/**
 * IntelligencePanel — generic persistent shell hosting phase-specific views.
 *
 * Reads activePhase from WorkspaceContext and renders the correct view.
 * Knows nothing about PIR data, citations, or sources directly.
 *
 * Run with: cd frontend && npx vitest IntelligencePanel.test
 */

import { screen, act } from "@testing-library/react";
import { describe, it, expect, vi } from "vitest";
import { useEffect } from "react";
import IntelligencePanel from "./IntelligencePanel";
import {
  WorkspaceProvider,
  useWorkspace,
} from "../../contexts/WorkspaceContext/WorkspaceContext";
import { renderWithSettings } from "../../test/renderWithProviders";

// ── Default props ─────────────────────────────────────────────────────────────
// IntelligencePanel requires these three props. Tests that don't care about
// them use these no-op defaults.

const defaultProps = {
  selectedPerspectives: ["NEUTRAL"] as string[],
  onPerspectiveChange: vi.fn(),
  onOpenFileUpload: vi.fn(),
};

// ── Seeder helpers ────────────────────────────────────────────────────────────

type Phase = "direction" | "collection" | "processing" | "analysis";

function PhaseSeeder({ phase }: { phase: Phase }) {
  const { setActivePhase } = useWorkspace();
  useEffect(() => {
    setActivePhase(phase);
  }, []);
  return null;
}

// ── Group 1: Phase label header ───────────────────────────────────────────────

describe("IntelligencePanel — phase label", () => {
  it("displays the current phase label in the header", () => {
    // Default phase is 'direction' — phaseLabel renders as "DIRECTION".
    renderWithSettings(
      <WorkspaceProvider>
        <IntelligencePanel {...defaultProps} />
      </WorkspaceProvider>,
    );

    expect(screen.getByText(/direction/i)).toBeInTheDocument();
  });

  it("updates the phase label when activePhase changes", async () => {
    renderWithSettings(
      <WorkspaceProvider>
        <PhaseSeeder phase="collection" />
        <IntelligencePanel {...defaultProps} />
      </WorkspaceProvider>,
    );

    // After the seeder's useEffect fires, the h2 should reflect "COLLECTION".
    await act(async () => {});

    expect(screen.getByRole("heading", { name: /collection/i })).toBeInTheDocument();
  });
});

// ── Group 2: Phase view routing ───────────────────────────────────────────────

describe("IntelligencePanel — phase view routing", () => {
  it("renders the Direction view (PirSourcesView) when activePhase is 'direction'", () => {
    // Default phase is 'direction'. PirSourcesView renders "No sources available."
    // when pirData is null — use that as the signal it is mounted.
    renderWithSettings(
      <WorkspaceProvider>
        <IntelligencePanel {...defaultProps} />
      </WorkspaceProvider>,
    );

    expect(screen.getByText(/no sources/i)).toBeInTheDocument();
  });

  it("renders the Collection view when activePhase is 'collection'", async () => {
    renderWithSettings(
      <WorkspaceProvider>
        <PhaseSeeder phase="collection" />
        <IntelligencePanel {...defaultProps} />
      </WorkspaceProvider>,
    );

    await act(async () => {});

    // Header reflects the phase, PirSourcesView is not mounted.
    expect(screen.getByRole("heading", { name: /collection/i })).toBeInTheDocument();
    expect(screen.queryByText(/no sources available/i)).not.toBeInTheDocument();
  });

  it("renders the Processing view when activePhase is 'processing'", async () => {
    renderWithSettings(
      <WorkspaceProvider>
        <PhaseSeeder phase="processing" />
        <IntelligencePanel {...defaultProps} />
      </WorkspaceProvider>,
    );

    await act(async () => {});

    expect(screen.getByRole("heading", { name: /processing/i })).toBeInTheDocument();
    expect(screen.queryByText(/no sources available/i)).not.toBeInTheDocument();
  });

  it("renders the Analysis view when activePhase is 'analysis'", async () => {
    renderWithSettings(
      <WorkspaceProvider>
        <PhaseSeeder phase="analysis" />
        <IntelligencePanel {...defaultProps} />
      </WorkspaceProvider>,
    );

    await act(async () => {});

    expect(screen.getByRole("heading", { name: /analysis/i })).toBeInTheDocument();
    expect(screen.queryByText(/no sources available/i)).not.toBeInTheDocument();
  });
});
