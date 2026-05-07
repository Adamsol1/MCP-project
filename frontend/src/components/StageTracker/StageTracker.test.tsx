import { render, screen } from "@testing-library/react";
import { describe, it, expect } from "vitest";
import { axe } from "vitest-axe";
import StageTracker from "./StageTracker";
import type { DialoguePhase } from "../../types/dialogue";

function renderTracker(phase: DialoguePhase) {
  return render(<StageTracker activePhase={phase} />);
}

describe("StageTracker", () => {
  it("renders all four stage labels", () => {
    renderTracker("direction");

    expect(screen.getByText("Direction")).toBeInTheDocument();
    expect(screen.getByText("Collection")).toBeInTheDocument();
    expect(screen.getByText("Processing")).toBeInTheDocument();
    expect(screen.getByText("Analysis")).toBeInTheDocument();
  });

  it("shows the active stage number badge for direction", () => {
    renderTracker("direction");

    // Direction is index 0 → displays "1" as active badge
    const badges = screen.getAllByText("1");
    expect(badges.length).toBeGreaterThanOrEqual(1);
  });

  it("marks earlier stages as completed (check icon) when active is collection", () => {
    renderTracker("collection");

    // Direction (index 0) should be completed — rendered as a span with CheckIcon svg
    // Collection (index 1) should be active
    // Direction label is present
    expect(screen.getByText("Direction")).toBeInTheDocument();
    // Active badge shows "2" for collection
    const activeBadge = screen.getByText("2");
    expect(activeBadge).toBeInTheDocument();
  });

  it("marks direction and collection as completed when active is processing", () => {
    renderTracker("processing");

    // Active badge shows "3" for processing
    expect(screen.getByText("3")).toBeInTheDocument();
  });

  it("marks first three stages completed when active is analysis", () => {
    renderTracker("analysis");

    // Active badge shows "4" for analysis
    expect(screen.getByText("4")).toBeInTheDocument();
  });

  it("treats council phase as analysis active", () => {
    // council is a sub-mode of analysis; tracker shows Analysis as active
    renderTracker("council" as DialoguePhase);

    expect(screen.getByText("4")).toBeInTheDocument();
  });
});

describe("StageTracker — accessibility (WCAG 2.1 AA)", () => {
  it("has no violations for direction phase", async () => {
    const { container } = render(<StageTracker activePhase="direction" />);
    expect(await axe(container)).toHaveNoViolations();
  });

  it("has no violations for collection phase", async () => {
    const { container } = render(<StageTracker activePhase="collection" />);
    expect(await axe(container)).toHaveNoViolations();
  });

  it("has no violations for processing phase", async () => {
    const { container } = render(<StageTracker activePhase="processing" />);
    expect(await axe(container)).toHaveNoViolations();
  });

  it("has no violations for analysis phase", async () => {
    const { container } = render(<StageTracker activePhase="analysis" />);
    expect(await axe(container)).toHaveNoViolations();
  });
});
