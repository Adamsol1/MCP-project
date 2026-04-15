import { useState, useMemo, type ReactNode } from "react";
import type {
  AnalysisDraftResponse,
  AssertionConfidence,
  ConfidenceTier,
  PerspectiveAssertion,
  ProcessingFinding,
} from "../../types/analysis";
import CollectionCoverageView from "../CollectionCoverageView/CollectionCoverageView";

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------

const PERSPECTIVE_ORDER = ["us", "norway", "china", "eu", "russia", "neutral"];

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
  low: { bg: "bg-error-subtle", text: "text-error-text", border: "border-error/30", label: "Low" },
  moderate: { bg: "bg-warning-subtle", text: "text-warning-text", border: "border-warning/30", label: "Moderate" },
  high: { bg: "bg-success-subtle", text: "text-success-text", border: "border-success/30", label: "High" },
  assessed: { bg: "bg-[#edf6f0]", text: "text-[#1a6640]", border: "border-[#1a6640]/20", label: "Assessed" },
};

// ---------------------------------------------------------------------------
// Helpers — display formatting
// ---------------------------------------------------------------------------

function formatPerspectiveLabel(key: string) {
  return key === "us" || key === "eu"
    ? key.toUpperCase()
    : key.charAt(0).toUpperCase() + key.slice(1);
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

function getAnalysisHeading(
  conversationTitle: string | undefined,
  findings: ProcessingFinding[],
) {
  const trimmedTitle = conversationTitle?.trim();
  if (trimmedTitle && trimmedTitle !== "New conversation") {
    return trimmedTitle;
  }
  return findings[0]?.title ?? "Analysis assessment";
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
  const total = findings.reduce((sum, finding) => sum + finding.confidence, 0);
  return Math.round(total / findings.length);
}

function getUniqueTechniques(findings: ProcessingFinding[]) {
  const all = findings.flatMap((f) => f.supporting_data["attack_ids"] ?? []);
  return [...new Set(all)];
}

function getSharedIndicatorCount(findings: ProcessingFinding[]) {
  const INDICATOR_KEYS = ["iocs", "domains", "ip_addresses", "urls"];
  const seen = new Map<string, number>();
  for (const finding of findings) {
    const findingValues = new Set<string>();
    for (const key of INDICATOR_KEYS) {
      for (const value of finding.supporting_data[key] ?? []) {
        findingValues.add(`${key}::${value}`);
      }
    }
    for (const v of findingValues) {
      seen.set(v, (seen.get(v) ?? 0) + 1);
    }
  }
  let shared = 0;
  for (const count of seen.values()) {
    if (count >= 2) shared++;
  }
  return shared;
}

function getTimelineSpan(findings: ProcessingFinding[]) {
  const allTimestamps = findings
    .flatMap((f) => f.supporting_data["timestamps"] ?? [])
    .map((t) => new Date(t).getTime())
    .filter((t) => !isNaN(t));
  if (allTimestamps.length < 2) return "—";
  const min = Math.min(...allTimestamps);
  const max = Math.max(...allTimestamps);
  const diffDays = Math.round((max - min) / (1000 * 60 * 60 * 24));
  if (diffDays === 0) return "< 1 day";
  if (diffDays === 1) return "1 day";
  return `${diffDays} days`;
}

function getUniqueSources(findings: ProcessingFinding[]) {
  return [...new Set(findings.map((f) => f.source))];
}

function getPirCoverage(findings: ProcessingFinding[]) {
  const coverage: Record<string, number> = {};
  for (const finding of findings) {
    for (const pir of finding.relevant_to) {
      coverage[pir] = (coverage[pir] ?? 0) + 1;
    }
  }
  return coverage;
}

// ---------------------------------------------------------------------------
// Sub-components — assertion confidence
// ---------------------------------------------------------------------------

function AssertionTierBadge({ confidence }: { confidence: AssertionConfidence | null }) {
  const [showScore, setShowScore] = useState(false);
  if (!confidence) return null;
  const styles = ASSERTION_TIER_STYLES[confidence.tier];
  return (
    <span
      title={`Score: ${confidence.score.toFixed(2)} | Authority: ${confidence.authority.toFixed(2)} | Corroboration: ${confidence.corroboration.toFixed(2)} | Independence: ${confidence.independence.toFixed(2)}`}
      onMouseEnter={() => setShowScore(true)}
      onMouseLeave={() => setShowScore(false)}
      className={`inline-flex cursor-default items-center rounded-full border px-2 py-0.5 text-[10px] font-semibold uppercase tracking-widest transition-all ${styles.bg} ${styles.text} ${styles.border}`}
    >
      {showScore ? confidence.score.toFixed(2) : styles.label}
    </span>
  );
}

function AssertionBreakdown({
  assertion,
  allFindings,
}: {
  assertion: PerspectiveAssertion;
  allFindings: ProcessingFinding[];
}) {
  const [expanded, setExpanded] = useState(false);
  const conf = assertion.confidence;

  return (
    <li className="rounded-[14px] border border-border bg-surface/60 px-3 py-2.5">
      <div className="flex items-start gap-2">
        <span className="mt-[0.55em] h-1.5 w-1.5 shrink-0 rounded-full bg-border" />
        <div className="flex-1 min-w-0">
          <div className="flex flex-wrap items-center gap-1.5 mb-1">
            <AssertionTierBadge confidence={conf} />
            {conf?.circular_flag && (
              <span className="text-[10px] font-medium text-warning-text">⚠ Circular</span>
            )}
          </div>
          <p className="text-sm leading-6 text-text-secondary">{assertion.assertion}</p>
        </div>
        {conf && (
          <button
            type="button"
            onClick={() => setExpanded((v) => !v)}
            className={`shrink-0 text-[10px] text-text-muted transition-transform ${expanded ? "rotate-90" : ""}`}
            aria-label="Toggle confidence breakdown"
          >
            ▶
          </button>
        )}
      </div>

      {expanded && conf && (
        <div className="mt-2 ml-3.5 space-y-2">
          <div className="grid grid-cols-3 gap-2">
            {(
              [
                ["Authority", conf.authority],
                ["Corroboration", conf.corroboration],
                ["Independence", conf.independence],
              ] as [string, number][]
            ).map(([label, value]) => (
              <div key={label}>
                <p className="text-[9px] font-medium uppercase tracking-widest text-text-muted">
                  {label}
                </p>
                <div className="mt-0.5 flex items-center gap-1">
                  <div className="h-1 flex-1 overflow-hidden rounded-full bg-border/40">
                    <div
                      className="h-full rounded-full bg-primary/60"
                      style={{ width: `${Math.round(value * 100)}%` }}
                    />
                  </div>
                  <span className="text-[9px] tabular-nums text-text-muted">
                    {value.toFixed(2)}
                  </span>
                </div>
              </div>
            ))}
          </div>

          {assertion.source_types.length > 0 && (
            <div className="flex flex-wrap gap-1">
              {assertion.source_types.map((st) => (
                <span
                  key={st}
                  className="rounded-full border border-border bg-surface px-1.5 py-0.5 text-[9px] text-text-muted"
                >
                  {st.replace(/_/g, " ")}
                </span>
              ))}
            </div>
          )}

          {assertion.supporting_finding_ids.length > 0 && (
            <div className="flex flex-wrap gap-1">
              {assertion.supporting_finding_ids.map((fid) => {
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
          )}
        </div>
      )}
    </li>
  );
}

// ---------------------------------------------------------------------------
// Props
// ---------------------------------------------------------------------------

interface AnalysisViewProps {
  data: AnalysisDraftResponse;
  conversationTitle: string | undefined;
  onStartCouncil: () => void;
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export default function AnalysisView({
  data,
  conversationTitle,
  onStartCouncil,
}: AnalysisViewProps) {
  const { processing_result: processingResult, analysis_draft: analysisDraft } = data;
  const findings = processingResult.findings;

  const uniqueTechniques = useMemo(() => getUniqueTechniques(findings), [findings]);
  const sharedIndicatorCount = useMemo(() => getSharedIndicatorCount(findings), [findings]);
  const timelineSpan = useMemo(() => getTimelineSpan(findings), [findings]);
  const uniqueSources = useMemo(() => getUniqueSources(findings), [findings]);
  const pirCoverage = useMemo(() => getPirCoverage(findings), [findings]);

  const averageConfidence = getAverageConfidence(findings);
  const analysisHeading = getAnalysisHeading(conversationTitle, findings);
  const orderedPerspectiveEntries = PERSPECTIVE_ORDER.filter(
    (key) => key in analysisDraft.per_perspective_implications,
  ).map(
    (key) => [key, analysisDraft.per_perspective_implications[key]] as const,
  );

  return (
    <div className="mx-auto max-w-6xl space-y-8 pb-8">
      {/* Hero section */}
      <section className="overflow-hidden rounded-[28px] border border-border bg-[linear-gradient(135deg,#f4efe6_0%,#edf3f4_48%,#f5f7fb_100%)] shadow-sm">
        <div className="grid gap-6 px-6 py-6 lg:grid-cols-[1.5fr,0.9fr]">
          <div className="space-y-4">
            <div className="flex flex-wrap items-center gap-2">
              <span className="rounded-full border border-border bg-white/75 px-3 py-1 text-[11px] font-medium uppercase tracking-[0.18em] text-text-muted">
                Draft Analysis
              </span>
            </div>
            <div>
              <h1 className="font-serif text-3xl leading-tight text-text-primary">
                {analysisHeading}
              </h1>
              <p className="mt-3 max-w-3xl text-sm leading-6 text-text-secondary">
                {analysisDraft.summary}
              </p>
            </div>
          </div>

          <div className="grid gap-3 grid-cols-2 lg:grid-cols-3">
            <div className="rounded-[20px] border border-border bg-white/70 px-4 py-3">
              <p className="text-[11px] uppercase tracking-[0.16em] text-text-muted">Findings</p>
              <p className="mt-1.5 text-2xl font-semibold text-text-primary">
                {findings.length}
              </p>
            </div>
            <div className="rounded-[20px] border border-border bg-white/70 px-4 py-3">
              <p className="text-[11px] uppercase tracking-[0.16em] text-text-muted">Avg confidence</p>
              <div className="mt-1.5 flex items-center gap-2">
                <p className={`text-2xl font-semibold ${getConfidenceTextColor(averageConfidence)}`}>
                  {averageConfidence}%
                </p>
                <div className="h-2 w-12 overflow-hidden rounded-full bg-border/40">
                  <div
                    className={`h-full rounded-full ${getConfidenceColor(averageConfidence)}`}
                    style={{ width: `${averageConfidence}%` }}
                  />
                </div>
              </div>
            </div>
            <div className="rounded-[20px] border border-border bg-white/70 px-4 py-3">
              <p className="text-[11px] uppercase tracking-[0.16em] text-text-muted">ATT&CK Techniques</p>
              <p className="mt-1.5 text-2xl font-semibold text-text-primary">
                {uniqueTechniques.length}
              </p>
            </div>
            <div className="rounded-[20px] border border-border bg-white/70 px-4 py-3">
              <p className="text-[11px] uppercase tracking-[0.16em] text-text-muted">Shared indicators</p>
              <p className="mt-1.5 text-2xl font-semibold text-text-primary">
                {sharedIndicatorCount}
                {sharedIndicatorCount > 0 && (
                  <span className="ml-1.5 text-xs font-normal text-warning">cross-linked</span>
                )}
              </p>
            </div>
            <div className="rounded-[20px] border border-border bg-white/70 px-4 py-3">
              <p className="text-[11px] uppercase tracking-[0.16em] text-text-muted">Timeline span</p>
              <p className="mt-1.5 text-2xl font-semibold text-text-primary">{timelineSpan}</p>
            </div>
            <div className="rounded-[20px] border border-border bg-white/70 px-4 py-3">
              <p className="text-[11px] uppercase tracking-[0.16em] text-text-muted">Sources</p>
              <p className="mt-1.5 text-2xl font-semibold text-text-primary">{uniqueSources.length}</p>
              <p className="mt-0.5 text-[11px] text-text-muted truncate">
                {uniqueSources.map(formatSourceLabel).join(", ")}
              </p>
            </div>
          </div>
        </div>

        {Object.keys(pirCoverage).length > 0 && (
          <div className="border-t border-border/50 px-6 py-3">
            <div className="flex flex-wrap items-center gap-4">
              <span className="text-[11px] font-medium uppercase tracking-[0.14em] text-text-muted">
                PIR Coverage
              </span>
              {Object.entries(pirCoverage)
                .sort(([a], [b]) => a.localeCompare(b))
                .map(([pir, count]) => (
                  <div key={pir} className="flex items-center gap-2">
                    <span className="text-xs font-medium text-text-secondary">{pir}</span>
                    <div className="flex gap-0.5">
                      {Array.from({ length: findings.length }, (_, i) => (
                        <div
                          key={i}
                          className={`h-2.5 w-2.5 rounded-sm ${i < count ? "bg-primary" : "bg-border/30"}`}
                        />
                      ))}
                    </div>
                    <span className="text-[11px] text-text-muted">{count}</span>
                  </div>
                ))}
            </div>
          </div>
        )}
      </section>

      {data.collection_coverage && (
        <CollectionCoverageView coverage={data.collection_coverage} />
      )}

      {/* Key judgments / recommended actions / gaps */}
      <section className="grid gap-4 grid-cols-1 xl:grid-cols-3">
        <article className="rounded-[24px] border border-border bg-surface px-5 py-5 shadow-sm">
          <p className="text-xs font-medium uppercase tracking-[0.12em] text-text-muted">
            Key Judgments
          </p>
          <ol className="mt-4 space-y-3">
            {analysisDraft.key_judgments.map((judgment, index) => (
              <li key={judgment} className="flex gap-3 text-sm leading-6 text-text-primary">
                <span className="mt-0.5 inline-flex h-6 w-6 shrink-0 items-center justify-center rounded-full border border-border bg-surface-muted text-[11px] font-semibold text-text-secondary">
                  {index + 1}
                </span>
                <span>{judgment}</span>
              </li>
            ))}
          </ol>
        </article>

        <article className="rounded-[24px] border border-border bg-surface px-5 py-5 shadow-sm">
          <p className="text-xs font-medium uppercase tracking-[0.12em] text-text-muted">
            Recommended Actions
          </p>
          <ul className="mt-4 space-y-2">
            {analysisDraft.recommended_actions.map((action) => (
              <li
                key={action}
                className="rounded-[14px] border-l-[3px] border-l-primary bg-primary-subtle/30 px-3 py-2.5 text-sm leading-6 text-text-primary"
              >
                {action}
              </li>
            ))}
          </ul>
        </article>

        <article className="rounded-3xl border border-border bg-surface px-5 py-5 shadow-sm">
          <p className="text-xs font-medium uppercase tracking-[0.12em] text-text-muted">
            Information Gaps
          </p>
          <ul className="mt-4 space-y-2">
            {analysisDraft.information_gaps.map((gap) => (
              <li
                key={gap}
                className="rounded-[14px] border-l-[3px] border-l-warning bg-warning/5 px-3 py-2.5 text-sm leading-6 text-text-secondary"
              >
                {gap}
              </li>
            ))}
          </ul>
        </article>
      </section>

      {/* Evidence docket */}
      <section className="space-y-4">
        <div className="flex items-end justify-between gap-4">
          <div>
            <p className="text-xs font-medium uppercase tracking-[0.12em] text-text-muted">
              Processing Findings
            </p>
            <h2 className="mt-1 text-2xl font-semibold text-text-primary">Evidence docket</h2>
          </div>
          <span className="rounded-full border border-border bg-surface-muted px-3 py-1 text-xs text-text-secondary">
            {findings.length} findings
          </span>
        </div>

        <div className="space-y-3">
          {findings.map((finding) => (
            <details
              key={finding.id}
              className="group rounded-[24px] border border-border bg-surface shadow-sm"
            >
              <summary className="list-none cursor-pointer px-5 py-4" aria-label={`Finding ${finding.id}`}>
                <div className="flex items-center gap-4">
                  <div className="flex shrink-0 items-center gap-2">
                    <span className="rounded-full border border-border bg-surface-muted px-2.5 py-1 text-[11px] font-medium uppercase tracking-[0.16em] text-text-muted">
                      {finding.id}
                    </span>
                    <span className="rounded-full border border-border bg-white px-2.5 py-1 text-[11px] uppercase tracking-wide text-text-secondary">
                      {formatSourceLabel(finding.source)}
                    </span>
                  </div>

                  <div className="min-w-0 flex-1">
                    <h3 className="truncate text-sm font-semibold text-text-primary">{finding.title}</h3>
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
                      <div className="h-2 w-14 overflow-hidden rounded-full bg-border/40">
                        <div
                          className={`h-full rounded-full ${getConfidenceColor(finding.confidence)}`}
                          style={{ width: `${finding.confidence}%` }}
                        />
                      </div>
                      <span className={`text-sm font-semibold tabular-nums ${getConfidenceTextColor(finding.confidence)}`}>
                        {finding.confidence}%
                      </span>
                    </div>
                    <span className="text-xs text-text-muted group-open:rotate-90 transition-transform">&#9654;</span>
                  </div>
                </div>
              </summary>

              <div className="grid gap-5 border-t border-border px-5 py-5 lg:grid-cols-[1.4fr,0.9fr]">
                <div className="space-y-5">
                  <section>
                    <p className="text-xs font-medium uppercase tracking-[0.12em] text-text-muted">Finding</p>
                    <p className="mt-2 text-sm leading-7 text-text-primary">{finding.finding}</p>
                  </section>

                  <section className="rounded-[18px] border-l-[3px] border-l-primary bg-primary-subtle/30 px-4 py-3">
                    <p className="text-xs font-medium uppercase tracking-[0.12em] text-primary">Why it matters</p>
                    <p className="mt-2 text-sm leading-7 text-text-primary">{finding.why_it_matters}</p>
                  </section>

                  <section>
                    <p className="text-xs font-medium uppercase tracking-[0.12em] text-text-muted">Uncertainties</p>
                    <ul className="mt-3 space-y-2">
                      {finding.uncertainties.map((uncertainty) => (
                        <li key={uncertainty} className="flex gap-2.5 text-sm leading-6 text-text-secondary">
                          <span className="mt-[0.55em] h-1.5 w-1.5 shrink-0 rounded-full bg-warning" />
                          <span>{uncertainty}</span>
                        </li>
                      ))}
                    </ul>
                  </section>
                </div>

                <div className="space-y-5">
                  <section className="rounded-[20px] border border-border bg-surface-muted/60 px-4 py-4">
                    <p className="text-xs font-medium uppercase tracking-[0.12em] text-text-muted">Evidence summary</p>
                    <p className="mt-2 text-sm leading-6 text-text-primary">{finding.evidence_summary}</p>
                  </section>

                  <section className="rounded-[20px] border border-border bg-surface-muted/60 px-4 py-4">
                    <p className="text-xs font-medium uppercase tracking-[0.12em] text-text-muted">Key indicators</p>
                    <div className="mt-3 space-y-3">
                      {PRIORITY_DATA_KEYS.filter(
                        (key) => finding.supporting_data[key]?.length > 0,
                      ).map((key) => (
                        <div key={key}>
                          <p className="text-[11px] font-medium uppercase tracking-[0.12em] text-text-muted">
                            {LABEL_MAP[key] || key}
                          </p>
                          <div className="mt-1.5 flex flex-wrap gap-1.5">
                            {finding.supporting_data[key].map((value) => (
                              <span
                                key={`${key}-${value}`}
                                className="rounded-md border border-border bg-surface px-2 py-1 text-xs text-text-secondary"
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

                  <details className="rounded-[20px] border border-border bg-surface-muted/40">
                    <summary className="cursor-pointer px-4 py-3 text-xs font-medium text-text-secondary hover:text-text-primary">
                      Show all technical data
                    </summary>
                    <div className="grid gap-3 px-4 pb-4 md:grid-cols-2">
                      {Object.entries(finding.supporting_data)
                        .filter(([, values]) => values.length > 0)
                        .map(([key, values]) => (
                          <div key={key} className="rounded-[14px] border border-border bg-surface/80 px-3 py-2.5">
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
                  </details>
                </div>
              </div>
            </details>
          ))}
        </div>
      </section>

      {/* Perspective implications */}
      <section className="space-y-4">
        <div>
          <p className="text-xs font-medium uppercase tracking-[0.12em] text-text-muted">
            Perspective Implications
          </p>
          <h2 className="mt-1 text-2xl font-semibold text-text-primary">Framing by perspective</h2>
        </div>

        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
          {orderedPerspectiveEntries.map(([key, implications]) => {
            const firstAssertion = implications[0] ?? null;
            const preview = firstAssertion
              ? firstAssertion.assertion.length > 120
                ? `${firstAssertion.assertion.slice(0, 120)}...`
                : firstAssertion.assertion
              : null;
            return (
              <details
                key={key}
                className="group rounded-[22px] border border-border bg-surface px-4 py-4 shadow-sm"
              >
                <summary className="flex cursor-pointer items-center justify-between list-none">
                  <div className="flex items-center gap-2">
                    <h3 className="text-sm font-semibold text-text-primary">
                      {formatPerspectiveLabel(key)}
                    </h3>
                    {firstAssertion?.confidence && (
                      <AssertionTierBadge confidence={firstAssertion.confidence} />
                    )}
                  </div>
                  <span className="text-xs text-text-muted group-open:rotate-90 transition-transform">
                    &#9654;
                  </span>
                </summary>
                {preview && (
                  <p className="mt-2 text-sm leading-6 text-text-secondary group-open:hidden">
                    {preview}
                  </p>
                )}
                <ul className="mt-3 space-y-2">
                  {implications.map((assertion, idx) => (
                    <AssertionBreakdown
                      key={idx}
                      assertion={assertion}
                      allFindings={findings}
                    />
                  ))}
                </ul>
              </details>
            );
          })}
        </div>
      </section>

      {/* Start council CTA */}
      <div className="flex justify-end pt-2">
        <button
          type="button"
          onClick={onStartCouncil}
          className="rounded-[18px] border border-border bg-surface px-5 py-2.5 text-sm font-medium text-text-primary shadow-sm hover:bg-surface-muted transition-colors"
        >
          Start Council →
        </button>
      </div>
    </div>
  );
}
