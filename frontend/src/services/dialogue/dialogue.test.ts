/**
 * dialogue service tests.
 *
 * All axios calls are mocked so no real HTTP requests are made.
 * Each function in the service is covered including:
 *  - sendMessage: default args, all optional params, options object
 *  - getCollectionStatus: happy path and silent-null on error
 *  - getDevDialogueState: happy path
 *  - setDevDialogueState: sub_state normalization rules
 *  - resetDevDialogueState: happy path
 *
 * Run with: cd frontend && npx vitest dialogue.test
 */

import { describe, it, expect, vi, beforeEach } from "vitest";
import axios from "axios";
import {
  sendMessage,
  getCollectionStatus,
  getDevDialogueState,
  setDevDialogueState,
  resetDevDialogueState,
} from "./dialogue";
import type {
  DialogueApiResponse,
  CollectionStatus,
  DialogueDevStateResponse,
} from "./dialogue";

vi.mock("axios");

const BASE = "http://127.0.0.1:8004";
const DIALOGUE_TIMEOUT = { timeout: 600000 };
const DEV_TIMEOUT = { timeout: 30000 };
const COLLECTION_STATUS_TIMEOUT = { timeout: 10000 };

// Reset call history between tests so assertions don't bleed across tests.
beforeEach(() => {
  vi.clearAllMocks();
});

// ── sendMessage ───────────────────────────────────────────────────────────────

describe("sendMessage", () => {
  const mockResponse: { data: DialogueApiResponse } = {
    data: {
      question: "What is the scope of your investigation?",
      action: "ask_question",
    },
  };

  it("sends the message and returns the response data", async () => {
    vi.mocked(axios.post).mockResolvedValue(mockResponse);

    const result = await sendMessage("Investigate APT29", "session-123", [
      "US",
      "EU",
    ]);

    expect(axios.post).toHaveBeenCalledWith(
      `${BASE}/api/dialogue/message`,
      {
        message: "Investigate APT29",
        session_id: "session-123",
        perspectives: ["US", "EU"],
        approved: undefined,
        language: "en",
        settings_timeframe: "",
        ai_provider: "local",
        selected_sources: [],
        gather_more: false,
        council_debate_point: "",
        council_finding_ids: [],
        council_perspectives: [],
        council_settings: null,
      },
      DIALOGUE_TIMEOUT,
    );
    expect(result).toEqual(mockResponse.data);
  });

  it("defaults perspectives to ['NEUTRAL'] when omitted", async () => {
    vi.mocked(axios.post).mockResolvedValue(mockResponse);

    await sendMessage("Hello", "session-1");

    const [, body] = vi.mocked(axios.post).mock.calls[0];
    expect((body as Record<string, unknown>).perspectives).toEqual(["NEUTRAL"]);
  });

  it("sends approved=true when the user approves a pending summary", async () => {
    vi.mocked(axios.post).mockResolvedValue(mockResponse);

    await sendMessage("yes", "session-1", ["NEUTRAL"], true);

    const [, body] = vi.mocked(axios.post).mock.calls[0];
    expect((body as Record<string, unknown>).approved).toBe(true);
  });

  it("sends a custom language when provided", async () => {
    vi.mocked(axios.post).mockResolvedValue(mockResponse);

    await sendMessage("Hei", "session-1", ["NEUTRAL"], undefined, "no");

    const [, body] = vi.mocked(axios.post).mock.calls[0];
    expect((body as Record<string, unknown>).language).toBe("no");
  });

  it("sends a non-empty settingsTimeframe when provided", async () => {
    vi.mocked(axios.post).mockResolvedValue(mockResponse);

    await sendMessage(
      "Hello",
      "session-1",
      ["NEUTRAL"],
      undefined,
      "en",
      "Last 30 days",
    );

    const [, body] = vi.mocked(axios.post).mock.calls[0];
    expect((body as Record<string, unknown>).settings_timeframe).toBe(
      "Last 30 days",
    );
  });

  it("forwards selectedSources from options", async () => {
    vi.mocked(axios.post).mockResolvedValue(mockResponse);

    await sendMessage("Hello", "session-1", ["NEUTRAL"], undefined, "en", "", {
      selectedSources: ["source-a", "source-b"],
    });

    const [, body] = vi.mocked(axios.post).mock.calls[0];
    expect((body as Record<string, unknown>).selected_sources).toEqual([
      "source-a",
      "source-b",
    ]);
  });

  it("forwards gatherMore=true from options", async () => {
    vi.mocked(axios.post).mockResolvedValue(mockResponse);

    await sendMessage("Hello", "session-1", ["NEUTRAL"], undefined, "en", "", {
      gatherMore: true,
    });

    const [, body] = vi.mocked(axios.post).mock.calls[0];
    expect((body as Record<string, unknown>).gather_more).toBe(true);
  });

  it("throws when the API call fails", async () => {
    vi.mocked(axios.post).mockRejectedValue(new Error("Network error"));

    await expect(sendMessage("Hello", "session-123")).rejects.toThrow(
      "Network error",
    );
  });
});

// ── getCollectionStatus ───────────────────────────────────────────────────────

describe("getCollectionStatus", () => {
  const mockStatus: CollectionStatus = {
    session_id: "session-1",
    status: "collecting",
    current_source: "web",
    current_activity: "Fetching pages",
    sources: {
      web: { call_count: 2, last_called_at: "2026-03-01T10:00:00Z" },
    },
  };

  it("returns the collection status from the API", async () => {
    vi.mocked(axios.get).mockResolvedValue({ data: mockStatus });

    const result = await getCollectionStatus("session-1");

    expect(axios.get).toHaveBeenCalledWith(
      `${BASE}/api/dialogue/collection-status/session-1`,
      COLLECTION_STATUS_TIMEOUT,
    );
    expect(result).toEqual(mockStatus);
  });

  it("returns null when the API call fails (best-effort)", async () => {
    vi.mocked(axios.get).mockRejectedValue(new Error("Not found"));

    const result = await getCollectionStatus("session-1");

    expect(result).toBeNull();
  });

  it("returns null when the session has no active collection", async () => {
    vi.mocked(axios.get).mockRejectedValue({ response: { status: 404 } });

    const result = await getCollectionStatus("unknown-session");

    expect(result).toBeNull();
  });
});

