import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, it, expect, vi } from "vitest";
import { axe } from "vitest-axe";
import CollectionCoverageView from "./CollectionCoverageView";
import type { CollectionCoverageResult } from "../../types/analysis";

// ---------------------------------------------------------------------------
// Fixtures
// ---------------------------------------------------------------------------

const highCoverage: CollectionCoverageResult = {
  aggregate_tier: "high",
  aggregate_score: 0.82,
  summary: "Strong coverage across all intelligence requirements.",
  per_pir: [
    {
      pir_index: 0,
      pir_question: "What are the primary threat vectors?",
      priority: "high",
      tier: "high",
      score: 0.85,
      finding_count: 3,
      source_types: ["osint", "network_telemetry"],
      has_gap_flag: false,
      rationale: "Multiple corroborating sources confirm the identified vectors.",
      findings: [
        { id: "F-001", title: "Initial access via phishing", source: "osint" },
        { id: "F-002", title: "Credential theft activity", source: "network_telemetry" },
      ],
    },
  ],
};

const lowCoverage: CollectionCoverageResult = {
  aggregate_tier: "low",
  aggregate_score: 0.22,
  summary: "Coverage is insufficient for reliable assessment.",
  per_pir: [
    {
      pir_index: 0,
      pir_question: "Who are the suspected threat actors?",
      priority: "high",
      tier: "low",
      score: 0.2,
      finding_count: 1,
      source_types: ["osint"],
      has_gap_flag: true,
      rationale: "Only a single unverified source addresses this requirement.",
      findings: [],
    },
  ],
};

const moderateCoverage: CollectionCoverageResult = {
  aggregate_tier: "moderate",
  aggregate_score: 0.55,
  summary: "Moderate coverage with some gaps remaining.",
  per_pir: [
    {
      pir_index: 0,
      pir_question: "What infrastructure is at risk?",
      priority: "medium",
      tier: "moderate",
      score: 0.55,
      finding_count: 2,
      source_types: ["web_search"],
      has_gap_flag: false,
      rationale: "Partial evidence collected from open sources.",
      findings: [],
    },
  ],
};

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

