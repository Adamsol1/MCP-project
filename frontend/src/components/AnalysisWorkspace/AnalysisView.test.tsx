import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, it, expect, vi, beforeEach } from "vitest";
import type { ReactNode } from "react";
import AnalysisView from "./AnalysisView";
import { SettingsProvider } from "../../contexts/SettingsContext/SettingsContext";
import { WorkspaceProvider } from "../../contexts/WorkspaceContext/WorkspaceContext";
import type { AnalysisResponse } from "../../types/analysis";

// @react-pdf/renderer does not work in jsdom — pdf().toBlob() is browser-only.
vi.mock("@react-pdf/renderer", () => ({
  pdf: vi.fn(() => ({ toBlob: vi.fn().mockResolvedValue(new Blob()) })),
  Document: ({ children }: { children: ReactNode }) => <>{children}</>,
  Page: ({ children }: { children: ReactNode }) => <>{children}</>,
  Text: ({ children }: { children: ReactNode }) => <>{children}</>,
  View: ({ children }: { children: ReactNode }) => <>{children}</>,
  StyleSheet: { create: (s: unknown) => s },
}));

// ---------------------------------------------------------------------------
// Fixtures
// ---------------------------------------------------------------------------

const demoData: AnalysisResponse = {
  processing_result: {
    findings: [
      {
        id: "F-001",
        title: "Credential-access surge against remote administration",
        finding: "Telemetry shows a credential-access surge over a 48-hour window.",
        evidence_summary: "Auth failures followed by successful logins.",
        source: "network_telemetry",
        confidence: 82,
        relevant_to: ["PIR-1"],
        supporting_data: {
          attack_ids: ["T1078", "T1110"],
          entities: ["vpn.demo.net"],
          locations: ["Oslo", "Bergen"],
          iocs: ["bad-user-agent"],
          timestamps: ["2026-01-10T08:00:00Z", "2026-01-11T09:00:00Z"],
        },
        why_it_matters: "Privileged access into telecom workflows may be established.",
        uncertainties: ["Credential source remains unknown."],
        computed_confidence: null,
      },
      {
        id: "F-002",
        title: "Lookalike domains staged for phishing",
        finding: "Recently registered lookalike domains appear staged for phishing.",
        evidence_summary: "Passive DNS confirms Nordic brand impersonation.",
        source: "osint",
        confidence: 58,
        relevant_to: ["PIR-1", "PIR-2"],
        supporting_data: {
          domains: ["demo-support.net"],
          urls: ["https://demo-support.net/auth"],
        },
        why_it_matters: "This supports a parallel credential-theft path.",
        uncertainties: ["Delivery method is unconfirmed."],
        computed_confidence: null,
      },
    ],
    gaps: ["Attribution unresolved.", "Victimology incomplete."],
  },
  analysis_draft: {
    title: "Demo Telecom Access-Development Assessment",
    summary: "Analysis indicates a likely access-development campaign against Nordic telecom.",
    key_judgments: [
      "Credential-access activity is deliberate and targeted.",
      "Phishing infrastructure supports a parallel intrusion path.",
    ],
    recommended_actions: [
      "Review privileged accounts for anomalous logins.",
      "Correlate phishing domains with existing threat intelligence.",
    ],
    per_perspective_implications: {
      us: [
        {
          assertion: "US analysts should monitor shared vendor-access pathways.",
          supporting_finding_ids: ["F-001"],
          source_types: ["network_telemetry"],
          confidence: {
            tier: "high",
            score: 0.78,
            authority: 0.8,
            corroboration: 0.75,
            independence: 0.7,
            circular_flag: false,
          },
        },
      ],
    },
    information_gaps: ["Attribution remains unclear.", "Victimology is incomplete."],
  },
  latest_council_note: null,
  collection_coverage: null,
  data_source: "session",
};