// ── getDevDialogueState ───────────────────────────────────────────────────────

describe("getDevDialogueState", () => {
  const mockDevState: DialogueDevStateResponse = {
    session_id: "session-1",
    stage: "gathering",
    phase: "direction",
    sub_state: null,
    question_count: 3,
    max_questions: 10,
    missing_context_fields: ["timeframe"],
    has_sufficient_context: false,
    awaiting_user_decision: false,
    has_modifications: false,
  };

  it("fetches the dev state with session_id as a query param", async () => {
    vi.mocked(axios.get).mockResolvedValue({ data: mockDevState });

    const result = await getDevDialogueState("session-1");

    expect(axios.get).toHaveBeenCalledWith(
      `${BASE}/api/dialogue/dev/state`,
      { params: { session_id: "session-1" }, ...DEV_TIMEOUT },
    );
    expect(result).toEqual(mockDevState);
  });

  it("throws when the API call fails", async () => {
    vi.mocked(axios.get).mockRejectedValue(new Error("Unauthorized"));

    await expect(getDevDialogueState("session-1")).rejects.toThrow(
      "Unauthorized",
    );
  });
});

// ── setDevDialogueState ───────────────────────────────────────────────────────

describe("setDevDialogueState", () => {
  const mockDevState: DialogueDevStateResponse = {
    session_id: "session-1",
    stage: "summary_confirming",
    phase: "direction",
    sub_state: "awaiting_decision",
    question_count: 5,
    max_questions: 10,
    missing_context_fields: [],
    has_sufficient_context: true,
    awaiting_user_decision: true,
    has_modifications: false,
  };

  it("sends stage and sub_state for summary_confirming", async () => {
    vi.mocked(axios.post).mockResolvedValue({ data: mockDevState });

    await setDevDialogueState("session-1", "summary_confirming", "awaiting_decision");

    const [, body] = vi.mocked(axios.post).mock.calls[0];
    expect(body).toMatchObject({
      session_id: "session-1",
      stage: "summary_confirming",
      sub_state: "awaiting_decision",
    });
  });

  it("sends stage and sub_state for pir_confirming", async () => {
    vi.mocked(axios.post).mockResolvedValue({ data: { ...mockDevState, stage: "pir_confirming" } });

    await setDevDialogueState("session-1", "pir_confirming", "awaiting_modifications");

    const [, body] = vi.mocked(axios.post).mock.calls[0];
    expect(body).toMatchObject({
      stage: "pir_confirming",
      sub_state: "awaiting_modifications",
    });
  });

  it("normalizes sub_state to null for non-confirm stages", async () => {
    vi.mocked(axios.post).mockResolvedValue({ data: { ...mockDevState, stage: "gathering", sub_state: null } });

    // Even if a sub_state is passed in, non-confirm stages must send null.
    await setDevDialogueState("session-1", "gathering", "awaiting_decision");

    const [, body] = vi.mocked(axios.post).mock.calls[0];
    expect((body as Record<string, unknown>).sub_state).toBeNull();
  });

  it("defaults sub_state to 'awaiting_decision' when not provided", async () => {
    vi.mocked(axios.post).mockResolvedValue({ data: mockDevState });

    await setDevDialogueState("session-1", "summary_confirming");

    const [, body] = vi.mocked(axios.post).mock.calls[0];
    expect((body as Record<string, unknown>).sub_state).toBe("awaiting_decision");
  });

  it("returns the response data", async () => {
    vi.mocked(axios.post).mockResolvedValue({ data: mockDevState });

    const result = await setDevDialogueState(
      "session-1",
      "summary_confirming",
    );

    expect(result).toEqual(mockDevState);
  });

  it("throws when the API call fails", async () => {
    vi.mocked(axios.post).mockRejectedValue(new Error("Server error"));

    await expect(
      setDevDialogueState("session-1", "summary_confirming"),
    ).rejects.toThrow("Server error");
  });
});

// ── resetDevDialogueState ─────────────────────────────────────────────────────

describe("resetDevDialogueState", () => {
  const mockResetResponse: DialogueDevStateResponse = {
    session_id: "session-1",
    stage: "initial",
    phase: "direction",
    sub_state: null,
    question_count: 0,
    max_questions: 10,
    missing_context_fields: [],
    has_sufficient_context: false,
    awaiting_user_decision: false,
    has_modifications: false,
  };

  it("POSTs to the reset endpoint with session_id as a query param", async () => {
    vi.mocked(axios.post).mockResolvedValue({ data: mockResetResponse });

    await resetDevDialogueState("session-1");

    expect(axios.post).toHaveBeenCalledWith(
      `${BASE}/api/dialogue/dev/reset`,
      null,
      { params: { session_id: "session-1" }, ...DEV_TIMEOUT },
    );
  });

  it("returns the response data", async () => {
    vi.mocked(axios.post).mockResolvedValue({ data: mockResetResponse });

    const result = await resetDevDialogueState("session-1");

    expect(result).toEqual(mockResetResponse);
  });

  it("throws when the API call fails", async () => {
    vi.mocked(axios.post).mockRejectedValue(new Error("Server error"));

    await expect(resetDevDialogueState("session-1")).rejects.toThrow(
      "Server error",
    );
  });
});
