import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { OptionsPanel } from "./OptionsPanel";

// Helper: renders OptionsPanel with sensible defaults so each test only
// specifies the props it actually cares about.
function renderOptionsPanel(
  props: Partial<React.ComponentProps<typeof OptionsPanel>> = {},
) {
  return render(
    <OptionsPanel
      selectedPerspectives={["NEUTRAL"]}
      onPerspectiveChange={vi.fn()}
      onOpenFileUpload={vi.fn()}
      {...props}
    />,
  );
}

describe("OptionsPanel", () => {
  it("renders the PerspectiveSelector", () => {
    renderOptionsPanel();

    // PerspectiveSelector renders buttons with full labels
    expect(screen.getByText("United States")).toBeInTheDocument();
    expect(screen.getByText("European Union")).toBeInTheDocument();
    expect(screen.getByText("Neutral")).toBeInTheDocument();
  });

  it("renders an 'Upload Files' button", () => {
    renderOptionsPanel();

    expect(
      screen.getByRole("button", { name: /upload files/i }),
    ).toBeInTheDocument();
  });

  it("calls onOpenFileUpload when the upload button is clicked", async () => {
    const onOpenFileUpload = vi.fn();
    const user = userEvent.setup();

    renderOptionsPanel({ onOpenFileUpload });

    await user.click(screen.getByRole("button", { name: /upload files/i }));

    expect(onOpenFileUpload).toHaveBeenCalledOnce();
  });

  it("passes perspectives and onChange to PerspectiveSelector", async () => {
    const onPerspectiveChange = vi.fn();
    const user = userEvent.setup();

    renderOptionsPanel({ selectedPerspectives: ["US"], onPerspectiveChange });

    // Click European Union to toggle it — PerspectiveSelector should call onChange
    await user.click(screen.getByText("European Union"));

    expect(onPerspectiveChange).toHaveBeenCalled();
  });

  // ---------- Collapsible Panel ----------
  // The panel has an internal toggle button. When collapsed the perspectives
  // and upload button are hidden; only the toggle itself remains visible.

  it("renders a toggle button for collapsing the options panel", () => {
    renderOptionsPanel();

    expect(
      screen.getByRole("button", { name: /toggle options/i }),
    ).toBeInTheDocument();
  });

  it("shows panel content by default (starts expanded)", () => {
    renderOptionsPanel();

    expect(screen.getByText("United States")).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: /upload files/i }),
    ).toBeInTheDocument();
  });

  it("hides panel content after clicking the toggle button", async () => {
    const user = userEvent.setup();

    renderOptionsPanel();

    await user.click(screen.getByRole("button", { name: /toggle options/i }));

    expect(screen.queryByText("United States")).not.toBeInTheDocument();
    expect(
      screen.queryByRole("button", { name: /upload files/i }),
    ).not.toBeInTheDocument();
  });

  it("shows panel content again after toggling twice", async () => {
    const user = userEvent.setup();

    renderOptionsPanel();

    const toggle = screen.getByRole("button", { name: /toggle options/i });
    await user.click(toggle);
    await user.click(toggle);

    expect(screen.getByText("United States")).toBeInTheDocument();
  });
});
