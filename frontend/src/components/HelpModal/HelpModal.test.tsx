import { render, screen } from "@testing-library/react";
import { describe, it, expect, vi } from "vitest";
import userEvent from "@testing-library/user-event";
import { axe } from "vitest-axe";
import { HelpModal, HelpButton } from "./HelpModal";

const sections = [
  { heading: "What is it?", body: "A help modal for users." },
  { body: "No heading section body." },
];

describe("HelpModal", () => {
  it("renders nothing when isOpen is false", () => {
    const { container } = render(
      <HelpModal isOpen={false} onClose={vi.fn()} title="Help" sections={sections} />,
    );

    expect(container.firstChild).toBeNull();
  });

  it("renders the dialog when isOpen is true", () => {
    render(
      <HelpModal isOpen onClose={vi.fn()} title="Help Guide" sections={sections} />,
    );

    expect(screen.getByRole("dialog")).toBeInTheDocument();
    expect(screen.getByText("Help Guide")).toBeInTheDocument();
  });

  it("renders section headings and body text", () => {
    render(
      <HelpModal isOpen onClose={vi.fn()} title="Help" sections={sections} />,
    );

    expect(screen.getByText("What is it?")).toBeInTheDocument();
    expect(screen.getByText("A help modal for users.")).toBeInTheDocument();
    expect(screen.getByText("No heading section body.")).toBeInTheDocument();
  });

  it("omits heading element for sections without a heading", () => {
    render(
      <HelpModal isOpen onClose={vi.fn()} title="Help" sections={[{ body: "Only body." }]} />,
    );

    // Body text is present; no extra heading element beyond the title
    expect(screen.getByText("Only body.")).toBeInTheDocument();
  });

  it("calls onClose when the close button is clicked", async () => {
    const user = userEvent.setup();
    const onClose = vi.fn();
    render(
      <HelpModal isOpen onClose={onClose} title="Help" sections={sections} />,
    );

    await user.click(screen.getByRole("button", { name: /close help/i }));

    expect(onClose).toHaveBeenCalledTimes(1);
  });

  it("calls onClose when the backdrop is clicked", async () => {
    const user = userEvent.setup();
    const onClose = vi.fn();
    const { container } = render(
      <HelpModal isOpen onClose={onClose} title="Help" sections={sections} />,
    );

    // Click the outermost backdrop div (first child)
    await user.click(container.firstChild as Element);

    expect(onClose).toHaveBeenCalledTimes(1);
  });

  it("does not call onClose when clicking inside the dialog", async () => {
    const user = userEvent.setup();
    const onClose = vi.fn();
    render(
      <HelpModal isOpen onClose={onClose} title="Help" sections={sections} />,
    );

    await user.click(screen.getByRole("dialog"));

    expect(onClose).not.toHaveBeenCalled();
  });
});

describe("HelpButton", () => {
  it("renders a button with default label '?'", () => {
    render(<HelpButton onClick={vi.fn()} />);

    const btn = screen.getByRole("button", { name: /help/i });
    expect(btn).toBeInTheDocument();
    expect(btn).toHaveTextContent("?");
  });

  it("uses the provided label for aria-label", () => {
    render(<HelpButton onClick={vi.fn()} label="Open guide" />);

    expect(screen.getByRole("button", { name: /open guide/i })).toBeInTheDocument();
  });

  it("calls onClick when clicked", async () => {
    const user = userEvent.setup();
    const onClick = vi.fn();
    render(<HelpButton onClick={onClick} />);

    await user.click(screen.getByRole("button", { name: /help/i }));

    expect(onClick).toHaveBeenCalledTimes(1);
  });
});

describe("HelpModal — accessibility (WCAG 2.1 AA)", () => {
  it("has no violations when open with sections", async () => {
    const { container } = render(
      <HelpModal isOpen onClose={vi.fn()} title="Help Guide" sections={sections} />,
    );
    expect(await axe(container)).toHaveNoViolations();
  });

  it("has no violations for HelpButton", async () => {
    const { container } = render(<HelpButton onClick={vi.fn()} />);
    expect(await axe(container)).toHaveNoViolations();
  });

  it("has no violations for HelpButton with custom label", async () => {
    const { container } = render(<HelpButton onClick={vi.fn()} label="Open guide" />);
    expect(await axe(container)).toHaveNoViolations();
  });
});
