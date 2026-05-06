import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { useContext, type ReactNode } from "react";
import { ToastProvider, ToastContext } from "./ToastContext";

function TestConsumer() {
  const ctx = useContext(ToastContext)!;
  return (
    <div>
      <span data-testid="toast-count">{ctx.toasts.length}</span>
      <button onClick={() => ctx.addToast("Hello")}>add default</button>
      <button onClick={() => ctx.success("Success!")}>success</button>
      <button onClick={() => ctx.error("Error!")}>error</button>
      <button onClick={() => ctx.warning("Warning!")}>warning</button>
      <button onClick={() => ctx.info("Info!")}>info</button>
      {ctx.toasts.map((t) => (
        <div key={t.id}>
          <span data-testid={`type-${t.id}`}>{t.type}</span>
          <span data-testid={`msg-${t.id}`}>{t.message}</span>
          <span data-testid={`dur-${t.id}`}>{t.duration}</span>
          <button onClick={() => ctx.removeToast(t.id)}>remove {t.id}</button>
        </div>
      ))}
    </div>
  );
}

function renderWithProvider(ui: ReactNode) {
  return render(<ToastProvider>{ui}</ToastProvider>);
}

describe("ToastProvider", () => {
  it("starts with an empty toast list", () => {
    renderWithProvider(<TestConsumer />);
    expect(screen.getByTestId("toast-count")).toHaveTextContent("0");
  });

  it("addToast with no options defaults to type 'info' and 5000ms duration", async () => {
    const user = userEvent.setup();
    renderWithProvider(<TestConsumer />);

    await user.click(screen.getByRole("button", { name: "add default" }));

    expect(screen.getByTestId("toast-count")).toHaveTextContent("1");
    const ids = screen
      .getAllByText(/remove /)
      .map((el) => el.textContent!.replace("remove ", ""));
    expect(screen.getByTestId(`type-${ids[0]}`)).toHaveTextContent("info");
    expect(screen.getByTestId(`msg-${ids[0]}`)).toHaveTextContent("Hello");
    expect(screen.getByTestId(`dur-${ids[0]}`)).toHaveTextContent("5000");
  });

  it("removeToast removes the correct toast", async () => {
    const user = userEvent.setup();
    renderWithProvider(<TestConsumer />);

    await user.click(screen.getByRole("button", { name: "add default" }));
    await user.click(screen.getByRole("button", { name: "success" }));
    expect(screen.getByTestId("toast-count")).toHaveTextContent("2");

    // Remove the first toast
    const removeButtons = screen.getAllByRole("button", { name: /^remove / });
    await user.click(removeButtons[0]);
    expect(screen.getByTestId("toast-count")).toHaveTextContent("1");
  });

  it("success() creates a toast with type 'success'", async () => {
    const user = userEvent.setup();
    renderWithProvider(<TestConsumer />);

    await user.click(screen.getByRole("button", { name: "success" }));

    const id = screen
      .getByText(/remove /)
      .textContent!.replace("remove ", "");
    expect(screen.getByTestId(`type-${id}`)).toHaveTextContent("success");
    expect(screen.getByTestId(`msg-${id}`)).toHaveTextContent("Success!");
  });

  it("error() creates a toast with type 'error'", async () => {
    const user = userEvent.setup();
    renderWithProvider(<TestConsumer />);

    await user.click(screen.getByRole("button", { name: "error" }));

    const id = screen
      .getByText(/remove /)
      .textContent!.replace("remove ", "");
    expect(screen.getByTestId(`type-${id}`)).toHaveTextContent("error");
    expect(screen.getByTestId(`msg-${id}`)).toHaveTextContent("Error!");
  });

  it("warning() creates a toast with type 'warning'", async () => {
    const user = userEvent.setup();
    renderWithProvider(<TestConsumer />);

    await user.click(screen.getByRole("button", { name: "warning" }));

    const id = screen
      .getByText(/remove /)
      .textContent!.replace("remove ", "");
    expect(screen.getByTestId(`type-${id}`)).toHaveTextContent("warning");
  });

  it("info() creates a toast with type 'info'", async () => {
    const user = userEvent.setup();
    renderWithProvider(<TestConsumer />);

    await user.click(screen.getByRole("button", { name: "info" }));

    const id = screen
      .getByText(/remove /)
      .textContent!.replace("remove ", "");
    expect(screen.getByTestId(`type-${id}`)).toHaveTextContent("info");
  });

  it("multiple toasts are accumulated in order", async () => {
    const user = userEvent.setup();
    renderWithProvider(<TestConsumer />);

    await user.click(screen.getByRole("button", { name: "success" }));
    await user.click(screen.getByRole("button", { name: "error" }));
    await user.click(screen.getByRole("button", { name: "warning" }));

    expect(screen.getByTestId("toast-count")).toHaveTextContent("3");
    const types = screen.getAllByTestId(/^type-/).map((el) => el.textContent);
    expect(types).toEqual(["success", "error", "warning"]);
  });

  it("removing one toast does not affect others", async () => {
    const user = userEvent.setup();
    renderWithProvider(<TestConsumer />);

    await user.click(screen.getByRole("button", { name: "success" }));
    await user.click(screen.getByRole("button", { name: "error" }));

    const removeButtons = screen.getAllByRole("button", { name: /^remove / });
    await user.click(removeButtons[0]);

    expect(screen.getByTestId("toast-count")).toHaveTextContent("1");
    const remainingType = screen.getAllByTestId(/^type-/)[0];
    expect(remainingType).toHaveTextContent("error");
  });

  it("renders children correctly", () => {
    render(
      <ToastProvider>
        <p data-testid="child">Hello world</p>
      </ToastProvider>,
    );
    expect(screen.getByTestId("child")).toHaveTextContent("Hello world");
  });
});
