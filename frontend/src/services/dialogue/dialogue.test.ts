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
  getPendingElicitation,
  respondToElicitation,
  listDevDialogueSnapshots,
  restoreDevDialogueSnapshot,
} from "./dialogue";
import type {
  DialogueApiResponse,
  CollectionStatus,
  DialogueDevStateResponse,
  DialogueDevSnapshot,
} from "./dialogue";

vi.mock("axios");

const BASE = "http://127.0.0.1:8000";
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
        settings_source_timeframes: {},
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

// ── getPendingElicitation ─────────────────────────────────────────────────────

describe("getPendingElicitation", () => {
  it("returns the pending elicitation when one is present", async () => {
    const pending = {
      message: "Which time range should we use?",
      options: ["7 days", "30 days", "90 days"],
    };
    vi.mocked(axios.get).mockResolvedValue({
      data: { pending_elicitation: pending },
    });

    const result = await getPendingElicitation("session-1");

    expect(axios.get).toHaveBeenCalledWith(
      `${BASE}/api/dialogue/elicitation/pending/session-1`,
      expect.objectContaining({ timeout: expect.any(Number) }),
    );
    expect(result).toEqual(pending);
  });

  it("returns null when there is no pending elicitation", async () => {
    vi.mocked(axios.get).mockResolvedValue({
      data: { pending_elicitation: null },
    });

    const result = await getPendingElicitation("session-1");

    expect(result).toBeNull();
  });

  it("returns null when the API call fails (best-effort)", async () => {
    vi.mocked(axios.get).mockRejectedValue(new Error("Network error"));

    const result = await getPendingElicitation("session-1");

    expect(result).toBeNull();
  });
});

// ── respondToElicitation ──────────────────────────────────────────────────────

describe("respondToElicitation", () => {
  it("POSTs the user choice to the elicitation respond endpoint", async () => {
    vi.mocked(axios.post).mockResolvedValue({ data: {} });

    await respondToElicitation("session-1", "30 days");

    expect(axios.post).toHaveBeenCalledWith(
      `${BASE}/api/dialogue/elicitation/session-1/respond`,
      { choice: "30 days" },
      expect.objectContaining({ timeout: expect.any(Number) }),
    );
  });

  it("propagates errors from the API", async () => {
    vi.mocked(axios.post).mockRejectedValue(new Error("Server error"));

    await expect(respondToElicitation("session-1", "7 days")).rejects.toThrow(
      "Server error",
    );
  });
});

// ── listDevDialogueSnapshots ──────────────────────────────────────────────────

describe("listDevDialogueSnapshots", () => {
  const mockSnapshots: DialogueDevSnapshot[] = [
    {
      session_id: "snap-1",
      title: "APT29 investigation",
      artifacts: { session: true, collection: true, processing: false, analysis: false },
    },
  ];

  it("returns the list of snapshots from the API", async () => {
    vi.mocked(axios.get).mockResolvedValue({ data: mockSnapshots });

    const result = await listDevDialogueSnapshots();

    expect(axios.get).toHaveBeenCalledWith(
      `${BASE}/api/dialogue/dev/snapshots`,
      expect.objectContaining({ timeout: expect.any(Number) }),
    );
    expect(result).toEqual(mockSnapshots);
  });

  it("throws when the API call fails", async () => {
    vi.mocked(axios.get).mockRejectedValue(new Error("Unauthorized"));

    await expect(listDevDialogueSnapshots()).rejects.toThrow("Unauthorized");
  });
});

// ── restoreDevDialogueSnapshot ────────────────────────────────────────────────

describe("restoreDevDialogueSnapshot", () => {
  const mockRestoreResponse = {
    stage: "pir_confirming",
    sub_state: "awaiting_decision",
    phase: "direction",
    messages: [{ text: "Restored message", sender: "system", type: "question" }],
  };

  it("POSTs to the restore endpoint with the correct body", async () => {
    vi.mocked(axios.post).mockResolvedValue({ data: mockRestoreResponse });

    const result = await restoreDevDialogueSnapshot(
      "source-session",
      "target-session",
      "pir_confirming",
      "direction",
    );

    expect(axios.post).toHaveBeenCalledWith(
      `${BASE}/api/dialogue/dev/restore`,
      {
        source_session_id: "source-session",
        target_session_id: "target-session",
        target_stage: "pir_confirming",
        target_phase: "direction",
      },
      expect.objectContaining({ timeout: expect.any(Number) }),
    );
    expect(result).toEqual(mockRestoreResponse);
  });

  it("throws when the API call fails", async () => {
    vi.mocked(axios.post).mockRejectedValue(new Error("Restore failed"));

    await expect(
      restoreDevDialogueSnapshot(
        "source-session",
        "target-session",
        "pir_confirming",
        "direction",
      ),
    ).rejects.toThrow("Restore failed");
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