describe("CollectionCoverageView", () => {
  it("renders the 'Collection Coverage' heading", () => {
    render(<CollectionCoverageView coverage={highCoverage} />);
    expect(screen.getByText(/Collection Coverage/i)).toBeInTheDocument();
  });

  it("renders the aggregate summary text", () => {
    render(<CollectionCoverageView coverage={highCoverage} />);
    expect(
      screen.getByText(/Strong coverage across all intelligence requirements/i),
    ).toBeInTheDocument();
  });

  it("renders the PIR count in the header", () => {
    render(<CollectionCoverageView coverage={highCoverage} />);
    expect(screen.getByText(/1 PIR assessed/i)).toBeInTheDocument();
  });

  it("uses the plural 'PIRs' label when count > 1", () => {
    const twoPerPir: CollectionCoverageResult = {
      ...highCoverage,
      per_pir: [
        ...highCoverage.per_pir,
        { ...highCoverage.per_pir[0], pir_index: 1, pir_question: "Second requirement?" },
      ],
    };
    render(<CollectionCoverageView coverage={twoPerPir} />);
    expect(screen.getByText(/2 PIRs assessed/i)).toBeInTheDocument();
  });

  it("renders PIR questions in collapsed rows", () => {
    render(<CollectionCoverageView coverage={highCoverage} />);
    expect(
      screen.getByText(/What are the primary threat vectors/i),
    ).toBeInTheDocument();
  });

  it("expands a PIR row on click to show rationale and findings", async () => {
    const user = userEvent.setup();
    render(<CollectionCoverageView coverage={highCoverage} />);

    await user.click(
      screen.getByRole("button", { name: /What are the primary threat vectors/i }),
    );

    expect(
      screen.getByText(/Multiple corroborating sources confirm/i),
    ).toBeInTheDocument();
    expect(screen.getByText(/Contributing Findings/i)).toBeInTheDocument();
    expect(screen.getByText("F-001")).toBeInTheDocument();
    expect(screen.getByText("F-002")).toBeInTheDocument();
  });

  it("collapses the PIR row again on a second click", async () => {
    const user = userEvent.setup();
    render(<CollectionCoverageView coverage={highCoverage} />);

    const rowBtn = screen.getByRole("button", {
      name: /What are the primary threat vectors/i,
    });
    await user.click(rowBtn);
    expect(screen.getByText(/Contributing Findings/i)).toBeInTheDocument();

    await user.click(rowBtn);
    expect(screen.queryByText(/Contributing Findings/i)).not.toBeInTheDocument();
  });

  it("shows finding count and source types when row is expanded", async () => {
    const user = userEvent.setup();
    render(<CollectionCoverageView coverage={highCoverage} />);

    await user.click(
      screen.getByRole("button", { name: /What are the primary threat vectors/i }),
    );

    // finding_count is 3 — rendered inside a <span> alongside surrounding text
    expect(
      screen.getByText((_, el) =>
        el?.tagName === "SPAN" && /^3$/.test(el.textContent?.trim() ?? ""),
      ),
    ).toBeInTheDocument();
    // source_types has 2 entries — count and label text live in sibling DOM nodes
    expect(
      screen.getAllByText((_, el) =>
        Boolean(el?.textContent?.includes("2") && el.textContent.includes("source type")),
      ).length,
    ).toBeGreaterThan(0);
    expect(screen.getByText(/osint, network_telemetry/i)).toBeInTheDocument();
  });

  it("shows gap flag warning in an expanded row when has_gap_flag is true", async () => {
    const user = userEvent.setup();
    render(<CollectionCoverageView coverage={lowCoverage} />);

    await user.click(
      screen.getByRole("button", { name: /Who are the suspected threat actors/i }),
    );

    expect(screen.getByText(/Gap flagged/i)).toBeInTheDocument();
  });

  it("does not show gap flag warning when has_gap_flag is false", async () => {
    const user = userEvent.setup();
    render(<CollectionCoverageView coverage={highCoverage} />);

    await user.click(
      screen.getByRole("button", { name: /What are the primary threat vectors/i }),
    );

    expect(screen.queryByText(/Gap flagged/i)).not.toBeInTheDocument();
  });

  it("shows inline low-coverage indicator in collapsed row when tier is low", () => {
    render(<CollectionCoverageView coverage={lowCoverage} />);
    // The per-PIR row shows the inline indicator; the header also shows "Low coverage"
    // so there will be multiple matches — assert at least one exists.
    expect(screen.getAllByText(/Low coverage/i).length).toBeGreaterThan(0);
  });

  it("shows inline moderate-coverage indicator in collapsed row when tier is moderate", () => {
    render(<CollectionCoverageView coverage={moderateCoverage} />);
    expect(screen.getAllByText(/Moderate coverage/i).length).toBeGreaterThan(0);
  });

  it("does NOT show 'Back to Collection' button for high aggregate tier", () => {
    const onBack = vi.fn();
    render(
      <CollectionCoverageView
        coverage={highCoverage}
        onGoBackToCollection={onBack}
      />,
    );
    expect(
      screen.queryByRole("button", { name: /Back to Collection/i }),
    ).not.toBeInTheDocument();
  });

  it("shows 'Back to Collection' button only when aggregate tier is low", () => {
    const onBack = vi.fn();
    render(
      <CollectionCoverageView
        coverage={lowCoverage}
        onGoBackToCollection={onBack}
      />,
    );
    expect(
      screen.getByRole("button", { name: /Back to Collection/i }),
    ).toBeInTheDocument();
  });

  it("calls onGoBackToCollection when 'Back to Collection' is clicked", async () => {
    const user = userEvent.setup();
    const onBack = vi.fn();
    render(
      <CollectionCoverageView
        coverage={lowCoverage}
        onGoBackToCollection={onBack}
      />,
    );

    await user.click(screen.getByRole("button", { name: /Back to Collection/i }));

    expect(onBack).toHaveBeenCalledOnce();
  });

  it("does not render 'Back to Collection' when callback is not provided even for low tier", () => {
    render(<CollectionCoverageView coverage={lowCoverage} />);
    expect(
      screen.queryByRole("button", { name: /Back to Collection/i }),
    ).not.toBeInTheDocument();
  });

  it("renders no PIR breakdown section when per_pir is empty", () => {
    const empty: CollectionCoverageResult = {
      aggregate_tier: "high",
      aggregate_score: 0.9,
      summary: "All requirements fully addressed.",
      per_pir: [],
    };
    render(<CollectionCoverageView coverage={empty} />);
    expect(screen.queryByText(/Per-PIR Breakdown/i)).not.toBeInTheDocument();
  });
});

describe("CollectionCoverageView — accessibility (WCAG 2.1 AA)", () => {
  it("has no violations for high coverage", async () => {
    const { container } = render(<CollectionCoverageView coverage={highCoverage} />);
    expect(await axe(container)).toHaveNoViolations();
  });

  it("has no violations for low coverage", async () => {
    const { container } = render(<CollectionCoverageView coverage={lowCoverage} />);
    expect(await axe(container)).toHaveNoViolations();
  });

  it("has no violations for moderate coverage", async () => {
    const { container } = render(<CollectionCoverageView coverage={moderateCoverage} />);
    expect(await axe(container)).toHaveNoViolations();
  });
});
