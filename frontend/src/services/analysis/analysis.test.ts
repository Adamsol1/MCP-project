import { describe, it, expect, vi, beforeEach } from "vitest";
import axios from "axios";
import { runAnalysisCouncil } from "./analysis";
import type { RunAnalysisCouncilRequest, CouncilNote } from "../../types/analysis";

vi.mock("axios");

const BASE = "http://127.0.0.1:8004";

beforeEach(() => {
  vi.clearAllMocks();
});

const request: RunAnalysisCouncilRequest = {
  session_id: "session-abc",
  debate_point: "Assess the phishing campaign attribution.",
  finding_ids: ["F-001", "F-002"],
  selected_perspectives: ["US", "NEUTRAL"],
  council_settings: null,
};

const mockNote: CouncilNote = {
  status: "complete",
  question: "Assess the phishing campaign attribution.",
  participants: ["US Analyst", "Neutral Evidence Analyst"],
  rounds_completed: 2,
  summary: "The council reached a cautious consensus on access-development intent.",
  key_agreements: ["Credential theft is the primary vector."],
  key_disagreements: [],
  final_recommendation: "Validate victimology before escalating attribution.",
  full_debate: [],
  transcript_path: null,
};

describe("runAnalysisCouncil", () => {
  it("POSTs to the correct council endpoint and returns the response data", async () => {
    vi.mocked(axios.post).mockResolvedValue({ data: mockNote });

    const result = await runAnalysisCouncil(request);

    expect(axios.post).toHaveBeenCalledWith(
      `${BASE}/api/analysis/council`,
      request,
    );
    expect(result).toEqual(mockNote);
  });

  it("propagates errors from the API", async () => {
    vi.mocked(axios.post).mockRejectedValue(new Error("Network error"));

    await expect(runAnalysisCouncil(request)).rejects.toThrow("Network error");
  });

  it("returns the full council note including key_agreements and full_debate", async () => {
    vi.mocked(axios.post).mockResolvedValue({ data: mockNote });

    const result = await runAnalysisCouncil(request);

    expect(result.key_agreements).toEqual(["Credential theft is the primary vector."]);
    expect(result.rounds_completed).toBe(2);
  });
});
