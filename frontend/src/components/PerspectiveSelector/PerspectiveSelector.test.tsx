import { render, screen } from "@testing-library/react";
import { describe, it, expect, vi } from "vitest";
import userEvent from "@testing-library/user-event";
import PerspectiveSelector from "./PerspectiveSelector";

/**
 * S2.3.1: Design perspective selection UI (checkboxes/buttons)
 *
 * PerspectiveSelector is a standalone component that sits next to ChatWindow.
 * It lets the user pick one or more geopolitical perspectives before starting
 * the dialogue. NEUTRAL is selected by default.
 *
 * Props:
 *   selected: string[]           — currently selected perspective IDs
 *   onChange: (perspectives: string[]) => void  — called when selection changes
 */

// The 6 perspectives we expect to be rendered
const ALL_PERSPECTIVES = ["US", "NORWAY", "CHINA", "EU", "RUSSIA", "NEUTRAL"];

// Human-readable labels we expect to see in the UI
const PERSPECTIVE_LABELS: Record<string, string> = {
  US: "United States",
  NORWAY: "Norway",
  CHINA: "China",
  EU: "European Union",
  RUSSIA: "Russia",
  NEUTRAL: "Neutral",
};

describe("PerspectiveSelector", () => {
  // ---------- Rendering ----------

  it("renders all six perspective options", () => {
    // The component should show a button/checkbox for every perspective
    render(<PerspectiveSelector selected={["NEUTRAL"]} onChange={vi.fn()} />);

    for (const label of Object.values(PERSPECTIVE_LABELS)) {
      expect(screen.getByText(label)).toBeInTheDocument();
    }
  });

  it("renders a heading or label for the section", () => {
    // Users need to know what this component is for
    render(<PerspectiveSelector selected={["NEUTRAL"]} onChange={vi.fn()} />);

    expect(screen.getByText(/perspectives/i)).toBeInTheDocument();
  });

  // ---------- Default state ----------

  it("shows NEUTRAL as selected by default", () => {
    // When selected=["NEUTRAL"], only Neutral should appear selected
    render(<PerspectiveSelector selected={["NEUTRAL"]} onChange={vi.fn()} />);

    const neutralBtn = screen.getByRole("button", { name: /neutral/i });
    // aria-pressed="true" indicates the button is toggled on
    expect(neutralBtn).toHaveAttribute("aria-pressed", "true");
  });

  it("shows non-selected perspectives as unselected", () => {
    render(<PerspectiveSelector selected={["NEUTRAL"]} onChange={vi.fn()} />);

    const usBtn = screen.getByRole("button", { name: /united states/i });
    expect(usBtn).toHaveAttribute("aria-pressed", "false");
  });

  // ---------- Selection behavior ----------

  it("calls onChange with perspective added when clicking an unselected option", async () => {
    const user = userEvent.setup();
    const handleChange = vi.fn();

    render(
      <PerspectiveSelector selected={["NEUTRAL"]} onChange={handleChange} />
    );

    // Click "United States" which is currently not selected
    const usBtn = screen.getByRole("button", { name: /united states/i });
    await user.click(usBtn);

    // Should be called with NEUTRAL (existing) + US (newly added)
    expect(handleChange).toHaveBeenCalledTimes(1);
    expect(handleChange).toHaveBeenCalledWith(
      expect.arrayContaining(["NEUTRAL", "US"])
    );
  });

  it("calls onChange with perspective removed when clicking a selected option", async () => {
    const user = userEvent.setup();
    const handleChange = vi.fn();

    render(
      <PerspectiveSelector
        selected={["NEUTRAL", "US"]}
        onChange={handleChange}
      />
    );

    // Click "United States" which IS currently selected — should deselect it
    const usBtn = screen.getByRole("button", { name: /united states/i });
    await user.click(usBtn);

    expect(handleChange).toHaveBeenCalledTimes(1);
    expect(handleChange).toHaveBeenCalledWith(["NEUTRAL"]);
  });

  it("supports selecting multiple perspectives", async () => {
    const user = userEvent.setup();
    const handleChange = vi.fn();

    // Start with US and EU already selected
    render(
      <PerspectiveSelector selected={["US", "EU"]} onChange={handleChange} />
    );

    // Add Norway
    const norwayBtn = screen.getByRole("button", { name: /norway/i });
    await user.click(norwayBtn);

    expect(handleChange).toHaveBeenCalledWith(
      expect.arrayContaining(["US", "EU", "NORWAY"])
    );
  });

  // ---------- Visual feedback ----------

  it("visually distinguishes selected from unselected perspectives", () => {
    // With US selected and CHINA not selected, they should have
    // different data-selected attributes for styling
    render(
      <PerspectiveSelector selected={["US"]} onChange={vi.fn()} />
    );

    const usBtn = screen.getByRole("button", { name: /united states/i });
    const chinaBtn = screen.getByRole("button", { name: /china/i });

    expect(usBtn).toHaveAttribute("data-selected", "true");
    expect(chinaBtn).toHaveAttribute("data-selected", "false");
  });

  it("updates visual state when selected prop changes", () => {
    // First render: only NEUTRAL selected
    const { rerender } = render(
      <PerspectiveSelector selected={["NEUTRAL"]} onChange={vi.fn()} />
    );

    const russiaBtn = screen.getByRole("button", { name: /russia/i });
    expect(russiaBtn).toHaveAttribute("aria-pressed", "false");

    // Re-render with RUSSIA now selected
    rerender(
      <PerspectiveSelector selected={["NEUTRAL", "RUSSIA"]} onChange={vi.fn()} />
    );

    expect(russiaBtn).toHaveAttribute("aria-pressed", "true");
  });
});
