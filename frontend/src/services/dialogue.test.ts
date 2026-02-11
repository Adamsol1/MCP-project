import { describe, it, expect, vi } from "vitest";
import { sendMessage } from "./dialogue";
import axios from "axios";

// We mock axios so our tests don't make real HTTP requests.
// vi.mock() replaces the entire axios module with mock functions.
// This means axios.post() becomes a spy we can control and inspect.
vi.mock("axios");

describe("dialogue service", () => {
  it("sends a message to the dialogue API and returns the response", async () => {
    // Define what the fake API should return
    const mockResponse = {
      data: {
        question: "What is the scope of your investigation?",
        type: "scope",
        is_final: false,
      },
    };

    // Tell the mocked axios.post to resolve with our fake response
    // vi.mocked() gives us TypeScript-aware access to the mock
    vi.mocked(axios.post).mockResolvedValue(mockResponse);

    const result = await sendMessage("Investigate APT29", "session-123", [
      "US",
      "EU",
    ]);

    // Verify axios was called with the correct URL and payload including perspectives
    expect(axios.post).toHaveBeenCalledWith(
      "http://localhost:8000/api/dialogue/message",
      {
        message: "Investigate APT29",
        session_id: "session-123",
        perspectives: ["US", "EU"],
      }
    );

    // Verify the service returns the response data
    expect(result).toEqual({
      question: "What is the scope of your investigation?",
      type: "scope",
      is_final: false,
    });
  });

  it("throws when the API call fails", async () => {
    // Simulate a network error
    vi.mocked(axios.post).mockRejectedValue(new Error("Network error"));

    // expect().rejects lets us test that an async function throws
    await expect(sendMessage("Hello", "session-123")).rejects.toThrow(
      "Network error"
    );
  });
});
