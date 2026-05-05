/**
 * PerspectiveSelector — toggle buttons for geopolitical analysis perspectives.
 *
 * PerspectiveSelector is a controlled component that calls onChange whenever
 * the user toggles a perspective. GLOBAL (NEUTRAL) is selected by default.
 *
 * Props:
 *   selected: string[]           — currently selected perspective IDs
 *   onChange: (perspectives: string[]) => void  — called when selection changes
 *
 * Run with: cd frontend && npx vitest PerspectiveSelector.test
 */

import { screen } from "@testing-library/react";
import { describe, it, expect, vi } from "vitest";
import userEvent from "@testing-library/user-event";
import PerspectiveSelector from "./PerspectiveSelector";
import { renderWithSettings } from "../../test/renderWithProviders";
import { axe } from "vitest-axe";

// Labels as rendered by the component (from en.ts perspectiveLabels).
// These are the abbreviated labels shown in the grid buttons.
const PERSPECTIVE_LABELS: Record<string, string> = {
  US: "US",
  NORWAY: "Norway",
  CHINA: "China",
  EU: "EU",
  RUSSIA: "Russia",
  NEUTRAL: "Global",
};

describe("PerspectiveSelector", () => {
  // ---------- Rendering ----------

  it("renders all six perspective options", () => {
    renderWithSettings(
      <PerspectiveSelector selected={["NEUTRAL"]} onChange={vi.fn()} />,
    );

    for (const label of Object.values(PERSPECTIVE_LABELS)) {
      expect(screen.getByText(label)).toBeInTheDocument();
    }
  });

  // ---------- Default state ----------

  it("shows GLOBAL as selected by default", () => {
    renderWithSettings(
      <PerspectiveSelector selected={["NEUTRAL"]} onChange={vi.fn()} />,
    );

    const neutralBtn = screen.getByRole("button", { name: /global/i });
    expect(neutralBtn).toHaveAttribute("aria-pressed", "true");
  });

  it("shows non-selected perspectives as unselected", () => {
    renderWithSettings(
      <PerspectiveSelector selected={["NEUTRAL"]} onChange={vi.fn()} />,
    );

    // Buttons have emoji+label text (e.g. "🇺🇸US"); use ends-with match
    const usBtn = screen.getByRole("button", { name: /us$/i });
    expect(usBtn).toHaveAttribute("aria-pressed", "false");
  });

  // ---------- Selection behavior ----------

  it("calls onChange with perspective added when clicking an unselected option", async () => {
    const user = userEvent.setup();
    const handleChange = vi.fn();

    renderWithSettings(
      <PerspectiveSelector selected={["NEUTRAL"]} onChange={handleChange} />,
    );

    // Click "US" which is currently not selected.
    // First non-global pick replaces default NEUTRAL.
    const usBtn = screen.getByRole("button", { name: /us$/i });
    await user.click(usBtn);

    expect(handleChange).toHaveBeenCalledTimes(1);
    expect(handleChange).toHaveBeenCalledWith(["US"]);
  });

  it("calls onChange with perspective removed when clicking a selected option", async () => {
    const user = userEvent.setup();
    const handleChange = vi.fn();

    renderWithSettings(
      <PerspectiveSelector
        selected={["NEUTRAL", "US"]}
        onChange={handleChange}
      />,
    );

    const usBtn = screen.getByRole("button", { name: /us$/i });
    await user.click(usBtn);

    expect(handleChange).toHaveBeenCalledTimes(1);
    expect(handleChange).toHaveBeenCalledWith(["NEUTRAL"]);
  });

  it("supports selecting multiple perspectives", async () => {
    const user = userEvent.setup();
    const handleChange = vi.fn();

    renderWithSettings(
      <PerspectiveSelector selected={["US", "EU"]} onChange={handleChange} />,
    );

    const norwayBtn = screen.getByRole("button", { name: /norway/i });
    await user.click(norwayBtn);

    expect(handleChange).toHaveBeenCalledWith(
      expect.arrayContaining(["US", "EU", "NORWAY"])
    );
  });

  it("allows selecting GLOBAL together with other perspectives", async () => {
    const user = userEvent.setup();
    const handleChange = vi.fn();

    renderWithSettings(
      <PerspectiveSelector selected={["US"]} onChange={handleChange} />,
    );

    const neutralBtn = screen.getByRole("button", { name: /global/i });
    await user.click(neutralBtn);

    expect(handleChange).toHaveBeenCalledWith(
      expect.arrayContaining(["US", "NEUTRAL"])
    );
  });

  // ---------- Visual feedback ----------

  it("visually distinguishes selected from unselected perspectives", () => {
    renderWithSettings(
      <PerspectiveSelector selected={["US"]} onChange={vi.fn()} />,
    );

    const usBtn = screen.getByRole("button", { name: /us$/i });
    const chinaBtn = screen.getByRole("button", { name: /china/i });

    expect(usBtn).toHaveAttribute("data-selected", "true");
    expect(chinaBtn).toHaveAttribute("data-selected", "false");
  });

  it("updates visual state when selected prop changes", () => {
    const { rerender } = renderWithSettings(
      <PerspectiveSelector selected={["NEUTRAL"]} onChange={vi.fn()} />,
    );

    const russiaBtn = screen.getByRole("button", { name: /russia/i });
    expect(russiaBtn).toHaveAttribute("aria-pressed", "false");

    rerender(
      <PerspectiveSelector selected={["NEUTRAL", "RUSSIA"]} onChange={vi.fn()} />,
    );

    expect(russiaBtn).toHaveAttribute("aria-pressed", "true");
  });
});

describe("PerspectiveSelector — accessibility (WCAG 2.1 AA)", () => {
  it("has no violations with default selection", async () => {
    const { container } = renderWithSettings(
      <PerspectiveSelector selected={["NEUTRAL"]} onChange={vi.fn()} />,
    );
    expect(await axe(container)).toHaveNoViolations();
  });
});
