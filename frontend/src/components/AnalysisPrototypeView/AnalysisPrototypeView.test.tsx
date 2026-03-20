import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, it, expect, beforeEach, vi } from "vitest";
import type { ReactNode } from "react";
import AnalysisPrototypeView from "./AnalysisPrototypeView";
import { ConversationProvider } from "../../contexts/ConversationContext/ConversationContext";
import type { ConversationStore } from "../../types/conversation";
import type {
  AnalysisDraftResponse,
  CouncilNote,
} from "../../types/analysis";

vi.mock("../../services/analysis", () => ({
  getAnalysisDraft: vi.fn(),
  runAnalysisCouncil: vi.fn(),
}));

import {
  getAnalysisDraft,
  runAnalysisCouncil,
} from "../../services/analysis";

const STORAGE_KEY = "mcp-conversations";

const demoCouncilNote: CouncilNote = {
  status: "complete",
  question:
    "Assess whether the phishing staging indicates coordinated access development.",
  participants: [
    "US Strategic Analyst",
    "Neutral Evidence Analyst",
  ],
  rounds_completed: 2,
  summary:
    "The council assessed the findings as deliberate access-development activity.",
  key_agreements: [
    "Credential theft and phishing staging reinforce the access-development hypothesis.",
  ],
  key_disagreements: [
    "Participants differed on whether disruption preparation is likely.",
  ],
  final_recommendation:
    "Validate victimology and correlate the infrastructure overlap before escalating attribution.",
  full_debate: [
    {
      round: 1,
      participant: "Neutral Evidence Analyst",
      response:
        "The evidence is sufficient for a cautious access-development assessment.",
      timestamp: "2026-03-20T10:00:00Z",
    },
  ],
  transcript_path: "backend/data/outputs/council_transcripts/demo.md",
};

const demoResponse: AnalysisDraftResponse = {
  processing_result: {
    findings: [
      {
        id: "F-001",
        title:
          "Repeated credential-access activity against telecom administration services",
        finding:
          "Demo telemetry indicates a short-duration surge of credential-access activity targeting remote administration services.",
        evidence_summary:
          "Authentication failures were followed by successful logins and mailbox rule changes.",
        source: "network_telemetry",
        confidence: 82,
        relevant_to: ["PIR-1", "PIR-2"],
        supporting_data: {
          iocs: ["demo-user-agent"],
          attack_ids: ["T1078"],
          domains: ["vpn.nordtel-demo.net"],
          urls: [],
        },
        why_it_matters:
          "This could provide a credible access path into telecom administration workflows.",
        uncertainties: [
          "Successful logins may have used sprayed passwords or previously compromised credentials.",
        ],
      },
      {
        id: "F-002",
        title: "Recently registered lookalike domains appear staged for telecom phishing",
        finding:
          "Recently registered lookalike domains appear staged for telecom phishing.",
        evidence_summary:
          "Passive DNS and page captures indicate Nordic telecom brand impersonation.",
        source: "osint",
        confidence: 76,
        relevant_to: ["PIR-1"],
        supporting_data: {
          domains: ["nordtel-support.net"],
          urls: ["https://nordtel-support.net/auth/verify"],
        },
        why_it_matters:
          "This supports a parallel credential-theft path against telecom staff.",
        uncertainties: [
          "The specific lure delivery method remains unknown.",
        ],
      },
    ],
    gaps: [
      "Attribution remains unclear.",
      "Victimology is incomplete.",
    ],
  },
  analysis_draft: {
    summary:
      "Analysis of processed findings indicates a likely access-development campaign against Northern European telecom functions.",
    key_judgments: [
      "Repeated credential-access activity suggests deliberate targeting of privileged telecom workflows.",
    ],
    per_perspective_implications: {
      us: ["US analysts should monitor shared vendor-access pathways."],
      norway: ["Norwegian operators should prioritize identity and telecom admin review."],
      china: ["Actor-specific judgments should remain limited while attribution is unresolved."],
      eu: ["Cross-border telecom dependencies increase regional significance."],
      russia: ["Regional critical-infrastructure scenarios remain relevant."],
      neutral: ["The evidence is stronger on access preparation than final intent."],
    },
    recommended_actions: [
      "Review privileged telecom administration accounts for anomalous logins.",
    ],
    information_gaps: [
      "Attribution remains unclear.",
      "Victimology is incomplete.",
    ],
  },
  latest_council_note: null,
};

