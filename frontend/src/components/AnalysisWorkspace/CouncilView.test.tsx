import { render, screen, fireEvent } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, it, expect, vi, beforeEach } from "vitest";
import type { ReactNode } from "react";
import CouncilView from "./CouncilView";
import { SettingsProvider } from "../../contexts/SettingsContext/SettingsContext";
import type { CouncilNote, ProcessingFinding } from "../../types/analysis";

// useChat is called by CouncilView; mock it so tests don't need a full
// ConversationProvider + live backend.
vi.mock("../../hooks/useChat/useChat", () => ({
  useChat: vi.fn(),
}));

// @react-pdf/renderer does not work in jsdom.
vi.mock("@react-pdf/renderer", () => ({
  pdf: vi.fn(() => ({ toBlob: vi.fn().mockResolvedValue(new Blob()) })),
  Document: ({ children }: { children: ReactNode }) => <>{children}</>,
  Page: ({ children }: { children: ReactNode }) => <>{children}</>,
  Text: ({ children }: { children: ReactNode }) => <>{children}</>,
  View: ({ children }: { children: ReactNode }) => <>{children}</>,
  StyleSheet: { create: (s: unknown) => s },
}));

import { useChat } from "../../hooks/useChat/useChat";

// ---------------------------------------------------------------------------
// Fixtures
// ---------------------------------------------------------------------------

const demoFindings: ProcessingFinding[] = [
  {
    id: "F-001",
    title: "Credential-access surge",
    finding: "Repeated credential-access activity detected.",
    evidence_summary: "Auth failures followed by successful logins.",
    source: "network_telemetry",
    confidence: 82,
    relevant_to: ["PIR-1"],
    supporting_data: {},
    why_it_matters: "Could provide privileged access.",
    uncertainties: [],
    computed_confidence: null,
  },
  {
    id: "F-002",
    title: "Lookalike phishing domains",
    finding: "Lookalike domains staged for phishing.",
    evidence_summary: "Passive DNS confirms brand impersonation.",
    source: "osint",
    confidence: 60,
    relevant_to: ["PIR-1"],
    supporting_data: {},
    why_it_matters: "Supports a parallel credential-theft path.",
    uncertainties: [],
    computed_confidence: null,
  },
];

const demoCouncilNote: CouncilNote = {
  status: "complete",
  question: "Is this access development or opportunistic intrusion?",
  participants: ["US Strategic Analyst", "Neutral Evidence Analyst"],
  rounds_completed: 1,
  summary: "The council assessed this as deliberate access-development activity.",
  key_agreements: ["Both analysts agree credential theft is targeted."],
  key_disagreements: ["None"],
  final_recommendation: "Escalate attribution efforts to confirm state involvement.",
  full_debate: [
    {
      round: 1,
      participant: "US Strategic Analyst",
      response:
        '## Assessment\n\nThis is clearly state-sponsored.\n\nVOTE: {"option":"State-sponsored access development","confidence":0.88,"rationale":"Infrastructure overlap is consistent with state actor TTPs."}',
      timestamp: "2026-02-01T10:00:00Z",
    },
    {
      round: 1,
      participant: "Neutral Evidence Analyst",
      response:
        'Evidence supports targeted activity but attribution is uncertain.\n\nVOTE: {"option":"Targeted but attribution unclear","confidence":0.65,"rationale":"Correlation exists but independent confirmation is lacking."}',
      timestamp: "2026-02-01T10:01:00Z",
    },
  ],
  transcript_path: null,
};

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function createWrapper() {
  return function Wrapper({ children }: { children: ReactNode }) {
    return <SettingsProvider>{children}</SettingsProvider>;
  };
}

const mockSendCouncilRequest = vi.fn();

function setupUseChatMock(isLoading = false) {
  vi.mocked(useChat).mockReturnValue({
    sendCouncilRequest: mockSendCouncilRequest,
    isLoading,
    sendMessage: vi.fn(),
    sendApproval: vi.fn(),
    sendSources: vi.fn(),
  });
}