function createWrapper() {
  return function Wrapper({ children }: { children: ReactNode }) {
    return (
      <SettingsProvider>
        <WorkspaceProvider>{children}</WorkspaceProvider>
      </SettingsProvider>
    );
  };
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function renderAnalysisView(
  overrides: Partial<React.ComponentProps<typeof AnalysisView>> = {},
) {
  return render(
    <AnalysisView
      data={demoData}
      conversationTitle="Test Conversation"
      onStartCouncil={vi.fn()}
      {...overrides}
    />,
    { wrapper: createWrapper() },
  );
}

// ---------------------------------------------------------------------------
// Rendering
// ---------------------------------------------------------------------------

describe("AnalysisView — rendering", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    // URL.createObjectURL is not available in jsdom
    vi.spyOn(URL, "createObjectURL").mockReturnValue("blob:mock");
    vi.spyOn(URL, "revokeObjectURL").mockReturnValue(undefined);
  });

  it("renders the analysis title as an h1", async () => {
    renderAnalysisView();
    expect(
      await screen.findByRole("heading", {
        name: /Demo Telecom Access-Development Assessment/i,
        level: 1,
      }),
    ).toBeInTheDocument();
  });

  it("renders the analysis summary text", () => {
    renderAnalysisView();
    expect(
      screen.getByText(/likely access-development campaign against Nordic telecom/i),
    ).toBeInTheDocument();
  });

  it("renders all key judgments", () => {
    renderAnalysisView();
    expect(
      screen.getByText(/Credential-access activity is deliberate and targeted/i),
    ).toBeInTheDocument();
    expect(
      screen.getByText(/Phishing infrastructure supports a parallel intrusion path/i),
    ).toBeInTheDocument();
  });

  it("renders all recommended actions", () => {
    renderAnalysisView();
    expect(
      screen.getByText(/Review privileged accounts for anomalous logins/i),
    ).toBeInTheDocument();
    expect(
      screen.getByText(/Correlate phishing domains with existing threat intelligence/i),
    ).toBeInTheDocument();
  });

  it("renders information gaps", () => {
    renderAnalysisView();
    expect(screen.getByText(/Attribution remains unclear/i)).toBeInTheDocument();
    expect(screen.getByText(/Victimology is incomplete/i)).toBeInTheDocument();
  });

  it("shows the findings count and avg confidence in the stat strip", () => {
    renderAnalysisView();
    // Stat strip labels
    expect(screen.getByText("Findings")).toBeInTheDocument();
    // 2 findings — there may be many "2"s in the page so check allByText
    expect(screen.getAllByText("2").length).toBeGreaterThan(0);
    // avg confidence = (82+58)/2 = 70%
    expect(screen.getByText("70%")).toBeInTheDocument();
  });

  it("renders the computed timeline span from finding timestamps", () => {
    renderAnalysisView();
    // timestamps span 1 day
    expect(screen.getByText(/1 day/i)).toBeInTheDocument();
  });

  it("overrides computed timeline with explicit timeframe prop", () => {
    renderAnalysisView({ timeframe: "6 months" });
    expect(screen.getByText("6 months")).toBeInTheDocument();
  });

  it("renders finding IDs in the collapsed evidence docket rows", () => {
    renderAnalysisView();
    expect(screen.getAllByText("F-001").length).toBeGreaterThan(0);
    expect(screen.getAllByText("F-002").length).toBeGreaterThan(0);
  });

  it("renders finding confidence scores in the collapsed rows", () => {
    renderAnalysisView();
    expect(screen.getByText("82%")).toBeInTheDocument();
    expect(screen.getByText("58%")).toBeInTheDocument();
  });

  it("renders the Perspective Implications section", () => {
    renderAnalysisView();
    expect(screen.getByText(/Perspective Implications/i)).toBeInTheDocument();
    expect(screen.getByText(/Framing by Perspective/i)).toBeInTheDocument();
    // The US perspective section heading should appear (may share text with other elements)
    expect(screen.getAllByText("US").length).toBeGreaterThan(0);
  });

  it("derives heading from summary when title is empty", async () => {
    renderAnalysisView({
      data: {
        ...demoData,
        analysis_draft: { ...demoData.analysis_draft, title: "" },
      },
      conversationTitle: undefined,
    });
    // First sentence of summary becomes the title
    expect(
      await screen.findByRole("heading", {
        name: /Analysis indicates a likely access-development campaign against Nordic telecom/i,
        level: 1,
      }),
    ).toBeInTheDocument();
  });

  it("renders 'Go to Council' button", () => {
    renderAnalysisView();
    expect(
      screen.getByRole("button", { name: /Go to Council/i }),
    ).toBeInTheDocument();
  });
});

// ---------------------------------------------------------------------------
// Evidence docket interaction
// ---------------------------------------------------------------------------

