import { render, screen, act } from "@testing-library/react";
import { describe, it, expect } from "vitest";
import userEvent from "@testing-library/user-event";
import { ToastProvider, useToast } from "../../contexts/Toast/ToastContext";
import ToastContainer from "./ToastContainer";

function ToastTrigger({ message = "Hello" }: { message?: string }) {
  const { addToast } = useToast();
  return (
    <button onClick={() => addToast(message, "info")}>Add toast</button>
  );
}

function renderContainer(position?: React.ComponentProps<typeof ToastContainer>["position"]) {
  return render(
    <ToastProvider>
      <ToastTrigger />
      <ToastContainer position={position} />
    </ToastProvider>,
  );
}

describe("ToastContainer", () => {
  it("renders nothing when there are no toasts", () => {
    const { container } = renderContainer();

    // No toast list rendered
    expect(screen.queryByRole("status")).not.toBeInTheDocument();
    // The container only has the trigger button, no toast wrapper
    expect(container.querySelectorAll('[class*="fixed"]').length).toBe(0);
  });

  it("renders a toast after addToast is called", async () => {
    const user = userEvent.setup();
    renderContainer();

    await user.click(screen.getByRole("button", { name: /add toast/i }));

    expect(screen.getByText("Hello")).toBeInTheDocument();
  });

  it("renders multiple toasts stacked", async () => {
    const user = userEvent.setup();
    render(
      <ToastProvider>
        <ToastTrigger message="First" />
        <ToastTrigger message="Second" />
        <ToastContainer />
      </ToastProvider>,
    );

    const [btn1, btn2] = screen.getAllByRole("button", { name: /add toast/i });
    await user.click(btn1);
    await user.click(btn2);

    expect(screen.getByText("First")).toBeInTheDocument();
    expect(screen.getByText("Second")).toBeInTheDocument();
  });

  it("removes a toast when its close button is clicked", async () => {
    const user = userEvent.setup();
    renderContainer();

    await user.click(screen.getByRole("button", { name: /add toast/i }));
    expect(screen.getByText("Hello")).toBeInTheDocument();

    const closeBtn = screen.getByRole("button", { name: /close/i });
    await user.click(closeBtn);

    expect(screen.queryByText("Hello")).not.toBeInTheDocument();
  });

  it("accepts an above-input position without throwing", async () => {
    const user = userEvent.setup();
    renderContainer("above-input");

    await user.click(screen.getByRole("button", { name: /add toast/i }));

    expect(screen.getByText("Hello")).toBeInTheDocument();
  });

  it("accepts a bottom-center position without throwing", async () => {
    const user = userEvent.setup();
    renderContainer("bottom-center");

    await user.click(screen.getByRole("button", { name: /add toast/i }));

    expect(screen.getByText("Hello")).toBeInTheDocument();
  });
});
