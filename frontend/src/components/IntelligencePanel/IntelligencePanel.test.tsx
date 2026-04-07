/**
 * IntelligencePanel — generic persistent shell hosting phase-specific views.
 *
 * Reads activePhase from WorkspaceContext and renders the correct view.
 * Knows nothing about PIR data, citations, or sources directly.
 *
 * Run with: cd frontend && npx vitest IntelligencePanel.test
 */

import { render, screen, act } from "@testing-library/react";
import { describe, it, expect } from "vitest";
import { useEffect } from "react";
import IntelligencePanel from "./IntelligencePanel";
import {
  WorkspaceProvider,
  useWorkspace,
} from "../../contexts/WorkspaceContext/WorkspaceContext";
import { ConversationProvider } from "../../contexts/ConversationContext/ConversationContext";

// ── Seeder helpers ────────────────────────────────────────────────────────────

type Phase = "direction" | "collection" | "processing" | "analysis";

function PhaseSeeder({ phase }: { phase: Phase }) {
  const { setActivePhase } = useWorkspace();
  useEffect(() => {
    setActivePhase(phase);
  }, [phase, setActivePhase]);
  return null;
}

// ── Group 1: Phase label header ───────────────────────────────────────────────

describe("IntelligencePanel — phase label", () => {
  it("displays the current phase label in the header", () => {
    // Default phase is 'direction' — no seeder needed.
    render(
      <ConversationProvider>
      <WorkspaceProvider>
        <IntelligencePanel />
      </WorkspaceProvider>
      </ConversationProvider>
    );

    expect(screen.getByRole("heading", { name: /direction/i })).toBeInTheDocument();
  });

  it("updates the phase label when activePhase changes", async () => {
    render(
      <ConversationProvider>
      <WorkspaceProvider>
        <PhaseSeeder phase="collection" />
        <IntelligencePanel />
      </WorkspaceProvider>
      </ConversationProvider>
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
    render(
      <ConversationProvider>
      <WorkspaceProvider>
        <IntelligencePanel />
      </WorkspaceProvider>
      </ConversationProvider>
    );

    expect(screen.getByText(/no sources/i)).toBeInTheDocument();
  });

  it("renders a placeholder for the 'collection' phase", async () => {
    render(
      <ConversationProvider>
      <WorkspaceProvider>
        <PhaseSeeder phase="collection" />
        <IntelligencePanel />
      </WorkspaceProvider>
      </ConversationProvider>
    );

    await act(async () => {});

    // Header reflects the phase, PirSourcesView is not mounted.
    expect(screen.getByRole("heading", { name: /collection/i })).toBeInTheDocument();
    expect(screen.queryByText(/no sources available/i)).not.toBeInTheDocument();
  });

  it("renders a placeholder for the 'processing' phase", async () => {
    render(
      <ConversationProvider>
      <WorkspaceProvider>
        <PhaseSeeder phase="processing" />
        <IntelligencePanel />
      </WorkspaceProvider>
      </ConversationProvider>
    );

    await act(async () => {});

    expect(screen.getByRole("heading", { name: /processing/i })).toBeInTheDocument();
    expect(screen.queryByText(/no sources available/i)).not.toBeInTheDocument();
  });

  it("renders the analysis prototype view for the 'analysis' phase", async () => {
    render(
      <ConversationProvider>
      <WorkspaceProvider>
        <PhaseSeeder phase="analysis" />
        <IntelligencePanel />
      </WorkspaceProvider>
      </ConversationProvider>
    );

    await act(async () => {});

    expect(screen.getByRole("heading", { name: /analysis/i })).toBeInTheDocument();
    expect(screen.queryByText(/no sources/i)).not.toBeInTheDocument();
    expect(
      screen.getByText(/create or select a conversation to load the analysis prototype/i),
    ).toBeInTheDocument();
  });
});
