/**
 * PerspectiveSelector — toggle buttons for geopolitical analysis perspectives.
 *
 * PerspectiveSelector is a controlled component that calls onChange whenever
 * the user toggles a perspective. NEUTRAL is selected by default.
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

// Labels as rendered by the component (from en.ts perspectiveLabels).
// These are the abbreviated labels shown in the grid buttons.
const PERSPECTIVE_LABELS: Record<string, string> = {
  US: "US",
  NORWAY: "Norway",
  CHINA: "China",
  EU: "EU",
  RUSSIA: "Russia",
  NEUTRAL: "Neutral",
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

  it("renders a heading or label for the section", () => {
    renderWithSettings(
      <PerspectiveSelector selected={["NEUTRAL"]} onChange={vi.fn()} />,
    );

    expect(screen.getByText(/perspective/i)).toBeInTheDocument();
  });

  // ---------- Default state ----------

  it("shows NEUTRAL as selected by default", () => {
    renderWithSettings(
      <PerspectiveSelector selected={["NEUTRAL"]} onChange={vi.fn()} />,
    );

    const neutralBtn = screen.getByRole("button", { name: /neutral/i });
    expect(neutralBtn).toHaveAttribute("aria-pressed", "true");
  });

  it("shows non-selected perspectives as unselected", () => {
    renderWithSettings(
      <PerspectiveSelector selected={["NEUTRAL"]} onChange={vi.fn()} />,
    );

    // "US" button should not be selected when only NEUTRAL is selected
    const usBtn = screen.getByRole("button", { name: /^us$/i });
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
    // First non-neutral pick replaces default NEUTRAL.
    const usBtn = screen.getByRole("button", { name: /^us$/i });
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

    const usBtn = screen.getByRole("button", { name: /^us$/i });
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

  it("allows selecting NEUTRAL together with other perspectives", async () => {
    const user = userEvent.setup();
    const handleChange = vi.fn();

    renderWithSettings(
      <PerspectiveSelector selected={["US"]} onChange={handleChange} />,
    );

    const neutralBtn = screen.getByRole("button", { name: /neutral/i });
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

    const usBtn = screen.getByRole("button", { name: /^us$/i });
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