function renderCouncilView(
  overrides: Partial<React.ComponentProps<typeof CouncilView>> = {},
) {
  return render(
    <CouncilView
      processingFindings={demoFindings}
      councilNote={null}
      defaultPerspectives={["us", "neutral"]}
      onBack={vi.fn()}
      {...overrides}
    />,
    { wrapper: createWrapper() },
  );
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

describe("CouncilView — perspective selection", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.spyOn(URL, "createObjectURL").mockReturnValue("blob:mock");
    vi.spyOn(URL, "revokeObjectURL").mockReturnValue(undefined);
    setupUseChatMock();
  });

  it("renders all available perspective buttons", () => {
    renderCouncilView();
    // Use word-boundary or end-of-name anchors because "Russia" contains "us" case-insensitively
    for (const [, regex] of [
      ["US", /\bUS$/i],
      ["Norway", /Norway$/i],
      ["China", /China$/i],
      ["EU", /\bEU$/i],
      ["Russia", /Russia$/i],
      ["Global", /Global$/i],
    ] as [string, RegExp][]) {
      expect(screen.getByRole("button", { name: regex })).toBeInTheDocument();
    }
  });

  it("pre-selects defaultPerspectives with aria-pressed='true'", () => {
    renderCouncilView();
    expect(screen.getByRole("button", { name: /us$/i })).toHaveAttribute(
      "aria-pressed",
      "true",
    );
    expect(screen.getByRole("button", { name: /global$/i })).toHaveAttribute(
      "aria-pressed",
      "true",
    );
  });

  it("deselects a pre-selected perspective on click", async () => {
    const user = userEvent.setup();
    renderCouncilView();

    const usBtn = screen.getByRole("button", { name: /us$/i });
    expect(usBtn).toHaveAttribute("aria-pressed", "true");

    await user.click(usBtn);

    expect(usBtn).toHaveAttribute("aria-pressed", "false");
  });

  it("selects an unselected perspective on click", async () => {
    const user = userEvent.setup();
    renderCouncilView();

    const chinaBtn = screen.getByRole("button", { name: /china$/i });
    expect(chinaBtn).toHaveAttribute("aria-pressed", "false");

    await user.click(chinaBtn);

    expect(chinaBtn).toHaveAttribute("aria-pressed", "true");
  });

  it("allows toggling a perspective back off after selecting", async () => {
    const user = userEvent.setup();
    renderCouncilView();

    const chinaBtn = screen.getByRole("button", { name: /china$/i });
    await user.click(chinaBtn);
    expect(chinaBtn).toHaveAttribute("aria-pressed", "true");

    await user.click(chinaBtn);
    expect(chinaBtn).toHaveAttribute("aria-pressed", "false");
  });
});

describe("CouncilView — finding selection", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    setupUseChatMock();
  });

  it("renders all processing findings as toggleable buttons", () => {
    renderCouncilView();
    expect(
      screen.getByRole("button", { name: /F-001 Credential-access surge/i }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: /F-002 Lookalike phishing domains/i }),
    ).toBeInTheDocument();
  });

  it("findings start unselected", () => {
    renderCouncilView();
    expect(
      screen.getByRole("button", { name: /F-001 Credential-access surge/i }),
    ).toHaveAttribute("aria-pressed", "false");
  });

  it("selects a finding on click", async () => {
    const user = userEvent.setup();
    renderCouncilView();

    const f1 = screen.getByRole("button", { name: /F-001 Credential-access surge/i });
    await user.click(f1);
    expect(f1).toHaveAttribute("aria-pressed", "true");
  });

  it("deselects a finding on second click", async () => {
    const user = userEvent.setup();
    renderCouncilView();

    const f1 = screen.getByRole("button", { name: /F-001 Credential-access surge/i });
    await user.click(f1);
    await user.click(f1);
    expect(f1).toHaveAttribute("aria-pressed", "false");
  });

  it("'Select all' button selects all findings", async () => {
    const user = userEvent.setup();
    renderCouncilView();

    await user.click(screen.getByRole("button", { name: /Select all/i }));

    expect(
      screen.getByRole("button", { name: /F-001 Credential-access surge/i }),
    ).toHaveAttribute("aria-pressed", "true");
    expect(
      screen.getByRole("button", { name: /F-002 Lookalike phishing domains/i }),
    ).toHaveAttribute("aria-pressed", "true");
  });

  it("'Deselect all' button appears and clears all findings after selecting all", async () => {
    const user = userEvent.setup();
    renderCouncilView();

    await user.click(screen.getByRole("button", { name: /Select all/i }));
    expect(
      screen.getByRole("button", { name: /Deselect all/i }),
    ).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: /Deselect all/i }));

    expect(
      screen.getByRole("button", { name: /F-001 Credential-access surge/i }),
    ).toHaveAttribute("aria-pressed", "false");
  });
});

