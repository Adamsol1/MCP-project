import { render, screen, waitFor, fireEvent } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, it, expect, beforeEach, vi } from "vitest";
import type { ReactNode } from "react";
import AnalysisWorkspace from "./AnalysisWorkspace";
import { ConversationProvider } from "../../contexts/ConversationContext/ConversationContext";
import { SettingsProvider } from "../../contexts/SettingsContext/SettingsContext";
import { WorkspaceProvider } from "../../contexts/WorkspaceContext/WorkspaceContext";
import { ToastProvider } from "../../contexts/Toast/ToastContext";
import type { ConversationStore, Message } from "../../types/conversation";
import type { AnalysisResponse, CouncilNote } from "../../types/analysis";
import { axe } from "vitest-axe";

// Mock the dialogue service so council submissions don't need a live backend.
vi.mock("../../services/dialogue/dialogue", () => ({
  sendMessage: vi.fn(),
  listDevDialogueSnapshots: vi.fn().mockResolvedValue([]),
  restoreDevDialogueSnapshot: vi.fn(),
  setDevDialogueState: vi.fn(),
}));

import { sendMessage } from "../../services/dialogue/dialogue";

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

const demoResponse: AnalysisResponse = {
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
        computed_confidence: null,
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
        computed_confidence: null,
      },
    ],
    gaps: ["Attribution remains unclear.", "Victimology is incomplete."],
  },
  analysis_draft: {
    title: "Northern Europe telecom access-development assessment",
    summary:
      "Analysis of processed findings indicates a likely access-development campaign against Northern European telecom functions.",
    key_judgments: [
      "Repeated credential-access activity suggests deliberate targeting of privileged telecom workflows.",
    ],
    per_perspective_implications: {
      us: [
        {
          assertion:
            "US analysts should monitor shared vendor-access pathways.",
          supporting_finding_ids: ["F-001"],
          source_types: ["network_telemetry"],
          confidence: null,
        },
      ],
      neutral: [
        {
          assertion:
            "The evidence is stronger on access preparation than final intent.",
          supporting_finding_ids: ["F-002"],
          source_types: ["osint"],
          confidence: null,
        },
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
  collection_coverage: null,
  data_source: "session",
};

function createWrapper() {
  return function Wrapper({ children }: { children: ReactNode }) {
    return (
      <SettingsProvider>
        <ToastProvider>
          <ConversationProvider>
            <WorkspaceProvider>{children}</WorkspaceProvider>
          </ConversationProvider>
        </ToastProvider>
      </SettingsProvider>
    );
  };
}

function seedConversationStore(
  perspectives = ["US", "NEUTRAL"],
  response: AnalysisResponse = demoResponse,
  councilNote: CouncilNote | null = null,
) {
  const messages: Message[] = [
    {
      id: "msg-1",
      sender: "system",
      text: "Analysis complete",
      type: "analysis",
      data: response,
    },
  ];
  if (councilNote) {
    messages.push({
      id: "msg-2",
      sender: "system",
      text: "Council complete",
      type: "council",
      data: councilNote,
    });
  }
  const store: ConversationStore = {
    conversations: [
      {
        id: "conv-1",
        title: "Northern Europe telecom access-development assessment",
        messages,
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

describe("AnalysisWorkspace", () => {
  beforeEach(() => {
    localStorage.clear();
    vi.clearAllMocks();
    // Default: resolve silently so the dev-snapshots loader doesn't throw.
    vi.mocked(sendMessage).mockResolvedValue({
      question: "",
      action: "complete",
    });
    seedConversationStore();
  });

  it("shows a fallback when no analysis message exists", () => {
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

    render(<AnalysisWorkspace />, { wrapper: createWrapper() });

    expect(
      screen.getByText(/No analysis available for this session/i),
    ).toBeInTheDocument();
  });

  it("renders findings and analysis sections", async () => {
    render(<AnalysisWorkspace />, { wrapper: createWrapper() });

    expect(
      await screen.findByRole("heading", {
        name: /Northern Europe telecom access-development assessment/i,
      }),
    ).toBeInTheDocument();
    expect(
      screen.getByText(/likely access-development campaign/i),
    ).toBeInTheDocument();
    // Finding ID badge is always visible in the collapsed row header
    expect(screen.getAllByText("F-001").length).toBeGreaterThan(0);
    // Perspective Implications section is rendered
    expect(screen.getByText(/Perspective Implications/i)).toBeInTheDocument();
    // Recommended actions and information gaps are always rendered
    expect(
      screen.getByText(/Review privileged telecom administration accounts/i),
    ).toBeInTheDocument();
    expect(
      screen.getByText(/Attribution remains unclear/i),
    ).toBeInTheDocument();
  });

  it("falls back to the first finding title when conversation title and summary are generic", async () => {
    localStorage.clear();
    const store: ConversationStore = {
      conversations: [
        {
          id: "conv-1",
          title: "New conversation",
          messages: [
            {
              id: "msg-1",
              sender: "system",
              text: "Analysis complete",
              type: "analysis",
              data: {
                ...demoResponse,
                analysis_draft: {
                  ...demoResponse.analysis_draft,
                  title: "",
                  summary: "",
                },
              },
            },
          ],
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

    render(<AnalysisWorkspace />, { wrapper: createWrapper() });

    expect(
      await screen.findByRole("heading", {
        name: /Repeated credential-access activity against telecom administration services/i,
        level: 1,
      }),
    ).toBeInTheDocument();
  });

  it("renders a finding card with visible confidence", async () => {
    render(<AnalysisWorkspace />, { wrapper: createWrapper() });

    // F-001 ID badge is visible in the collapsed row header
    expect(await screen.findAllByText("F-001")).not.toHaveLength(0);
    expect(screen.getByText("82%")).toBeInTheDocument();
  });

  it("renders finding uncertainties after expanding the row", async () => {
    const user = userEvent.setup();
    render(<AnalysisWorkspace />, { wrapper: createWrapper() });

    // F-001 row is collapsed by default; click it to expand
    const findingBtn = await screen.findByRole("button", {
      name: /Repeated credential-access activity against telecom administration services/i,
    });
    await user.click(findingBtn);

    expect(
      await screen.findByText(/Uncertainties/i),
    ).toBeInTheDocument();
    expect(
      screen.getByText(/Successful logins may have used sprayed passwords/i),
    ).toBeInTheDocument();
  });

  it("supports perspective chip selection in CouncilView", async () => {
    const user = userEvent.setup();

    render(<AnalysisWorkspace />, { wrapper: createWrapper() });

    // Navigate from AnalysisView to CouncilView
    await user.click(
      await screen.findByRole("button", { name: /go to council/i }),
    );

    // US and Neutral (shown as "Global") are pre-selected from the conversation
    const usChip = await screen.findByRole("button", { name: /us$/i });
    const chinaChip = screen.getByRole("button", { name: /china$/i });

    expect(usChip).toHaveAttribute("aria-pressed", "true");
    expect(chinaChip).toHaveAttribute("aria-pressed", "false");

    await user.click(chinaChip);

    expect(chinaChip).toHaveAttribute("aria-pressed", "true");
  });

  it("accepts textarea input and submits a council request", async () => {
    const user = userEvent.setup();

    // Mock sendMessage to return a council note response
    vi.mocked(sendMessage).mockResolvedValue({
      question: JSON.stringify(demoCouncilNote),
      action: "show_council",
    });

    render(<AnalysisWorkspace />, { wrapper: createWrapper() });

    // Navigate to CouncilView
    await user.click(
      await screen.findByRole("button", { name: /go to council/i }),
    );

    const textarea = await screen.findByLabelText(/Debate point/i);
    fireEvent.change(textarea, {
      target: {
        value:
          "Assess whether the selected findings indicate coordinated access development.",
      },
    });
    await user.click(
      screen.getByLabelText(
        /F-001 Repeated credential-access activity against telecom administration services/i,
      ),
    );
    await user.click(screen.getByRole("button", { name: /Run council/i }));

    // After council completes the note summary appears in the advisory panel
    expect(
      await screen.findByText(/deliberate access-development activity/i),
    ).toBeInTheDocument();
  });

  it("shows the active council runtime settings in the form", async () => {
    const user = userEvent.setup();
    render(<AnalysisWorkspace />, { wrapper: createWrapper() });

    await user.click(
      await screen.findByRole("button", { name: /go to council/i }),
    );

    // Runtime chips are rendered individually from the settings defaults
    expect(await screen.findByText("Conference")).toBeInTheDocument();
    expect(screen.getByText("2 rounds")).toBeInTheDocument();
    expect(screen.getByText("180s timeout")).toBeInTheDocument();
    expect(screen.getByText(/retry 1×/i)).toBeInTheDocument();
  });

  it("shows validation feedback when council input is incomplete", async () => {
    const user = userEvent.setup();

    render(<AnalysisWorkspace />, { wrapper: createWrapper() });

    await user.click(
      await screen.findByRole("button", { name: /go to council/i }),
    );

    await screen.findByRole("button", { name: /Run council/i });
    await user.click(screen.getByRole("button", { name: /Run council/i }));

    expect(
      await screen.findByText(
        /Enter a debate point or select at least one finding/i,
      ),
    ).toBeInTheDocument();
  });

  it("renders the council result and expands the transcript", async () => {
    const user = userEvent.setup();
    seedConversationStore(["US", "NEUTRAL"], demoResponse, demoCouncilNote);

    render(<AnalysisWorkspace />, { wrapper: createWrapper() });

    // Council view is shown automatically when a council note exists
    expect(
      await screen.findByText(/deliberate access-development activity/i),
    ).toBeInTheDocument();
    // Participant tabs are named by shortenParticipantName
    expect(screen.getByRole("button", { name: "US Analyst" })).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: /Show full debate/i }));

    // Participant summary is visible in the collapsed round header row
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
    // Council summary stays visible after hiding the transcript
    expect(
      screen.getByText(/deliberate access-development activity/i),
    ).toBeInTheDocument();
  });

  it("switches between council summary and participant views", async () => {
    const user = userEvent.setup();
    seedConversationStore(["US", "NEUTRAL"], demoResponse, demoCouncilNote);

    render(<AnalysisWorkspace />, { wrapper: createWrapper() });

    expect(
      await screen.findByText(/deliberate access-development activity/i),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: /^Summary$/i }),
    ).toHaveAttribute("aria-pressed", "true");
    expect(screen.getByText(/Key Agreements/i)).toBeInTheDocument();

    // "Neutral Evidence Analyst" is abbreviated to "EU Analyst" by shortenParticipantName
    // because "neutral" contains the substring "eu" which maps to the EU perspective key.
    await user.click(
      screen.getByRole("button", { name: "EU Analyst" }),
    );

    expect(
      screen.getByRole("button", { name: "EU Analyst" }),
    ).toHaveAttribute("aria-pressed", "true");
    // Participant view shows the parsed response sections
    expect(screen.getByText(/Uncertainties/i)).toBeInTheDocument();
    expect(
      screen.getByText(/Attribution remains unresolved/i),
    ).toBeInTheDocument();
    expect(
      screen.getByText(/Cautious access development assessment/i),
    ).toBeInTheDocument();
    expect(screen.getByText(/81% confidence/i)).toBeInTheDocument();
    expect(screen.queryByText(/Key Agreements/i)).not.toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: /^Summary$/i }));

    expect(screen.getByText(/Key Agreements/i)).toBeInTheDocument();
    await waitFor(() => {
      expect(
        screen.queryByText(/Attribution remains unresolved/i),
      ).not.toBeInTheDocument();
    });
  });
});

describe("AnalysisWorkspace — accessibility (WCAG 2.1 AA)", () => {
  beforeEach(() => {
    localStorage.clear();
    vi.clearAllMocks();
    vi.mocked(sendMessage).mockResolvedValue({
      question: "",
      action: "complete",
    });
    seedConversationStore();
  });

  it("has no violations in initial render", async () => {
    const { container } = render(<AnalysisWorkspace />, {
      wrapper: createWrapper(),
    });
    expect(await axe(container)).toHaveNoViolations();
  });
});
