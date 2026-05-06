import { render, screen } from "@testing-library/react";
import { describe, it, expect, vi } from "vitest";
import userEvent from "@testing-library/user-event";
import CollectionActivityModal from "./CollectionActivityModal";
import type { PhaseReviewItem } from "../../types/conversation";

const approvedItem: PhaseReviewItem = {
  attempt: 1,
  phase: "collection",
  reviewer_approved: true,
  reviewer_suggestions: null,
  sources_used: ["AlienVault OTX", "Web Search"],
  generated_content: null,
};

const rejectedItem: PhaseReviewItem = {
  attempt: 2,
  phase: "collection",
  reviewer_approved: false,
  reviewer_suggestions: "Improve source diversity.\n\n1. Add Knowledge Bank.",
  sources_used: ["Web Search"],
  generated_content: null,
};

describe("CollectionActivityModal", () => {
  it("renders nothing when isOpen is false", () => {
    const { container } = render(
      <CollectionActivityModal isOpen={false} onClose={vi.fn()} activity={[]} />,
    );

    expect(container.firstChild).toBeNull();
  });

  it("renders the modal when isOpen is true", () => {
    render(
      <CollectionActivityModal isOpen onClose={vi.fn()} activity={[approvedItem]} />,
    );

    expect(screen.getByRole("dialog")).toBeInTheDocument();
    expect(screen.getByText("Review Activity")).toBeInTheDocument();
  });

  it("shows empty state message when activity is empty", () => {
    render(
      <CollectionActivityModal isOpen onClose={vi.fn()} activity={[]} />,
    );

    expect(screen.getByText(/no activity recorded/i)).toBeInTheDocument();
  });

  it("shows attempt count in the subtitle", () => {
    render(
      <CollectionActivityModal
        isOpen
        onClose={vi.fn()}
        activity={[approvedItem, rejectedItem]}
      />,
    );

    expect(screen.getByText(/2 attempts/i)).toBeInTheDocument();
  });

  it("renders attempt number and approved badge", () => {
    render(
      <CollectionActivityModal isOpen onClose={vi.fn()} activity={[approvedItem]} />,
    );

    expect(screen.getByText(/attempt 1/i)).toBeInTheDocument();
    expect(screen.getByText("Approved")).toBeInTheDocument();
  });

  it("renders rejected badge for a rejected attempt", () => {
    render(
      <CollectionActivityModal isOpen onClose={vi.fn()} activity={[rejectedItem]} />,
    );

    expect(screen.getByText(/rejected/i)).toBeInTheDocument();
  });

  it("renders sources used in an attempt", () => {
    render(
      <CollectionActivityModal isOpen onClose={vi.fn()} activity={[approvedItem]} />,
    );

    expect(screen.getByText("AlienVault OTX")).toBeInTheDocument();
    expect(screen.getByText("Web Search")).toBeInTheDocument();
  });

  it("renders reviewer suggestions for a rejected attempt", () => {
    render(
      <CollectionActivityModal isOpen onClose={vi.fn()} activity={[rejectedItem]} />,
    );

    expect(screen.getByText(/improve source diversity/i)).toBeInTheDocument();
  });

  it("renders formatted numbered list in reviewer suggestions", () => {
    render(
      <CollectionActivityModal isOpen onClose={vi.fn()} activity={[rejectedItem]} />,
    );

    expect(screen.getByText(/add knowledge bank/i)).toBeInTheDocument();
  });

  it("calls onClose when the close button is clicked", async () => {
    const user = userEvent.setup();
    const onClose = vi.fn();
    render(
      <CollectionActivityModal isOpen onClose={onClose} activity={[approvedItem]} />,
    );

    await user.click(screen.getByRole("button", { name: /close/i }));

    expect(onClose).toHaveBeenCalledTimes(1);
  });

  it("calls onClose when the backdrop is clicked", async () => {
    const user = userEvent.setup();
    const onClose = vi.fn();
    render(
      <CollectionActivityModal isOpen onClose={onClose} activity={[approvedItem]} />,
    );

    await user.click(screen.getByTestId("activity-modal-backdrop"));

    expect(onClose).toHaveBeenCalledTimes(1);
  });
});
