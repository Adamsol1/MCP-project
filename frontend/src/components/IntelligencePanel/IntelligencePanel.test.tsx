import { render, screen } from "@testing-library/react";
import { describe, it, expect } from "vitest";
import IntelligencePanel from "./IntelligencePanel";
import { WorkspaceProvider } from "../../contexts/WorkspaceContext/WorkspaceContext";
import { ConversationProvider } from "../../contexts/ConversationContext/ConversationContext";
import { SettingsProvider } from "../../contexts/SettingsContext/SettingsContext";
import type { DialoguePhase } from "../../types/dialogue";

function renderPanel(phase: DialoguePhase) {
  return render(
    <SettingsProvider>
      <ConversationProvider>
        <WorkspaceProvider>
          <IntelligencePanel phase={phase} />
        </WorkspaceProvider>
      </ConversationProvider>
    </SettingsProvider>,
  );
}

describe("IntelligencePanel", () => {
  it("renders the direction header and view", () => {
    renderPanel("direction");

    expect(screen.getByRole("heading", { name: /direction/i })).toBeInTheDocument();
    expect(screen.getByText(/no sources/i)).toBeInTheDocument();
  });

  it("renders the collection header and hides the direction view", () => {
    renderPanel("collection");

    expect(screen.getByRole("heading", { name: /collection/i })).toBeInTheDocument();
    expect(screen.queryByText(/no sources available/i)).not.toBeInTheDocument();
  });

  it("renders the processing header", () => {
    renderPanel("processing");

    expect(screen.getByRole("heading", { name: /processing/i })).toBeInTheDocument();
    expect(screen.getByText(/processing artifacts/i)).toBeInTheDocument();
  });

  it("renders the analysis header", () => {
    renderPanel("analysis");

    expect(screen.getByRole("heading", { name: /analysis/i })).toBeInTheDocument();
    expect(screen.getByText(/analysis outputs/i)).toBeInTheDocument();
  });
});
