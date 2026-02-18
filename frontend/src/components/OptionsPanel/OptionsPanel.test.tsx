import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { OptionsPanel } from "./OptionsPanel";

describe("OptionsPanel", () => {
  it("renders the PerspectiveSelector", () => {
    render(
      <OptionsPanel
        selectedPerspectives={["NEUTRAL"]}
        onPerspectiveChange={vi.fn()}
        onOpenFileUpload={vi.fn()}
      />,
    );

    // PerspectiveSelector renders buttons with full labels
    expect(screen.getByText("United States")).toBeInTheDocument();
    expect(screen.getByText("European Union")).toBeInTheDocument();
    expect(screen.getByText("Neutral")).toBeInTheDocument();
  });

  it("renders an 'Upload Files' button", () => {
    render(
      <OptionsPanel
        selectedPerspectives={["NEUTRAL"]}
        onPerspectiveChange={vi.fn()}
        onOpenFileUpload={vi.fn()}
      />,
    );

    expect(
      screen.getByRole("button", { name: /upload files/i }),
    ).toBeInTheDocument();
  });

  it("calls onOpenFileUpload when the upload button is clicked", async () => {
    const onOpenFileUpload = vi.fn();
    const user = userEvent.setup();

    render(
      <OptionsPanel
        selectedPerspectives={["NEUTRAL"]}
        onPerspectiveChange={vi.fn()}
        onOpenFileUpload={onOpenFileUpload}
      />,
    );

    await user.click(screen.getByRole("button", { name: /upload files/i }));

    expect(onOpenFileUpload).toHaveBeenCalledOnce();
  });

  it("passes perspectives and onChange to PerspectiveSelector", async () => {
    const onPerspectiveChange = vi.fn();
    const user = userEvent.setup();

    render(
      <OptionsPanel
        selectedPerspectives={["US"]}
        onPerspectiveChange={onPerspectiveChange}
        onOpenFileUpload={vi.fn()}
      />,
    );

    // Click European Union to toggle it — PerspectiveSelector should call onChange
    await user.click(screen.getByText("European Union"));

    expect(onPerspectiveChange).toHaveBeenCalled();
  });
});
