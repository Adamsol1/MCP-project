import { useState, useMemo } from "react";
import { pdf } from "@react-pdf/renderer";
import { HelpModal, HelpButton } from "../HelpModal/HelpModal";
import type {
  AnalysisResponse,
  AssertionConfidence,
  ConfidenceTier,
  PerspectiveAssertion,
  ProcessingFinding,
} from "../../types/analysis";
import CollectionCoverageView from "../CollectionCoverageView/CollectionCoverageView";
import AnalysisReportPDF from "./AnalysisReportPDF";
import ReviewFeedbackPDF from "./ReviewFeedbackPDF";
import type { PhaseReviewItem } from "../../types/conversation";
import type { CouncilNote } from "../../types/analysis";
import { useWorkspace } from "../../contexts/WorkspaceContext/WorkspaceContext";

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------

const PRIORITY_DATA_KEYS = ["attack_ids", "entities", "locations"];
const LABEL_MAP: Record<string, string> = {
  iocs: "IOCs",
  kb_refs: "KB refs",
  attack_ids: "ATT&CK",
  source_refs: "Sources",
  entities: "Entities",
  timestamps: "Timestamps",
  locations: "Locations",
  domains: "Domains",
  ip_addresses: "IPs",
  urls: "URLs",
};

const ASSERTION_TIER_STYLES: Record<
  ConfidenceTier,
  { bg: string; text: string; border: string; label: string }
> = {
  low: {
    bg: "bg-error-subtle",
    text: "text-error-text",
    border: "border-error/30",
    label: "Low",
  },
  moderate: {
    bg: "bg-warning-subtle",
    text: "text-warning-text",
    border: "border-warning/30",
    label: "Moderate",
  },
  high: {
    bg: "bg-success-subtle",
    text: "text-success-text",
    border: "border-success/30",
    label: "High",
  },
  assessed: {
    bg: "bg-success-subtle",
    text: "text-success-text",
    border: "border-success/30",
    label: "Assessed",
  },
};

// ---------------------------------------------------------------------------
// Helpers — display formatting
// ---------------------------------------------------------------------------

function formatPerspectiveLabel(key: string) {
  if (key === "neutral") return "Global";
  if (key === "us" || key === "eu") return key.toUpperCase();
  return key.charAt(0).toUpperCase() + key.slice(1);
}

function formatSupportingDataLabel(key: string) {
  return key.replace(/_/g, " ");
}

function formatSourceLabel(source: string) {
  return source.replace(/_/g, " ");
}

function getConfidenceColor(confidence: number) {
  if (confidence >= 75) return "bg-success";
  if (confidence >= 50) return "bg-warning";
  return "bg-error";
}

function getConfidenceTextColor(confidence: number) {
  if (confidence >= 75) return "text-success";
  if (confidence >= 50) return "text-warning";
  return "text-error";
}

function getConfidenceTierLabel(confidence: number): string {
  if (confidence >= 90) return "Assessed";
  if (confidence >= 70) return "High";
  if (confidence >= 40) return "Moderate";
  return "Low";
}

function deriveTitleFromSummary(summary: string): string {
  // Take the first sentence of the AI-generated summary as a title fallback
  const firstSentence = summary.split(/[.!?]/)[0]?.trim() ?? "";
  if (firstSentence.length <= 80) return firstSentence;
  // Otherwise take first 8 words
  return firstSentence.split(/\s+/).slice(0, 8).join(" ");
}

function getAnalysisHeading(
  analysisTitle: string,
  summary: string,
  conversationTitle: string | undefined,
  findings: ProcessingFinding[],
) {
  if (analysisTitle?.trim()) return analysisTitle.trim();
  // Derive from the AI-generated summary so we always show analytical language
  if (summary?.trim()) return deriveTitleFromSummary(summary);
  const trimmedTitle = conversationTitle?.trim();
  if (trimmedTitle && trimmedTitle !== "New conversation") return trimmedTitle;
  return findings[0]?.title ?? "Analysis Assessment";
}

function getSupportingDataSummary(data: Record<string, string[]>) {
  return Object.entries(data)
    .filter(
      ([key, values]) => values.length > 0 && !PRIORITY_DATA_KEYS.includes(key),
    )
    .map(([key, values]) => `${values.length} ${LABEL_MAP[key] || key}`)
    .join(" · ");
}