describe("CouncilView — form validation", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    setupUseChatMock();
  });

  it("shows validation error when fewer than 2 perspectives are selected", async () => {
    const user = userEvent.setup();
    // Start with only 1 perspective
    renderCouncilView({ defaultPerspectives: ["us"] });

    // Provide a debate point so that's not the blocking issue
    fireEvent.change(screen.getByRole("textbox"), {
      target: { value: "Is this state-sponsored?" },
    });
    await user.click(screen.getByRole("button", { name: /Run council/i }));

    expect(
      screen.getByText(/Select at least 2 perspectives/i),
    ).toBeInTheDocument();
    expect(mockSendCouncilRequest).not.toHaveBeenCalled();
  });

  it("shows validation error when debate point is empty and no findings are selected", async () => {
    const user = userEvent.setup();
    renderCouncilView();

    await user.click(screen.getByRole("button", { name: /Run council/i }));

    expect(
      screen.getByText(/Enter a debate point or select at least one finding/i),
    ).toBeInTheDocument();
    expect(mockSendCouncilRequest).not.toHaveBeenCalled();
  });

  it("clears the validation message when a debate point is typed", async () => {
    const user = userEvent.setup();
    renderCouncilView();

    await user.click(screen.getByRole("button", { name: /Run council/i }));
    expect(
      screen.getByText(/Enter a debate point or select at least one finding/i),
    ).toBeInTheDocument();

    fireEvent.change(screen.getByRole("textbox"), {
      target: { value: "Any debate point" },
    });

    expect(
      screen.queryByText(/Enter a debate point or select at least one finding/i),
    ).not.toBeInTheDocument();
  });

  it("submits successfully with a valid debate point and ≥2 perspectives", async () => {
    const user = userEvent.setup();
    mockSendCouncilRequest.mockResolvedValue(undefined);
    renderCouncilView();

    fireEvent.change(screen.getByRole("textbox"), {
      target: { value: "Is this access development or opportunistic intrusion?" },
    });
    await user.click(screen.getByRole("button", { name: /Run council/i }));

    expect(mockSendCouncilRequest).toHaveBeenCalledOnce();
    expect(mockSendCouncilRequest).toHaveBeenCalledWith(
      expect.objectContaining({
        debatePoint: "Is this access development or opportunistic intrusion?",
        perspectives: expect.arrayContaining(["us", "neutral"]),
      }),
    );
  });

  it("submits successfully with findings selected (no debate point required)", async () => {
    const user = userEvent.setup();
    mockSendCouncilRequest.mockResolvedValue(undefined);
    renderCouncilView();

    await user.click(
      screen.getByRole("button", { name: /F-001 Credential-access surge/i }),
    );
    await user.click(screen.getByRole("button", { name: /Run council/i }));

    expect(mockSendCouncilRequest).toHaveBeenCalledOnce();
    expect(mockSendCouncilRequest).toHaveBeenCalledWith(
      expect.objectContaining({
        findingIds: ["F-001"],
      }),
    );
  });

  it("disables the submit button while loading", () => {
    setupUseChatMock(true);
    renderCouncilView();

    expect(
      screen.getByRole("button", { name: /Running/i }),
    ).toBeDisabled();
  });

  it("shows an error message when sendCouncilRequest rejects", async () => {
    const user = userEvent.setup();
    mockSendCouncilRequest.mockRejectedValue(new Error("Network timeout"));
    renderCouncilView();

    fireEvent.change(screen.getByRole("textbox"), {
      target: { value: "Any point" },
    });
    await user.click(screen.getByRole("button", { name: /Run council/i }));

    expect(await screen.findByText(/Network timeout/i)).toBeInTheDocument();
  });
});

describe("CouncilView — back navigation", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    setupUseChatMock();
  });

  it("calls onBack when the back button is clicked", async () => {
    const user = userEvent.setup();
    const onBack = vi.fn();
    renderCouncilView({ onBack });

    await user.click(
      screen.getByRole("button", { name: /Back to Analysis/i }),
    );

    expect(onBack).toHaveBeenCalledOnce();
  });
});

