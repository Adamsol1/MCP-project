import { beforeEach, describe, expect, it, vi } from "vitest";
import axios from "axios";
import { sendDevLlmChat } from "./devLlmChat";

vi.mock("axios");

const BASE = "http://127.0.0.1:8000";
const TIMEOUT = { timeout: 600000 };

beforeEach(() => {
  vi.clearAllMocks();
});

describe("sendDevLlmChat", () => {
  it("posts messages to the dev LLM endpoint", async () => {
    vi.mocked(axios.post).mockResolvedValue({
      data: { message: "pong", provider: "local", model: "test-model" },
    });

    const result = await sendDevLlmChat(
      [{ role: "user", content: "ping" }],
      "local",
      "test-model",
    );

    expect(axios.post).toHaveBeenCalledWith(
      `${BASE}/api/dev/llm-chat`,
      {
        messages: [{ role: "user", content: "ping" }],
        ai_provider: "local",
        model: "test-model",
      },
      TIMEOUT,
    );
    expect(result).toEqual({
      message: "pong",
      provider: "local",
      model: "test-model",
    });
  });

  it("sends null for a blank model override", async () => {
    vi.mocked(axios.post).mockResolvedValue({
      data: { message: "pong", provider: "gemini", model: "default" },
    });

    await sendDevLlmChat([{ role: "user", content: "ping" }], "gemini", " ");

    const [, body] = vi.mocked(axios.post).mock.calls[0];
    expect((body as Record<string, unknown>).model).toBeNull();
  });
});
