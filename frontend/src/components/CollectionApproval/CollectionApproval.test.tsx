import { act, fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi, afterEach } from "vitest";
import userEvent from "@testing-library/user-event";
import CollectionApproval from "./CollectionApproval";

function markReviewedByScroll() {
  const panel = screen.getByTestId("collection-review-panel");

  Object.defineProperty(panel, "scrollHeight", {
    value: 1000,
    configurable: true,
  });
  Object.defineProperty(panel, "clientHeight", {
    value: 400,
    configurable: true,
  });
  Object.defineProperty(panel, "scrollTop", {
    value: 600,
    configurable: true,
  });

  fireEvent.scroll(panel);
}

afterEach(() => {
  vi.useRealTimers();
});

describe("CollectionApproval", () => {
  it("renders primary actions for collection review", () => {
    render(<CollectionApproval />);

    expect(
      screen.getByRole("button", { name: /approve & continue/i })
    ).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: /reject with feedback/i })
    ).toBeInTheDocument();
    expect(screen.queryByLabelText(/feedback/i)).not.toBeInTheDocument();
  });

  it("keeps both actions disabled until data is reviewed", () => {
    render(<CollectionApproval />);

    expect(
      screen.getByRole("button", { name: /approve & continue/i })
    ).toBeDisabled();
    expect(
      screen.getByRole("button", { name: /reject with feedback/i })
    ).toBeDisabled();
  });

  it("enables approve after user spends 10 seconds on the page", () => {
    vi.useFakeTimers();
    render(<CollectionApproval minReviewSeconds={10} />);

    const approveButton = screen.getByRole("button", {
      name: /approve & continue/i,
    });

    expect(approveButton).toBeDisabled();

    act(() => {
      vi.advanceTimersByTime(10000);
    });

    expect(approveButton).toBeEnabled();
  });

  it("enables approve when the review panel is scrolled to the bottom", () => {
    render(<CollectionApproval minReviewSeconds={60} />);

    const approveButton = screen.getByRole("button", {
      name: /approve & continue/i,
    });
    expect(approveButton).toBeDisabled();

    markReviewedByScroll();

    expect(approveButton).toBeEnabled();
  });

  it("shows a confirmation dialog when approve is clicked", async () => {
    const user = userEvent.setup();

    render(<CollectionApproval minReviewSeconds={60} />);
    markReviewedByScroll();

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

    render(
      <CollectionApproval
        minReviewSeconds={60}
        onApproveContinue={onApproveContinue}
      />
    );
    markReviewedByScroll();

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

    render(
      <CollectionApproval
        minReviewSeconds={60}
        onApproveContinue={onApproveContinue}
      />
    );
    markReviewedByScroll();

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

    render(
      <CollectionApproval
        minReviewSeconds={60}
        onRejectWithFeedback={onRejectWithFeedback}
      />
    );
    markReviewedByScroll();

    await user.click(screen.getByLabelText(/keep partial results/i));
    await user.click(
      screen.getByRole("button", { name: /reject with feedback/i })
    );

    expect(onRejectWithFeedback).toHaveBeenCalledTimes(1);
    expect(onRejectWithFeedback).toHaveBeenCalledWith({
      keepPartialResults: true,
    });
  });

  it("allows reject once review is complete", () => {
    render(<CollectionApproval minReviewSeconds={60} />);
    markReviewedByScroll();

    expect(
      screen.getByRole("button", { name: /reject with feedback/i })
    ).toBeEnabled();
  });
});
