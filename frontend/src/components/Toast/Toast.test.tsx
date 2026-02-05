import { render, screen } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import userEvent from "@testing-library/user-event";
import Toast from "./Toast";

describe("Toast", () => {
  beforeEach(() => {
    vi.useFakeTimers();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it("renders the message", () => {
    const onClose = vi.fn();
    render(
      <Toast
        id="1"
        type="info"
        message="Test message"
        duration={5000}
        onClose={onClose}
      />
    );

    expect(screen.getByText("Test message")).toBeInTheDocument();
  });

  it("renders with success styling", () => {
    const onClose = vi.fn();
    render(
      <Toast
        id="1"
        type="success"
        message="Success message"
        duration={5000}
        onClose={onClose}
      />
    );

    const toast = screen.getByRole("alert");
    expect(toast).toHaveClass("bg-green-50");
    expect(toast).toHaveClass("border-green-500");
    expect(toast).toHaveClass("text-green-800");
  });

  it("renders with error styling", () => {
    const onClose = vi.fn();
    render(
      <Toast
        id="1"
        type="error"
        message="Error message"
        duration={5000}
        onClose={onClose}
      />
    );

    const toast = screen.getByRole("alert");
    expect(toast).toHaveClass("bg-red-50");
    expect(toast).toHaveClass("border-red-500");
    expect(toast).toHaveClass("text-red-800");
  });

  it("renders with warning styling", () => {
    const onClose = vi.fn();
    render(
      <Toast
        id="1"
        type="warning"
        message="Warning message"
        duration={5000}
        onClose={onClose}
      />
    );

    const toast = screen.getByRole("alert");
    expect(toast).toHaveClass("bg-yellow-50");
    expect(toast).toHaveClass("border-yellow-500");
    expect(toast).toHaveClass("text-yellow-800");
  });

  it("renders with info styling", () => {
    const onClose = vi.fn();
    render(
      <Toast
        id="1"
        type="info"
        message="Info message"
        duration={5000}
        onClose={onClose}
      />
    );

    const toast = screen.getByRole("alert");
    expect(toast).toHaveClass("bg-blue-50");
    expect(toast).toHaveClass("border-blue-500");
    expect(toast).toHaveClass("text-blue-800");
  });

  it("auto-dismisses after duration", () => {
    const onClose = vi.fn();
    render(
      <Toast
        id="1"
        type="info"
        message="Test message"
        duration={5000}
        onClose={onClose}
      />
    );

    expect(onClose).not.toHaveBeenCalled();

    vi.advanceTimersByTime(5000);

    expect(onClose).toHaveBeenCalledTimes(1);
    expect(onClose).toHaveBeenCalledWith("1");
  });

  it("calls onClose when close button is clicked", async () => {
    vi.useRealTimers();
    const user = userEvent.setup();
    const onClose = vi.fn();

    render(
      <Toast
        id="1"
        type="info"
        message="Test message"
        duration={5000}
        onClose={onClose}
      />
    );

    const closeButton = screen.getByRole("button", {
      name: /close notification/i,
    });
    await user.click(closeButton);

    expect(onClose).toHaveBeenCalledTimes(1);
    expect(onClose).toHaveBeenCalledWith("1");
  });

  it("has correct aria-live attribute for error type", () => {
    const onClose = vi.fn();
    render(
      <Toast
        id="1"
        type="error"
        message="Error message"
        duration={5000}
        onClose={onClose}
      />
    );

    const toast = screen.getByRole("alert");
    expect(toast).toHaveAttribute("aria-live", "assertive");
  });

  it("has correct aria-live attribute for non-error types", () => {
    const onClose = vi.fn();
    render(
      <Toast
        id="1"
        type="success"
        message="Success message"
        duration={5000}
        onClose={onClose}
      />
    );

    const toast = screen.getByRole("alert");
    expect(toast).toHaveAttribute("aria-live", "polite");
  });

  it("cleans up timer on unmount", () => {
    const onClose = vi.fn();
    const { unmount } = render(
      <Toast
        id="1"
        type="info"
        message="Test message"
        duration={5000}
        onClose={onClose}
      />
    );

    unmount();

    vi.advanceTimersByTime(5000);

    expect(onClose).not.toHaveBeenCalled();
  });
});