// ---------------------------------------------------------------------------
// Helpers — stat computation
// ---------------------------------------------------------------------------

function getAverageConfidence(findings: ProcessingFinding[]) {
  if (findings.length === 0) return 0;
  const total = findings.reduce((sum, f) => sum + f.confidence, 0);
  return Math.round(total / findings.length);
}

function getTimelineSpan(findings: ProcessingFinding[]) {
  const allTimestamps = findings
    .flatMap((f) => f.supporting_data["timestamps"] ?? [])
    .map((t) => new Date(t).getTime())
    .filter((t) => !isNaN(t));
  if (allTimestamps.length < 2) return null;
  const min = Math.min(...allTimestamps);
  const max = Math.max(...allTimestamps);
  const diffDays = Math.round((max - min) / (1000 * 60 * 60 * 24));
  if (diffDays === 0) return "< 1 day";
  if (diffDays === 1) return "1 day";
  if (diffDays > 365) return `${Math.round(diffDays / 365)} yr`;
  if (diffDays > 30) return `${Math.round(diffDays / 30)} mo`;
  return `${diffDays} days`;
}

function getAllSourceTypes(findings: ProcessingFinding[]): string[] {
  const types = new Set<string>();
  for (const finding of findings) {
    types.add(finding.source);
    for (const src of finding.supporting_data["sources"] ?? []) {
      types.add(src);
    }
  }
  return [...types].filter(Boolean);
}

// ---------------------------------------------------------------------------
// Sub-components — assertion confidence
// ---------------------------------------------------------------------------

function AssertionTierBadge({
  confidence,
}: {
  confidence: AssertionConfidence | null;
}) {
  if (!confidence) {
    return (
      <span className="inline-flex items-center rounded-full border border-border px-2 py-0.5 text-[10px] font-medium text-text-muted">
        —
      </span>
    );
  }
  const styles = ASSERTION_TIER_STYLES[confidence.tier];
  return (
    <span
      title={`Score: ${confidence.score.toFixed(2)} | Authority: ${confidence.authority.toFixed(2)} | Corroboration: ${confidence.corroboration.toFixed(2)} | Independence: ${confidence.independence.toFixed(2)}`}
      className={`inline-flex cursor-default items-center rounded-full border px-2 py-0.5 text-[10px] font-semibold uppercase tracking-widest ${styles.bg} ${styles.text} ${styles.border}`}
    >
      {styles.label}
    </span>
  );
}

function AssertionRow({
  assertion,
  allFindings,
}: {
  assertion: PerspectiveAssertion;
  allFindings: ProcessingFinding[];
}) {
  const conf = assertion.confidence;

  return (
    <div>
      <div className="flex items-start gap-3">
        <div className="mt-0.5 flex shrink-0 items-center gap-1.5 flex-wrap">
          <AssertionTierBadge confidence={conf} />
          {conf?.circular_flag && (
            <span className="text-[10px] font-medium text-warning-text">⚠</span>
          )}
          {assertion.supporting_finding_ids.length > 0 &&
            assertion.supporting_finding_ids.map((fid) => {
              const finding = allFindings.find((f) => f.id === fid);
              return (
                <span
                  key={fid}
                  title={finding?.title}
                  className="rounded border border-primary/30 bg-primary-subtle/20 px-1.5 py-0.5 text-[9px] font-mono text-primary/70"
                >
                  {fid}
                </span>
              );
            })}
        </div>
        <p className="flex-1 text-sm font-medium leading-6 text-text-primary">{assertion.assertion}</p>
      </div>

      {assertion.analysis && (
        <p className="mt-2 text-sm leading-6 text-text-secondary whitespace-pre-line">{assertion.analysis}</p>
      )}

    </div>
  );
}

// ---------------------------------------------------------------------------
// Props
// ---------------------------------------------------------------------------

