import { describe, expect, it, vi } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { DevLlmChatModal } from "./DevLlmChatModal";
import * as devLlmChat from "../../services/devLlmChat/devLlmChat";

describe("DevLlmChatModal", () => {
  it("sends a chat message and renders the response", async () => {
    const user = userEvent.setup();
    vi.spyOn(devLlmChat, "sendDevLlmChat").mockResolvedValue({
      message: "pong",
      provider: "local",
      model: "test-model",
    });

    render(
      <DevLlmChatModal isOpen={true} onClose={vi.fn()} aiProvider="local" />,
    );

    await user.type(screen.getByPlaceholderText(/message the llm/i), "ping");
    await user.click(screen.getByRole("button", { name: /send/i }));

    await waitFor(() => {
      expect(screen.getByText("pong")).toBeInTheDocument();
    });
    expect(devLlmChat.sendDevLlmChat).toHaveBeenCalledWith(
      expect.arrayContaining([
        { role: "user", content: "ping" },
      ]),
      "local",
      "",
    );
  });

  it("returns null when closed", () => {
    const { container } = render(
      <DevLlmChatModal isOpen={false} onClose={vi.fn()} aiProvider="gemini" />,
    );

    expect(container).toBeEmptyDOMElement();
  });
});