function createWrapper() {
  return function Wrapper({ children }: { children: ReactNode }) {
    return <ConversationProvider>{children}</ConversationProvider>;
  };
}

function seedConversationStore(perspectives = ["US", "NEUTRAL"]) {
  const store: ConversationStore = {
    conversations: [
      {
        id: "conv-1",
        title: "Analysis conversation",
        messages: [],
        perspectives,
        sessionId: "session-1",
        isConfirming: false,
        stage: "complete",
        subState: null,
        createdAt: 1000,
        updatedAt: 1000,
      },
    ],
    activeConversationId: "conv-1",
  };
  localStorage.setItem(STORAGE_KEY, JSON.stringify(store));
}

describe("AnalysisPrototypeView", () => {
  beforeEach(() => {
    localStorage.clear();
    vi.clearAllMocks();
    seedConversationStore();
  });

  it("renders a loading state while the draft is being fetched", () => {
    vi.mocked(getAnalysisDraft).mockReturnValue(new Promise(() => {}));

    render(<AnalysisPrototypeView />, { wrapper: createWrapper() });

    expect(screen.getByText(/loading analysis draft/i)).toBeInTheDocument();
  });

  it("renders findings and draft sections after a successful load", async () => {
    vi.mocked(getAnalysisDraft).mockResolvedValue(demoResponse);

    render(<AnalysisPrototypeView />, { wrapper: createWrapper() });

    expect(
      await screen.findByText(/likely access-development campaign/i),
    ).toBeInTheDocument();
    expect(
      screen.getByLabelText(/finding f-001/i),
    ).toBeInTheDocument();
    expect(screen.getAllByText("F-001").length).toBeGreaterThan(0);
    expect(screen.getAllByText(/Evidence summary/i).length).toBeGreaterThan(0);
    expect(screen.getAllByText(/Supporting data/i).length).toBeGreaterThan(0);
    expect(screen.getByText(/attack ids/i)).toBeInTheDocument();
    expect(screen.getByText(/vpn.nordtel-demo.net/i)).toBeInTheDocument();
    expect(
      screen.getByText(/Perspective Implications/i),
    ).toBeInTheDocument();
    expect(
      screen.getByText(/Review privileged telecom administration accounts/i),
    ).toBeInTheDocument();
    expect(screen.getByText(/Attribution remains unclear/i)).toBeInTheDocument();
  });

  it("renders an error state when the fetch fails", async () => {
    vi.mocked(getAnalysisDraft).mockRejectedValue(
      new Error("backend unavailable"),
    );

    render(<AnalysisPrototypeView />, { wrapper: createWrapper() });

    expect(
      await screen.findByText(/failed to load analysis draft/i),
    ).toBeInTheDocument();
    expect(screen.getByText(/backend unavailable/i)).toBeInTheDocument();
  });

  it("renders a finding card with visible confidence", async () => {
    vi.mocked(getAnalysisDraft).mockResolvedValue(demoResponse);

    render(<AnalysisPrototypeView />, { wrapper: createWrapper() });

    expect(await screen.findByLabelText(/finding f-001/i)).toBeInTheDocument();
    expect(screen.getByText(/82% confidence/i)).toBeInTheDocument();
  });

  it("renders finding uncertainties clearly", async () => {
    vi.mocked(getAnalysisDraft).mockResolvedValue(demoResponse);

    render(<AnalysisPrototypeView />, { wrapper: createWrapper() });

    expect((await screen.findAllByText(/Uncertainties/i)).length).toBeGreaterThan(0);
    expect(
      screen.getByText(/Successful logins may have used sprayed passwords/i),
    ).toBeInTheDocument();
  });

  it("supports perspective chip selection", async () => {
    const user = userEvent.setup();
    vi.mocked(getAnalysisDraft).mockResolvedValue(demoResponse);

    render(<AnalysisPrototypeView />, { wrapper: createWrapper() });

    const chinaChip = await screen.findByRole("button", { name: "China" });
    expect(screen.getByRole("button", { name: "US" })).toHaveAttribute(
      "aria-pressed",
      "true",
    );
    expect(chinaChip).toHaveAttribute("aria-pressed", "false");

    await user.click(chinaChip);

    expect(chinaChip).toHaveAttribute("aria-pressed", "true");
  });

  it("accepts textarea input and submits a council request", async () => {
    const user = userEvent.setup();
    vi.mocked(getAnalysisDraft).mockResolvedValue(demoResponse);
    vi.mocked(runAnalysisCouncil).mockResolvedValue(demoCouncilNote);

    render(<AnalysisPrototypeView />, { wrapper: createWrapper() });

    const textarea = await screen.findByLabelText(/Debate point/i);
    await user.type(
      textarea,
      "Assess whether the selected findings indicate coordinated access development.",
    );
    await user.click(
      screen.getByLabelText(
        /F-001 Repeated credential-access activity against telecom administration services/i,
      ),
    );
    await user.click(screen.getByRole("button", { name: /Run council/i }));

    await waitFor(() => {
      expect(runAnalysisCouncil).toHaveBeenCalledWith({
        session_id: "session-1",
        debate_point:
          "Assess whether the selected findings indicate coordinated access development.",
        finding_ids: ["F-001"],
        selected_perspectives: ["us", "neutral"],
      });
    });
    expect(
      await screen.findByText(/deliberate access-development activity/i),
    ).toBeInTheDocument();
  });

  it("shows validation feedback when council input is incomplete", async () => {
    const user = userEvent.setup();
    vi.mocked(getAnalysisDraft).mockResolvedValue(demoResponse);

    render(<AnalysisPrototypeView />, { wrapper: createWrapper() });

    await screen.findByText(/Run council on a point/i);
    await user.click(screen.getByRole("button", { name: /Run council/i }));

    expect(
      await screen.findByText(
        /Enter a debate point or select at least one finding/i,
      ),
    ).toBeInTheDocument();
  });

  it("renders the council result and expands the transcript without changing the draft", async () => {
    const user = userEvent.setup();
    vi.mocked(getAnalysisDraft).mockResolvedValue({
      ...demoResponse,
      latest_council_note: demoCouncilNote,
    });

    render(<AnalysisPrototypeView />, { wrapper: createWrapper() });

    expect(
      await screen.findByText(/deliberate access-development activity/i),
    ).toBeInTheDocument();
    expect(
      screen.getByText(/likely access-development campaign against Northern European telecom functions/i),
    ).toBeInTheDocument();
    expect(screen.getByText(/US Strategic Analyst/i)).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: /Show full debate/i }));

    expect(
      await screen.findByText(
        /The evidence is sufficient for a cautious access-development assessment/i,
      ),
    ).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: /Hide full debate/i }));

    await waitFor(() => {
      expect(
        screen.queryByText(
          /The evidence is sufficient for a cautious access-development assessment/i,
        ),
      ).not.toBeInTheDocument();
    });
    expect(
      screen.getByText(/likely access-development campaign against Northern European telecom functions/i),
    ).toBeInTheDocument();
  });

  it("reloads with the persisted council note while keeping the draft visible", async () => {
    const user = userEvent.setup();
    vi.mocked(getAnalysisDraft)
      .mockResolvedValueOnce(demoResponse)
      .mockResolvedValueOnce({
        ...demoResponse,
        latest_council_note: demoCouncilNote,
      });
    vi.mocked(runAnalysisCouncil).mockResolvedValue(demoCouncilNote);

    const view = render(<AnalysisPrototypeView />, { wrapper: createWrapper() });

    await screen.findByText(/likely access-development campaign/i);
    await user.type(
      screen.getByLabelText(/Debate point/i),
      "Assess whether coordinated access development is the strongest interpretation.",
    );
    await user.click(screen.getByRole("button", { name: /Run council/i }));
    await screen.findByText(/deliberate access-development activity/i);

    view.unmount();

    render(<AnalysisPrototypeView />, { wrapper: createWrapper() });

    expect(
      await screen.findByText(/deliberate access-development activity/i),
    ).toBeInTheDocument();
    expect(
      screen.getByText(/likely access-development campaign against Northern European telecom functions/i),
    ).toBeInTheDocument();
  });
});