describe("AnalysisView — finding row expansion", () => {
  beforeEach(() => {
    vi.spyOn(URL, "createObjectURL").mockReturnValue("blob:mock");
    vi.spyOn(URL, "revokeObjectURL").mockReturnValue(undefined);
  });

  it("expands a finding row on click to reveal the finding text", async () => {
    const user = userEvent.setup();
    renderAnalysisView();

    await user.click(
      screen.getByRole("button", {
        name: /Credential-access surge against remote administration/i,
      }),
    );

    expect(
      screen.getByText(/Telemetry shows a credential-access surge/i),
    ).toBeInTheDocument();
  });

  it("shows 'Why it matters' after expanding", async () => {
    const user = userEvent.setup();
    renderAnalysisView();

    await user.click(
      screen.getByRole("button", {
        name: /Credential-access surge against remote administration/i,
      }),
    );

    expect(
      screen.getByText(/Privileged access into telecom workflows/i),
    ).toBeInTheDocument();
  });

  it("shows uncertainties after expanding", async () => {
    const user = userEvent.setup();
    renderAnalysisView();

    await user.click(
      screen.getByRole("button", {
        name: /Credential-access surge against remote administration/i,
      }),
    );

    expect(screen.getByText(/Uncertainties/i)).toBeInTheDocument();
    expect(
      screen.getByText(/Credential source remains unknown/i),
    ).toBeInTheDocument();
  });

  it("shows ATT&CK and entity key indicators after expanding", async () => {
    const user = userEvent.setup();
    renderAnalysisView();

    await user.click(
      screen.getByRole("button", {
        name: /Credential-access surge against remote administration/i,
      }),
    );

    expect(screen.getByText("T1078")).toBeInTheDocument();
    expect(screen.getByText("vpn.demo.net")).toBeInTheDocument();
  });

  it("reveals technical data accordion inside expanded finding", async () => {
    const user = userEvent.setup();
    renderAnalysisView();

    await user.click(
      screen.getByRole("button", {
        name: /Credential-access surge against remote administration/i,
      }),
    );

    const showTechBtn = screen.getByRole("button", {
      name: /Show all technical data/i,
    });
    await user.click(showTechBtn);

    expect(
      screen.getByRole("button", { name: /Hide all technical data/i }),
    ).toBeInTheDocument();
  });

  it("collapses the finding row on second click", async () => {
    const user = userEvent.setup();
    renderAnalysisView();

    const rowBtn = screen.getByRole("button", {
      name: /Credential-access surge against remote administration/i,
    });
    await user.click(rowBtn);
    expect(
      screen.getByText(/Telemetry shows a credential-access surge/i),
    ).toBeInTheDocument();

    await user.click(rowBtn);
    expect(
      screen.queryByText(/Telemetry shows a credential-access surge/i),
    ).not.toBeInTheDocument();
  });
});

// ---------------------------------------------------------------------------
// Perspective section interaction
// ---------------------------------------------------------------------------

describe("AnalysisView — perspective section expansion", () => {
  beforeEach(() => {
    vi.spyOn(URL, "createObjectURL").mockReturnValue("blob:mock");
    vi.spyOn(URL, "revokeObjectURL").mockReturnValue(undefined);
  });

  it("expands a perspective section on click", async () => {
    const user = userEvent.setup();
    renderAnalysisView();

    // The PerspectiveSection button accessible name is "US High" (label + tier badge)
    await user.click(screen.getByRole("button", { name: /^US\b/i }));

    expect(
      screen.getByText(/US analysts should monitor shared vendor-access pathways/i),
    ).toBeInTheDocument();
  });

  it("shows the assertion badge label in expanded perspective", async () => {
    const user = userEvent.setup();
    renderAnalysisView();

    await user.click(screen.getByRole("button", { name: /^US\b/i }));

    expect(screen.getByText(/Assertion 1/i)).toBeInTheDocument();
  });

  it("collapses the perspective section on second click", async () => {
    const user = userEvent.setup();
    renderAnalysisView();

    const perspBtn = screen.getByRole("button", { name: /^US\b/i });

    // First click — expands; "Assertion 1" label only appears in the expanded body
    await user.click(perspBtn);
    expect(screen.getByText(/Assertion 1/i)).toBeInTheDocument();

    // Second click — collapses; the assertion label disappears
    await user.click(perspBtn);
    expect(screen.queryByText(/Assertion 1/i)).not.toBeInTheDocument();
  });
});

// ---------------------------------------------------------------------------
// Callbacks
// ---------------------------------------------------------------------------

describe("AnalysisView — Go to Council callback", () => {
  it("calls onStartCouncil when the button is clicked", async () => {
    const user = userEvent.setup();
    const onStartCouncil = vi.fn();
    renderAnalysisView({ onStartCouncil });

    await user.click(screen.getByRole("button", { name: /Go to Council/i }));

    expect(onStartCouncil).toHaveBeenCalledOnce();
  });
});

// ---------------------------------------------------------------------------
// Help modal
// ---------------------------------------------------------------------------

describe("AnalysisView — help modal", () => {
  it("opens the help modal when the help button is clicked", async () => {
    const user = userEvent.setup();
    renderAnalysisView();

    await user.click(
      screen.getByRole("button", { name: /Analysis report guide/i }),
    );

    expect(
      screen.getByText(/Reading the Analysis Report/i),
    ).toBeInTheDocument();
  });

  it("closes the help modal when the close button is clicked", async () => {
    const user = userEvent.setup();
    renderAnalysisView();

    await user.click(
      screen.getByRole("button", { name: /Analysis report guide/i }),
    );
    await user.click(screen.getByRole("button", { name: /close/i }));

    expect(
      screen.queryByText(/Reading the Analysis Report/i),
    ).not.toBeInTheDocument();
  });
});
