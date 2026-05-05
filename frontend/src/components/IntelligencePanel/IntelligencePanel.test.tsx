import { render, screen } from "@testing-library/react";
import { describe, it, expect } from "vitest";
import IntelligencePanel from "./IntelligencePanel";
import { WorkspaceProvider } from "../../contexts/WorkspaceContext/WorkspaceContext";
import { ConversationProvider } from "../../contexts/ConversationContext/ConversationContext";
import { SettingsProvider } from "../../contexts/SettingsContext/SettingsContext";
import type { DialoguePhase } from "../../types/dialogue";
import { axe } from "vitest-axe";

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
    // Direction phase shows perspective selector, not a sources list
    expect(screen.queryByText(/no sources available/i)).not.toBeInTheDocument();
  });

  it("renders the collection header and hides the direction view", () => {
    renderPanel("collection");

    expect(screen.getByRole("heading", { name: /collection/i })).toBeInTheDocument();
    expect(screen.queryByText(/no sources available/i)).not.toBeInTheDocument();
  });

  it("renders the processing header", () => {
    renderPanel("processing");

    expect(screen.getByRole("heading", { name: /processing/i })).toBeInTheDocument();
    // Processing phase shows the file upload section
    expect(screen.getByText(/upload files/i)).toBeInTheDocument();
  });

  it("renders the analysis header", () => {
    renderPanel("analysis");

    expect(screen.getByRole("heading", { name: /analysis/i })).toBeInTheDocument();
    // Analysis phase shows the file upload section
    expect(screen.getByText(/upload files/i)).toBeInTheDocument();
  });
});

describe("IntelligencePanel — accessibility (WCAG 2.1 AA)", () => {
  it("has no violations in direction phase", async () => {
    const { container } = renderPanel("direction");
    expect(await axe(container)).toHaveNoViolations();
  });

  it("has no violations in collection phase", async () => {
    const { container } = renderPanel("collection");
    expect(await axe(container)).toHaveNoViolations();
  });
});