interface AnalysisViewProps {
  data: AnalysisResponse;
  conversationTitle: string | undefined;
  onStartCouncil: () => void;
  timeframe?: string;
  reviewActivity?: PhaseReviewItem[];
  councilNote?: CouncilNote | null;
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export default function AnalysisView({
  data,
  conversationTitle,
  onStartCouncil,
  timeframe,
  reviewActivity = [],
}: AnalysisViewProps) {
  const { processing_result: processingResult, analysis_draft: analysis } =
    data;
  const findings = processingResult.findings;

  const computedTimelineSpan = useMemo(
    () => getTimelineSpan(findings),
    [findings],
  );
  const timelineSpan = timeframe?.trim() || computedTimelineSpan;
  const allSourceTypes = useMemo(() => getAllSourceTypes(findings), [findings]);
  const averageConfidence = getAverageConfidence(findings);
  const analysisHeading = getAnalysisHeading(
    analysis.title,
    analysis.summary,
    conversationTitle,
    findings,
  );

  const [isHelpOpen, setIsHelpOpen] = useState(false);

  const { collectionData } = useWorkspace();
  const totalCollectedItems = collectionData
    ? collectionData.source_summary.reduce((sum, s) => sum + s.count, 0)
    : findings.length;

  const orderedPerspectiveEntries = Object.keys(
    analysis.per_perspective_implications,
  )
    .sort((a, b) => a.localeCompare(b))
    .map((key) => [key, analysis.per_perspective_implications[key]] as const);

  async function handleDownloadPDF() {
    const blob = await pdf(
      <AnalysisReportPDF data={data} title={analysisHeading} />,
    ).toBlob();
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `${analysisHeading
      .slice(0, 60)
      .replace(/[^a-z0-9 ]/gi, "")
      .trim()
      .replace(/\s+/g, "_")}.pdf`;
    a.click();
    URL.revokeObjectURL(url);
  }

  async function handleDownloadFeedbackPDF() {
    const blob = await pdf(
      <ReviewFeedbackPDF
        reviewActivity={reviewActivity}
        reportTitle={analysisHeading}
      />,
    ).toBlob();
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `feedback_${analysisHeading
      .slice(0, 50)
      .replace(/[^a-z0-9 ]/gi, "")
      .trim()
      .replace(/\s+/g, "_")}.pdf`;
    a.click();
    URL.revokeObjectURL(url);
  }

  return (
    <>
      <div className="flex justify-end items-center gap-2 pb-2">
        <HelpButton onClick={() => setIsHelpOpen(true)} label="Analysis report guide" />
        <button
          onClick={handleDownloadFeedbackPDF}
          className="rounded-md border border-border px-3 py-1.5 text-xs font-semibold text-text-secondary transition-opacity hover:opacity-80"
        >
          Download Feedback
        </button>
        <button
          onClick={handleDownloadPDF}
          className="rounded-md bg-primary px-3 py-1.5 text-xs font-semibold text-text-inverse transition-opacity hover:opacity-80"
        >
          Download PDF
        </button>
      </div>
      <HelpModal
        isOpen={isHelpOpen}
        onClose={() => setIsHelpOpen(false)}
        title="Reading the Analysis Report"
        sections={[
          {
            heading: "What is this report?",
            body: "The Analysis Report is the final intelligence product synthesised from all collected and processed data. It brings together key judgments, recommended actions, and multi-perspective framing into a single structured document.",
          },
          {
            heading: "Key Judgments",
            body: "Key Judgments are the most important analytical conclusions drawn from the evidence. They represent the AI's highest-confidence assessments about the situation, ordered by significance.",
          },
          {
            heading: "Recommended Actions",
            body: "Recommended Actions are suggested next steps based on the intelligence picture. These are operationally oriented and directly tied to the key judgments.",
          },
          {
            heading: "Avg Confidence and confidence tiers",
            body: "Confidence is calculated per-finding based on the quality and corroboration of evidence. Low is below 40%, Moderate is 40–69%, High is 70–89%, and Assessed is 90%+. The average confidence shown in the stat strip reflects all findings in the report.",
          },
          {
            heading: "Evidence Docket",
            body: "The Evidence Docket lists every finding that went into the analysis. Click any finding to expand it and see the full evidence: core statement, why it matters, key indicators (ATT&CK IDs, entities, locations), and uncertainties.",
          },
          {
            heading: "Perspective Implications",
            body: "Perspective Implications show how the same intelligence picture is framed differently by each selected national or analytical perspective. Expand a perspective to see its specific assertions and confidence scores.",
          },
          {
            heading: "Information Gaps",
            body: "Information Gaps highlight areas where the evidence is insufficient to draw firm conclusions. These can be addressed by running additional collection on the highlighted topics.",
          },
        ]}
      />

      <div className="mx-auto max-w-4xl space-y-10 pb-12 pt-2">
        {/* ── Hero: document-style header ──────────────────────────────── */}
        <section className="space-y-4 px-5">
          <div>
            <h1 className="font-sans text-[2rem] font-bold leading-tight text-text-primary">
              {analysisHeading}
            </h1>
            <p className="mt-3 max-w-3xl text-sm leading-7 text-text-secondary">
              {analysis.summary}
            </p>
          </div>

          {/* Inline stat strip */}
          <div className="flex flex-wrap items-center gap-x-5 gap-y-2 border-y border-border/50 py-3 text-sm">
            <div className="flex items-center gap-2">
              <span className="text-[11px] uppercase tracking-widest text-text-muted">
                Findings
              </span>
              <span className="font-semibold text-text-primary">
                {findings.length}
              </span>
            </div>
            <span className="text-base font-bold text-text-secondary">·</span>
            <div className="flex items-center gap-2">
              <span className="text-[11px] uppercase tracking-widest text-text-muted">
                Avg Confidence
              </span>
              <span
                className={`font-semibold tabular-nums ${getConfidenceTextColor(averageConfidence)}`}
              >
                {averageConfidence}%
              </span>
              <span className="text-[11px] text-text-muted">
                {getConfidenceTierLabel(averageConfidence)}
              </span>
              <div className="h-1.5 w-10 overflow-hidden rounded-full bg-border/40">
                <div
                  className={`h-full rounded-full ${getConfidenceColor(averageConfidence)}`}
                  style={{ width: `${averageConfidence}%` }}
                />
              </div>
            </div>
            {allSourceTypes.length > 0 && (
              <>
                <span className="text-base font-bold text-text-secondary">·</span>
                <div className="flex items-center gap-2">
                  <span className="text-[11px] uppercase tracking-widest text-text-muted">
                    Sources
                  </span>
                  <span className="font-semibold text-text-primary">
                    {totalCollectedItems} items across {allSourceTypes.length}{" "}
                    {allSourceTypes.length === 1 ? "source" : "sources"}
                  </span>
                </div>
              </>
            )}
            {timelineSpan && (
              <>
                <span className="text-base font-bold text-text-secondary">·</span>
                <div className="flex items-center gap-2">
                  <span className="text-[11px] uppercase tracking-widest text-text-muted">
                    Timeline
                  </span>
                  <span className="font-semibold text-text-primary">
                    {timelineSpan}
                  </span>
                </div>
              </>
            )}
          </div>
        </section>

        {/* ── Collection Coverage ───────────────────────────────────────── */}
        {data.collection_coverage && (
          <CollectionCoverageView coverage={data.collection_coverage} />
        )}

        {/* ── Key Judgments + Recommended Actions (side-by-side) ───────── */}
        <section className="px-5">
          <div className="border-b border-border/50 pb-8 md:grid md:grid-cols-[1fr_1px_1fr]">
            {/* Key Judgments */}
            <div className="md:pr-8">
              <p className="text-[11px] font-medium uppercase tracking-[0.14em] text-text-muted">
                Key Judgments
              </p>
              <ol className="mt-4 space-y-4">
                {analysis.key_judgments.map((judgment, index) => (
                  <li
                    key={judgment}
                    className="flex gap-3 text-sm leading-6 text-text-primary"
                  >
                    <span className="mt-0.5 inline-flex h-5 w-5 shrink-0 items-center justify-center rounded-full border border-border bg-surface-muted text-[10px] font-semibold text-text-secondary">
                      {index + 1}
                    </span>
                    <span>{judgment}</span>
                  </li>
                ))}
              </ol>
            </div>

            {/* Vertical divider */}
            <div className="hidden md:block bg-border/50 my-2" />

            {/* Recommended Actions */}
            <div className="mt-8 md:mt-0 md:pl-8">
              <p className="text-[11px] font-medium uppercase tracking-[0.14em] text-text-muted">
                Recommended Actions
              </p>
              <ul className="mt-4 space-y-3">
                {analysis.recommended_actions.map((action) => (
                  <li
                    key={action}
                    className="flex gap-2.5 text-sm leading-6 text-text-primary"
                  >
                    <span className="mt-[0.55em] h-1.5 w-1.5 shrink-0 rounded-full bg-primary" />
                    <span>{action}</span>
                  </li>
                ))}
              </ul>
            </div>
          </div>
        </section>

        {/* ── Evidence Docket ───────────────────────────────────────────── */}
        <section className="space-y-4">
          <div className="flex items-end justify-between gap-4 px-5">
            <div>
              <p className="text-[11px] font-medium uppercase tracking-[0.14em] text-text-muted">
                Intelligence Findings
              </p>
              <h2 className="mt-1 text-xl font-semibold text-text-primary">
                Evidence Docket
              </h2>
            </div>
            <span className="text-xs text-text-muted">
              {findings.length} findings
            </span>
          </div>

          <div className="divide-y divide-border/50 rounded-2xl border border-border overflow-hidden">
            {findings.map((finding) => (
              <FindingRow key={finding.id} finding={finding} />
            ))}
          </div>
        </section>

        {/* ── Perspective Implications ──────────────────────────────────── */}
        {orderedPerspectiveEntries.length > 0 && (
          <section className="space-y-4 px-5">
            <div>
              <p className="text-[11px] font-medium uppercase tracking-[0.14em] text-text-muted">
                Perspective Implications
              </p>
              <h2 className="mt-1 text-xl font-semibold text-text-primary">
                Framing by Perspective
              </h2>
            </div>

            <div className="divide-y divide-border/50">
              {orderedPerspectiveEntries.map(([key, implications]) => (
                <PerspectiveSection
                  key={key}
                  perspectiveKey={key}
                  implications={implications}
                  allFindings={findings}
                />
              ))}
            </div>
          </section>
        )}

        {/* ── Information Gaps ──────────────────────────────────────────── */}
        {analysis.information_gaps.length > 0 && (
          <section className="space-y-4 border-t border-border/50 pt-8 px-5">
            <p className="text-[11px] font-medium uppercase tracking-[0.14em] text-text-muted">
              Information Gaps
            </p>
            <ul className="space-y-2">
              {analysis.information_gaps.map((gap) => (
                <li
                  key={gap}
                  className="flex gap-2.5 text-sm leading-6 text-text-secondary"
                >
                  <span className="mt-[0.55em] h-1.5 w-1.5 shrink-0 rounded-full bg-warning" />
                  <span>{gap}</span>
                </li>
              ))}
            </ul>
          </section>
        )}

        {/* ── Start Council CTA ─────────────────────────────────────────── */}
        <div className="flex justify-end pt-2 px-5">
          <button
            type="button"
            onClick={onStartCouncil}
            className="rounded-lg border border-border bg-surface px-5 py-2 text-sm font-medium text-text-secondary transition-colors hover:border-primary hover:bg-primary-subtle hover:text-primary"
          >
            Go to Council
          </button>
        </div>
      </div>
    </>
  );
}

// ---------------------------------------------------------------------------
// FindingRow — expandable evidence docket entry
// ---------------------------------------------------------------------------

function FindingRow({ finding }: { finding: ProcessingFinding }) {
  const [open, setOpen] = useState(false);
  const sourceTypes = [
    finding.source,
    ...(finding.supporting_data["sources"] ?? []),
  ].filter((v, i, arr) => Boolean(v) && arr.indexOf(v) === i);

  return (
    <div className="bg-surface">
      {/* Summary row */}
      <button
        type="button"
        className="flex w-full items-center gap-4 px-5 py-4 text-left hover:bg-surface-muted/50 transition-colors"
        onClick={() => setOpen((v) => !v)}
        aria-expanded={open}
      >
        <div className="flex shrink-0 items-center gap-2">
          <span className="rounded-full border border-border bg-surface-muted px-2.5 py-0.5 text-[11px] font-medium uppercase tracking-[0.16em] text-text-muted">
            {finding.id}
          </span>
          {sourceTypes.slice(0, 1).map((src) => (
            <span
              key={src}
              className="rounded-full border border-border px-2.5 py-0.5 text-[11px] uppercase tracking-wide text-text-secondary"
            >
              {formatSourceLabel(src)}
            </span>
          ))}
        </div>

        <div className="min-w-0 flex-1">
          <h3 className="truncate text-sm font-semibold text-text-primary">
            {finding.title}
          </h3>
          <div className="mt-1 flex flex-wrap items-center gap-1.5">
            {finding.relevant_to.map((pirId) => (
              <span
                key={pirId}
                className="rounded bg-surface-muted px-1.5 py-0.5 text-[10px] uppercase tracking-wide text-text-secondary"
              >
                {pirId}
              </span>
            ))}
          </div>
        </div>

        <div className="flex shrink-0 items-center gap-3">
          <div className="flex items-center gap-2">
            <div className="h-1.5 w-14 overflow-hidden rounded-full bg-border/40">
              <div
                className={`h-full rounded-full ${getConfidenceColor(finding.confidence)}`}
                style={{ width: `${finding.confidence}%` }}
              />
            </div>
            <span
              className={`text-sm font-semibold tabular-nums ${getConfidenceTextColor(finding.confidence)}`}
            >
              {finding.confidence}%
            </span>
          </div>
          <svg
            width="12"
            height="12"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2.5"
            strokeLinecap="round"
            strokeLinejoin="round"
            className={`shrink-0 text-text-muted transition-transform duration-150 ${open ? "rotate-180" : ""}`}
          >
            <path d="M6 9l6 6 6-6" />
          </svg>
        </div>
      </button>

      {/* Expanded content */}
      {open && (
        <div className="px-5 py-5 space-y-5">
          {/* Finding */}
          <section>
            <p className="text-[11px] font-medium uppercase tracking-[0.12em] text-text-muted">
              Finding
            </p>
            <p className="mt-2 text-sm leading-7 text-text-primary">
              {finding.finding}
            </p>
          </section>

          {/* Why it matters */}
          <section className="border-l-[3px] border-l-primary pl-4">
            <p className="text-[11px] font-medium uppercase tracking-[0.12em] text-primary">
              Why it matters
            </p>
            <p className="mt-1.5 text-sm leading-7 italic text-text-secondary">
              {finding.why_it_matters}
            </p>
          </section>

          {/* Evidence summary */}
          <section className="border-t border-border/50 pt-4">
            <p className="text-[11px] font-medium uppercase tracking-[0.12em] text-text-muted">
              Evidence Summary
            </p>
            <p className="mt-2 text-sm leading-6 text-text-primary">
              {finding.evidence_summary}
            </p>
          </section>

          {/* Key indicators */}
          {PRIORITY_DATA_KEYS.some(
            (k) => (finding.supporting_data[k]?.length ?? 0) > 0,
          ) && (
            <section className="border-t border-border/50 pt-4">
              <p className="text-[11px] font-medium uppercase tracking-[0.12em] text-text-muted">
                Key Indicators
              </p>
              <div className="mt-3 space-y-3">
                {PRIORITY_DATA_KEYS.filter(
                  (key) => (finding.supporting_data[key]?.length ?? 0) > 0,
                ).map((key) => (
                  <div key={key}>
                    <p className="text-[10px] font-medium uppercase tracking-[0.12em] text-text-muted">
                      {LABEL_MAP[key] || key}
                    </p>
                    <div className="mt-1.5 flex flex-wrap gap-1.5">
                      {finding.supporting_data[key].map((value) => (
                        <span
                          key={`${key}-${value}`}
                          className="rounded border border-border bg-surface-muted px-2 py-0.5 text-xs text-text-secondary"
                        >
                          {value}
                        </span>
                      ))}
                    </div>
                  </div>
                ))}
              </div>
              {getSupportingDataSummary(finding.supporting_data) && (
                <p className="mt-3 text-xs text-text-muted">
                  {getSupportingDataSummary(finding.supporting_data)}
                </p>
              )}
            </section>
          )}

          {/* Uncertainties */}
          {finding.uncertainties.length > 0 && (
            <section className="border-t border-border/50 pt-4">
              <p className="text-[11px] font-medium uppercase tracking-[0.12em] text-text-muted">
                Uncertainties
              </p>
              <ul className="mt-2 space-y-1.5">
                {finding.uncertainties.map((u) => (
                  <li
                    key={u}
                    className="flex gap-2.5 text-sm leading-6 text-text-secondary"
                  >
                    <span className="mt-[0.55em] h-1.5 w-1.5 shrink-0 rounded-full bg-warning" />
                    <span>{u}</span>
                  </li>
                ))}
              </ul>
            </section>
          )}

          {/* Show all technical data */}
          <TechnicalDataAccordion supporting_data={finding.supporting_data} />
        </div>
      )}
    </div>
  );
}

function TechnicalDataAccordion({
  supporting_data,
}: {
  supporting_data: Record<string, string[]>;
}) {
  const [open, setOpen] = useState(false);
  const hasData = Object.values(supporting_data).some((v) => v.length > 0);
  if (!hasData) return null;

  return (
    <div className="border-t border-border/50 pt-3">
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        className="text-xs font-medium text-text-muted hover:text-text-secondary transition-colors"
      >
        {open ? "Hide" : "Show"} all technical data
      </button>
      {open && (
        <div className="mt-3 grid gap-3 md:grid-cols-2">
          {Object.entries(supporting_data)
            .filter(([, values]) => values.length > 0)
            .map(([key, values]) => (
              <div key={key}>
                <p className="text-[10px] font-medium uppercase tracking-[0.12em] text-text-muted">
                  {formatSupportingDataLabel(key)}
                </p>
                <div className="mt-1.5 flex flex-wrap gap-1">
                  {values.map((value) => (
                    <span
                      key={`${key}-${value}`}
                      className="rounded border border-border bg-surface px-1.5 py-0.5 text-[11px] text-text-secondary"
                    >
                      {value}
                    </span>
                  ))}
                </div>
              </div>
            ))}
        </div>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// PerspectiveSection — document-style collapsible, no box wrapper
// ---------------------------------------------------------------------------

function PerspectiveSection({
  perspectiveKey,
  implications,
  allFindings,
}: {
  perspectiveKey: string;
  implications: PerspectiveAssertion[];
  allFindings: ProcessingFinding[];
}) {
  const [open, setOpen] = useState(false);
  const firstAssertion = implications[0] ?? null;

  return (
    <div className="py-2">
      {/* Clickable header row */}
      <button
        type="button"
        className="flex w-full items-center gap-4 py-3 text-left group"
        onClick={() => setOpen((v) => !v)}
        aria-expanded={open}
      >
        <h3 className="text-sm font-semibold uppercase tracking-[0.12em] text-text-primary">
          {formatPerspectiveLabel(perspectiveKey)}
        </h3>
        <AssertionTierBadge confidence={firstAssertion?.confidence ?? null} />
        <svg
          width="12"
          height="12"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="2.5"
          strokeLinecap="round"
          strokeLinejoin="round"
          className={`ml-auto shrink-0 text-text-muted transition-transform duration-150 ${open ? "rotate-180" : ""}`}
        >
          <path d="M6 9l6 6 6-6" />
        </svg>
      </button>

      {/* Collapsed preview */}
      {!open && firstAssertion && (
        <div className="relative pb-5 overflow-hidden">
          <p className="text-sm leading-6 text-text-secondary line-clamp-3">
            {firstAssertion.assertion}
          </p>
          <div className="pointer-events-none absolute bottom-0 left-0 right-0 h-10 bg-linear-to-t from-surface to-transparent" />
        </div>
      )}

      {/* Expanded assertions — flat, separated by border-b, labeled */}
      {open && (
        <div className="mb-4">
          {implications.map((assertion, idx) => (
            <div key={idx} className="border-t border-border/40 py-3">
              <p className="mb-1.5 text-[10px] font-medium uppercase tracking-[0.14em] text-text-muted">
                Assertion {idx + 1}
              </p>
              <AssertionRow assertion={assertion} allFindings={allFindings} />
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
