import { render, screen } from "@testing-library/react";
import { describe, it, expect, vi } from "vitest";
import userEvent from "@testing-library/user-event";
import ElicitationModal from "./ElicitationModal";
import type { PendingElicitation } from "../../services/dialogue/dialogue";

const elicitation: PendingElicitation = {
  message: "Classified content was detected in the collected data.",
  options: ["Proceed without classified content", "Bytt til lokal LLM"],
};

const plainElicitation: PendingElicitation = {
  message: "Choose how to handle sensitive data.",
  options: ["Accept", "Decline"],
};

describe("ElicitationModal", () => {
  it("renders the elicitation message", () => {
    render(<ElicitationModal elicitation={elicitation} onRespond={vi.fn()} />);

    expect(
      screen.getByText("Classified content was detected in the collected data."),
    ).toBeInTheDocument();
  });

  it("renders all option buttons", () => {
    render(<ElicitationModal elicitation={elicitation} onRespond={vi.fn()} />);

    expect(
      screen.getByRole("button", { name: /proceed without classified content/i }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: /bytt til lokal llm/i }),
    ).toBeInTheDocument();
  });

  it("calls onRespond with the selected option when a regular option is clicked", async () => {
    const user = userEvent.setup();
    const onRespond = vi.fn();
    render(<ElicitationModal elicitation={elicitation} onRespond={onRespond} />);

    await user.click(
      screen.getByRole("button", { name: /proceed without classified content/i }),
    );

    expect(onRespond).toHaveBeenCalledTimes(1);
    expect(onRespond).toHaveBeenCalledWith("Proceed without classified content");
  });

  it("disables the local LLM option and does not call onRespond when clicked", async () => {
    const user = userEvent.setup();
    const onRespond = vi.fn();
    render(<ElicitationModal elicitation={elicitation} onRespond={onRespond} />);

    const localLlmBtn = screen.getByRole("button", { name: /bytt til lokal llm/i });
    expect(localLlmBtn).toBeDisabled();

    await user.click(localLlmBtn);

    expect(onRespond).not.toHaveBeenCalled();
  });

  it("enables all buttons when none is the local LLM option", async () => {
    const user = userEvent.setup();
    const onRespond = vi.fn();
    render(
      <ElicitationModal elicitation={plainElicitation} onRespond={onRespond} />,
    );

    const acceptBtn = screen.getByRole("button", { name: /accept/i });
    const declineBtn = screen.getByRole("button", { name: /decline/i });

    expect(acceptBtn).toBeEnabled();
    expect(declineBtn).toBeEnabled();

    await user.click(acceptBtn);
    expect(onRespond).toHaveBeenCalledWith("Accept");
  });

  it("calls onRespond with the correct value for each option", async () => {
    const user = userEvent.setup();
    const onRespond = vi.fn();
    render(
      <ElicitationModal elicitation={plainElicitation} onRespond={onRespond} />,
    );

    await user.click(screen.getByRole("button", { name: /decline/i }));

    expect(onRespond).toHaveBeenCalledWith("Decline");
  });
});