describe("CouncilView — council note rendering", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    setupUseChatMock();
  });

  it("shows the advisory empty state when no council note exists", () => {
    renderCouncilView({ councilNote: null });
    // The advisory panel shows a placeholder (from i18n: councilAdvisoryEmpty)
    expect(
      screen.getByText(/Run a council deliberation/i),
    ).toBeInTheDocument();
  });

  it("renders the council summary when a note is provided", () => {
    renderCouncilView({ councilNote: demoCouncilNote });
    expect(
      screen.getByText(/deliberate access-development activity/i),
    ).toBeInTheDocument();
  });

  it("renders the debate question in the advisory panel", () => {
    renderCouncilView({ councilNote: demoCouncilNote });
    expect(
      screen.getByText(/Is this access development or opportunistic intrusion/i),
    ).toBeInTheDocument();
  });

  it("renders the Summary tab as active by default", () => {
    renderCouncilView({ councilNote: demoCouncilNote });
    expect(
      screen.getByRole("button", { name: /^Summary$/i }),
    ).toHaveAttribute("aria-pressed", "true");
  });

  it("renders key agreements in the summary panel", () => {
    renderCouncilView({ councilNote: demoCouncilNote });
    expect(
      screen.getByText(/Both analysts agree credential theft is targeted/i),
    ).toBeInTheDocument();
  });

  it("renders the final recommendation in the summary panel", () => {
    renderCouncilView({ councilNote: demoCouncilNote });
    expect(
      screen.getByText(/Escalate attribution efforts/i),
    ).toBeInTheDocument();
  });

  it("renders rounds completed badge when council note exists", () => {
    renderCouncilView({ councilNote: demoCouncilNote });
    expect(screen.getByText(/1 round/i)).toBeInTheDocument();
  });

  it("shows 'no disagreements' message when key_disagreements is ['None']", () => {
    renderCouncilView({ councilNote: demoCouncilNote });
    // i18n key councilNoDisagreements = "No disagreements recorded."
    expect(screen.getByText(/No disagreements recorded/i)).toBeInTheDocument();
  });

  it("switches to a participant view on tab click", async () => {
    const user = userEvent.setup();
    renderCouncilView({ councilNote: demoCouncilNote });

    // "US Strategic Analyst" shortened to "US Analyst"
    const usTab = screen.getByRole("button", { name: "US Analyst" });
    await user.click(usTab);

    expect(usTab).toHaveAttribute("aria-pressed", "true");
    expect(screen.getByText("Assessment")).toBeInTheDocument();
    expect(screen.queryByText(/## Assessment/i)).not.toBeInTheDocument();
    expect(
      screen.getByText(/State-sponsored access development/i),
    ).toBeInTheDocument();
  });

  it("expands the full debate transcript on toggle", async () => {
    const user = userEvent.setup();
    renderCouncilView({ councilNote: demoCouncilNote });

    await user.click(
      screen.getByRole("button", { name: /Show full debate/i }),
    );

    expect(screen.getByRole("button", { name: /Hide full debate/i })).toBeInTheDocument();
  });

  it("renders the download PDF button when council note exists", () => {
    renderCouncilView({ councilNote: demoCouncilNote });
    expect(
      screen.getByRole("button", { name: /Download.*PDF/i }),
    ).toBeInTheDocument();
  });
});

describe("CouncilView — help modal", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    setupUseChatMock();
  });

  it("opens the help modal when the help button is clicked", async () => {
    const user = userEvent.setup();
    renderCouncilView();

    await user.click(screen.getByRole("button", { name: /Council guide/i }));

    // The help modal renders a heading "The Council" — find it by heading role
    expect(
      screen.getByRole("heading", { name: /The Council/i }),
    ).toBeInTheDocument();
  });

  it("closes the help modal when the close button is clicked", async () => {
    const user = userEvent.setup();
    renderCouncilView();

    await user.click(screen.getByRole("button", { name: /Council guide/i }));
    await user.click(screen.getByRole("button", { name: /close/i }));

    expect(
      screen.queryByRole("heading", { name: /The Council/i }),
    ).not.toBeInTheDocument();
  });
});
