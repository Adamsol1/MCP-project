import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import userEvent from "@testing-library/user-event";
import ApprovalPrompt from "./ApprovalPrompt";

describe("ApprovalPrompt", () => {
  it("renders primary actions for approval prompt", () => {
    render(<ApprovalPrompt />);

    expect(
      screen.getByRole("button", { name: /approve & continue/i })
    ).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: /reject with feedback/i })
    ).toBeInTheDocument();
    expect(screen.queryByLabelText(/feedback/i)).not.toBeInTheDocument();
  });

  it("renders summary-specific copy when stage is summary_confirming", () => {
    render(<ApprovalPrompt stage="summary_confirming" />);

    expect(
      screen.getByRole("heading", { name: /summary approval prompt/i }),
    ).toBeInTheDocument();
  });

  it("renders pir-specific copy when stage is pir_confirming", () => {
    render(<ApprovalPrompt stage="pir_confirming" />);

    expect(
      screen.getByRole("heading", { name: /pir approval prompt/i }),
    ).toBeInTheDocument();
  });

  it("keeps both actions enabled by default", () => {
    render(<ApprovalPrompt />);

    expect(
      screen.getByRole("button", { name: /approve & continue/i })
    ).toBeEnabled();
    expect(
      screen.getByRole("button", { name: /reject with feedback/i })
    ).toBeEnabled();
  });

  it("disables both actions while loading", () => {
    render(<ApprovalPrompt isLoading />);

    expect(
      screen.getByRole("button", { name: /approve & continue/i })
    ).toBeDisabled();
    expect(
      screen.getByRole("button", { name: /reject with feedback/i })
    ).toBeDisabled();
  });

  it("shows a confirmation dialog when approve is clicked", async () => {
    const user = userEvent.setup();
    render(<ApprovalPrompt />);

    await user.click(
      screen.getByRole("button", { name: /approve & continue/i })
    );

    expect(
      screen.getByRole("dialog", { name: /confirm approval/i })
    ).toBeInTheDocument();
  });

  it("calls onApproveContinue only after confirmation", async () => {
    const user = userEvent.setup();
    const onApproveContinue = vi.fn();
    render(<ApprovalPrompt onApproveContinue={onApproveContinue} />);

    await user.click(
      screen.getByRole("button", { name: /approve & continue/i })
    );

    expect(onApproveContinue).not.toHaveBeenCalled();

    await user.click(screen.getByRole("button", { name: /confirm approve/i }));

    expect(onApproveContinue).toHaveBeenCalledTimes(1);
  });

  it("does not approve when the confirmation dialog is cancelled", async () => {
    const user = userEvent.setup();
    const onApproveContinue = vi.fn();
    render(<ApprovalPrompt onApproveContinue={onApproveContinue} />);

    await user.click(
      screen.getByRole("button", { name: /approve & continue/i })
    );
    await user.click(screen.getByRole("button", { name: /cancel/i }));

    expect(onApproveContinue).not.toHaveBeenCalled();
    expect(
      screen.queryByRole("dialog", { name: /confirm approval/i })
    ).not.toBeInTheDocument();
  });

  it("sends keep-partial flag when rejecting", async () => {
    const user = userEvent.setup();
    const onRejectWithFeedback = vi.fn();
    render(<ApprovalPrompt onRejectWithFeedback={onRejectWithFeedback} />);

    await user.click(screen.getByLabelText(/keep partial results/i));
    await user.click(
      screen.getByRole("button", { name: /reject with feedback/i })
    );

    expect(onRejectWithFeedback).toHaveBeenCalledTimes(1);
    expect(onRejectWithFeedback).toHaveBeenCalledWith({
      keepPartialResults: true,
    });
  });
});
