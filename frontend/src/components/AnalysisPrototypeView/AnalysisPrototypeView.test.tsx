import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, it, expect, beforeEach, vi } from "vitest";
import type { ReactNode } from "react";
import AnalysisPrototypeView from "./AnalysisPrototypeView";
import { ConversationProvider } from "../../contexts/ConversationContext/ConversationContext";
import { SettingsProvider } from "../../contexts/SettingsContext/SettingsContext";
import type { ConversationStore } from "../../types/conversation";
import type { AnalysisDraftResponse, CouncilNote } from "../../types/analysis";

vi.mock("../../services/analysis/analysis", () => ({
  getAnalysisDraft: vi.fn(),
  runAnalysisCouncil: vi.fn(),
}));

import {
  getAnalysisDraft,
  runAnalysisCouncil,
} from "../../services/analysis/analysis";

const STORAGE_KEY = "mcp-conversations";

const demoCouncilNote: CouncilNote = {
  status: "complete",
  question:
    "Assess whether the phishing staging indicates coordinated access development.",
  participants: ["US Strategic Analyst", "Neutral Evidence Analyst"],
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
        'The evidence is sufficient for a cautious access-development assessment.\n\n**Uncertainties:**\n- Attribution remains unresolved.\n\nVOTE: {"option":"Cautious access development assessment","confidence":0.81,"rationale":"Credential theft and phishing staging support the access-development hypothesis, but attribution is still unresolved."}',
      timestamp: "2026-03-20T10:00:00Z",
    },
    {
      round: 1,
      participant: "US Strategic Analyst",
      response:
        'The activity matters because allied telecom infrastructure is a strategic dependency.\n\n**Operational implications:**\n- Shared vendor-access pathways may be exposed.\n\nVOTE: {"option":"Strategic telecom intrusion assessment","confidence":0.87,"rationale":"The findings suggest deliberate access development against infrastructure relevant to alliance coordination."}',
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
        title:
          "Recently registered lookalike domains appear staged for telecom phishing",
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
        uncertainties: ["The specific lure delivery method remains unknown."],
      },
    ],
    gaps: ["Attribution remains unclear.", "Victimology is incomplete."],
  },
  analysis_draft: {
    summary:
      "Analysis of processed findings indicates a likely access-development campaign against Northern European telecom functions.",
    key_judgments: [
      "Repeated credential-access activity suggests deliberate targeting of privileged telecom workflows.",
    ],
    per_perspective_implications: {
      us: ["US analysts should monitor shared vendor-access pathways."],
      norway: [
        "Norwegian operators should prioritize identity and telecom admin review.",
      ],
      china: [
        "Actor-specific judgments should remain limited while attribution is unresolved.",
      ],
      eu: ["Cross-border telecom dependencies increase regional significance."],
      russia: ["Regional critical-infrastructure scenarios remain relevant."],
      neutral: [
        "The evidence is stronger on access preparation than final intent.",
      ],
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
  data_source: "session",
};

function createWrapper() {
  return function Wrapper({ children }: { children: ReactNode }) {
    return (
      <SettingsProvider>
        <ConversationProvider>{children}</ConversationProvider>
      </SettingsProvider>
    );
  };
}

function seedConversationStore(perspectives = ["US", "NEUTRAL"]) {
  const store: ConversationStore = {
    conversations: [
      {
        id: "conv-1",
        title: "Northern Europe telecom access-development assessment",
        messages: [],
        perspectives,
        sessionId: "session-1",
        isConfirming: false,
        stage: "complete",
        phase: "processing",
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
      await screen.findByRole("heading", {
        name: /Northern Europe telecom access-development assessment/i,
      }),
    ).toBeInTheDocument();
    expect(
      screen.getByText(/likely access-development campaign/i),
    ).toBeInTheDocument();
    expect(screen.getByLabelText(/finding f-001/i)).toBeInTheDocument();
    expect(screen.getAllByText("F-001").length).toBeGreaterThan(0);
    expect(screen.getAllByText(/Evidence summary/i).length).toBeGreaterThan(0);
    expect(screen.getByText(/ATT&CK Techniques/i)).toBeInTheDocument();
    expect(screen.getByText(/Perspective Implications/i)).toBeInTheDocument();
    expect(
      screen.getByText(/Review privileged telecom administration accounts/i),
    ).toBeInTheDocument();
    expect(
      screen.getByText(/Attribution remains unclear/i),
    ).toBeInTheDocument();
  });

  it("falls back to the first finding title when the conversation title is generic", async () => {
    localStorage.clear();
    const store: ConversationStore = {
      conversations: [
        {
          id: "conv-1",
          title: "New conversation",
          messages: [],
          perspectives: ["US", "NEUTRAL"],
          sessionId: "session-1",
          isConfirming: false,
          stage: "complete",
          phase: "processing",
          subState: null,
          createdAt: 1000,
          updatedAt: 1000,
        },
      ],
      activeConversationId: "conv-1",
    };
    localStorage.setItem(STORAGE_KEY, JSON.stringify(store));
    vi.mocked(getAnalysisDraft).mockResolvedValue(demoResponse);

    render(<AnalysisPrototypeView />, { wrapper: createWrapper() });

    expect(
      await screen.findByRole("heading", {
        name: /Repeated credential-access activity against telecom administration services/i,
        level: 1,
      }),
    ).toBeInTheDocument();
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

  it("shows the processing-required error when no processed result exists", async () => {
    vi.mocked(getAnalysisDraft).mockRejectedValue({
      response: {
        data: {
          detail:
            "No processed result available for this session. Complete processing first.",
        },
      },
    });

    render(<AnalysisPrototypeView />, { wrapper: createWrapper() });

    expect(
      await screen.findByText(
        /No processed result available for this session. Complete processing first./i,
      ),
    ).toBeInTheDocument();
  });

  it("renders a finding card with visible confidence", async () => {
    vi.mocked(getAnalysisDraft).mockResolvedValue(demoResponse);

    render(<AnalysisPrototypeView />, { wrapper: createWrapper() });

    expect(await screen.findByLabelText(/finding f-001/i)).toBeInTheDocument();
    expect(screen.getByText(/^82%$/i)).toBeInTheDocument();
  });

  it("renders finding uncertainties clearly", async () => {
    vi.mocked(getAnalysisDraft).mockResolvedValue(demoResponse);

    render(<AnalysisPrototypeView />, { wrapper: createWrapper() });

    expect(
      (await screen.findAllByText(/Uncertainties/i)).length,
    ).toBeGreaterThan(0);
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
        council_settings: {
          mode: "conference",
          rounds: 2,
          timeout_seconds: 180,
          vote_retry_enabled: true,
          vote_retry_attempts: 1,
        },
      });
    });
    expect(
      await screen.findByText(/deliberate access-development activity/i),
    ).toBeInTheDocument();
  });

  it("shows the active council runtime settings in the form", async () => {
    vi.mocked(getAnalysisDraft).mockResolvedValue(demoResponse);

    render(<AnalysisPrototypeView />, { wrapper: createWrapper() });

    expect(
      await screen.findByText(
        /Runtime: conference, 2 rounds, timeout 180s, vote retry 1x/i,
      ),
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
      screen.getByText(
        /likely access-development campaign against Northern European telecom functions/i,
      ),
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
      screen.getByText(
        /likely access-development campaign against Northern European telecom functions/i,
      ),
    ).toBeInTheDocument();
  });

  it("switches between council summary and participant views", async () => {
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
      screen.getByRole("button", { name: /Council Summary/i }),
    ).toHaveAttribute("aria-pressed", "true");
    expect(screen.getByText(/Key agreements/i)).toBeInTheDocument();

    await user.click(
      screen.getByRole("button", { name: /Neutral Evidence Analyst/i }),
    );

    expect(
      screen.getByRole("button", { name: /Neutral Evidence Analyst/i }),
    ).toHaveAttribute("aria-pressed", "true");
    expect(screen.getByText(/Perspective overview/i)).toBeInTheDocument();
    expect(
      screen.getByText(/Attribution remains unresolved/i),
    ).toBeInTheDocument();
    expect(
      screen.getByText(/Cautious access development assessment/i),
    ).toBeInTheDocument();
    expect(screen.getByText(/81% confidence/i)).toBeInTheDocument();
    expect(screen.queryByText(/Key agreements/i)).not.toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: /Council Summary/i }));

    expect(screen.getByText(/Key agreements/i)).toBeInTheDocument();
    await waitFor(() => {
      expect(
        screen.queryByText(/Attribution remains unresolved/i),
      ).not.toBeInTheDocument();
    });
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

    const view = render(<AnalysisPrototypeView />, {
      wrapper: createWrapper(),
    });

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
      screen.getByText(
        /likely access-development campaign against Northern European telecom functions/i,
      ),
    ).toBeInTheDocument();
  });
});
