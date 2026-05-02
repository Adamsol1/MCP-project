import React, { useEffect, useMemo, useRef, useState } from "react";
import { useT } from "../../i18n/useT";
import { useSettings } from "../../contexts/SettingsContext/SettingsContext";
import ApprovalPrompt from "../ApprovalPrompt/ApprovalPrompt";
import { HelpModal, HelpButton } from "../HelpModal/HelpModal";
import CitationText from "../CitationText/CitationText";
import SourceList from "../SourceList/SourceList";
import AnalysisWorkspace from "../AnalysisWorkspace/AnalysisWorkspace";
import type {
  CollectionDisplayData,
  CollectionPlanData,
  CollectionPlanStep,
  CollectionSourceSummary,
  CollectionSummaryData,
  Message,
  PirData,
  ProcessingData,
  SuggestedSourcesData,
} from "../../types/conversation";
import type {
  DialoguePhase,
  DialogueStage,
  DialogueSubState,
} from "../../types/dialogue";
import { useWorkspace } from "../../contexts/WorkspaceContext/WorkspaceContext";
import type { CollectionStatus } from "../../services/dialogue/dialogue";
import type { SourceTimeframes } from "../../types/settings";

function Chevron() {
  return (
    <svg
      width="12"
      height="12"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2.5"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
      className="inline-block ml-1 transition-transform group-open:rotate-180"
    >
      <path d="M6 9l6 6 6-6" />
    </svg>
  );
}

/** Renders reasoning markdown into structured sections and bullet lists. */
function ReasoningMarkdown({ text }: { text: string }) {
  // Normalise: replace inline " * " separators (model sometimes omits newlines)
  // with a real newline so each bullet lands on its own line.
  const normalised = text
    .replace(/\r\n/g, "\n")
    .replace(/ \* /g, "\n* ");

  const rawLines = normalised.split("\n");

  type Block =
    | { kind: "heading"; text: string }
    | { kind: "bullet"; text: string }
    | { kind: "prose"; text: string };

  const blocks: Block[] = [];
  for (const raw of rawLines) {
    const line = raw.trim();
    if (!line) continue;
    if (line.startsWith("* ") || line.startsWith("- ")) {
      blocks.push({ kind: "bullet", text: line.slice(2).trim() });
    } else if (/^[A-Z][^*\n]{0,80}:\s*$/.test(line)) {
      // Line is only a section label like "Perspective Integration:"
      blocks.push({ kind: "heading", text: line.replace(/:$/, "") });
    } else {
      blocks.push({ kind: "prose", text: line });
    }
  }

  // Group consecutive bullets into <ul> runs
  const rendered: React.ReactNode[] = [];
  let i = 0;
  while (i < blocks.length) {
    const block = blocks[i];
    if (block.kind === "heading") {
      rendered.push(
        <p key={i} className="text-xs font-semibold uppercase tracking-wide text-text-muted mt-3 mb-1">
          {block.text}
        </p>
      );
      i++;
    } else if (block.kind === "bullet") {
      const bullets: React.ReactNode[] = [];
      while (i < blocks.length && blocks[i].kind === "bullet") {
        const b = blocks[i] as { kind: "bullet"; text: string };
        bullets.push(
          <li key={i} className="flex gap-2 items-start">
            <span className="mt-1.5 shrink-0 w-1.5 h-1.5 rounded-full bg-text-muted/60" />
            <span className="flex-1">{renderInline(b.text)}</span>
          </li>
        );
        i++;
      }
      rendered.push(
        <ul key={`ul-${i}`} className="space-y-1.5 ml-1">
          {bullets}
        </ul>
      );
    } else {
      rendered.push(
        <p key={i} className="leading-relaxed">
          {renderInline(block.text)}
        </p>
      );
      i++;
    }
  }

  return <div className="space-y-1 text-sm text-text-secondary">{rendered}</div>;
}

/** Renders inline markdown: **bold** and plain text segments. */
function renderInline(text: string): React.ReactNode {
  const parts = text.split(/(\*\*[^*]+\*\*)/g);
  return parts.map((part, i) => {
    if (/^\*\*[^*]+\*\*$/.test(part)) {
      return <strong key={i} className="font-semibold text-text-primary">{part.slice(2, -2)}</strong>;
    }
    // Strip any residual stray asterisks at boundaries
    return <span key={i}>{part.replace(/^\*+|\*+$/g, "")}</span>;
  });
}

function PirMessage({ pirData }: { pirData: PirData }) {
  const { highlightedRefs, setHighlightedRefs, setPirData } = useWorkspace();
  const t = useT();
  const PRIORITY_LABEL: Record<string, string> = {
    high: t.priorityHigh,
    medium: t.priorityMedium,
    low: t.priorityLow,
  };
  const PRIORITY_COLOR: Record<string, string> = {
    high: "text-error",
    medium: "text-warning-dark",
    low: "text-text-muted",
  };

  const PRIORITY_ORDER: Record<string, number> = { high: 0, medium: 1, low: 2 };

  const sortedPirs = [...pirData.pirs].sort(
    (a, b) =>
      (PRIORITY_ORDER[a.priority] ?? 3) - (PRIORITY_ORDER[b.priority] ?? 3),
  );

  useEffect(() => {
    setPirData(pirData);
  }, [pirData, setPirData]);

  const handleHoveredRefs = (value: string[] | string | null) => {
    setHighlightedRefs(Array.isArray(value) ? value : value ? [value] : []);
  };

  const reasoningText = (pirData.reasoning ?? "").trim();

  return (
    <div className="space-y-3">
      <h3 className="font-semibold">{t.pirHeader}</h3>
      {pirData.pir_text && (
        <div className="text-sm text-text-secondary leading-relaxed">
          <CitationText
            text={pirData.pir_text}
            claims={pirData.claims}
            highlightedRefs={highlightedRefs}
            onRefHover={handleHoveredRefs}
          />
        </div>
      )}
      <div className="space-y-2 mt-2">
        {sortedPirs.map((pir, i) => (
          <div
            key={i}
            className="rounded-lg border border-border/50 bg-surface-muted px-3 py-2.5 space-y-1"
          >
            <div className="flex items-center gap-2">
              <span className="flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-primary/10 text-xs font-bold text-primary">
                {i + 1}
              </span>
              <p className="text-sm font-semibold text-text-primary leading-tight flex-1">
                {pir.question}
              </p>
              <span
                className={`ml-auto shrink-0 rounded px-1.5 py-0.5 text-xs font-semibold ${PRIORITY_COLOR[pir.priority] ?? "text-text-muted"} bg-surface-muted`}
              >
                {t.priority}: {PRIORITY_LABEL[pir.priority] ?? pir.priority}
              </span>
            </div>
            <details className="group">
              <summary className="cursor-pointer list-none text-xs text-text-muted hover:text-text-secondary select-none flex items-center pl-7">
                {t.rationale}
                <Chevron />
              </summary>
              <div className="mt-1.5 text-xs text-text-secondary leading-relaxed pl-7">
                <CitationText
                  text={pir.rationale}
                  claims={pirData.claims}
                  highlightedRefs={highlightedRefs}
                  onRefHover={handleHoveredRefs}
                />
              </div>
            </details>
          </div>
        ))}
      </div>
      <details className="group mt-3 border-t border-border/50 pt-2" open>
        <summary className="cursor-pointer list-none text-xs font-medium uppercase tracking-wider text-text-muted hover:text-text-secondary select-none flex items-center gap-1">
          Sources ({pirData.sources?.length ?? 0})
          <Chevron />
        </summary>
        <div className="mt-1.5">
          {pirData.sources && pirData.sources.length > 0 ? (
            <SourceList
              sources={pirData.sources}
              highlightedRefs={highlightedRefs}
              onSourceHover={handleHoveredRefs}
            />
          ) : (
            <p className="text-xs text-text-muted italic px-2">
              No knowledge bank sources used — PIRs generated from the
              conversation context.
            </p>
          )}
        </div>
      </details>
      {reasoningText && (
        <details className="group mt-3 border-t border-border/50 pt-2">
          <summary className="cursor-pointer list-none text-sm font-medium text-text-secondary hover:text-text-primary select-none flex items-center gap-1">
            {t.showReasoning}
            <Chevron />
          </summary>
          <div className="mt-2 bg-surface-muted rounded-md p-3">
            <ReasoningMarkdown text={reasoningText} />
          </div>
        </details>
      )}
    </div>
  );
}

function CollectionPlanMessage({ planData }: { planData: CollectionPlanData }) {
  const t = useT();
  const reasoningText = (planData.reasoning ?? "").trim();
  return (
    <div className="space-y-3">
      <h3 className="font-semibold">Collection Plan</h3>

      {/* Structured steps — shown when the AI returns step breakdown */}
      {planData.steps && planData.steps.length > 0 ? (
        <div className="space-y-2">
          {planData.steps.map((step: CollectionPlanStep, index: number) => {
            // Split "Title (PIR N)" into title + optional tag
            const tagMatch = step.title.match(/^(.*?)\s*\(([^)]+)\)\s*$/);
            const displayTitle = tagMatch ? tagMatch[1].trim() : step.title;
            const tag = tagMatch ? tagMatch[2] : null;
            return (
              <div
                key={index}
                className="rounded-lg border border-border/50 bg-surface-muted px-3 py-2.5 space-y-1"
              >
                <div className="flex items-center gap-2">
                  <span className="flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-primary/10 text-xs font-bold text-primary">
                    {index + 1}
                  </span>
                  <p className="text-sm font-semibold text-text-primary leading-tight">
                    {displayTitle}
                  </p>
                  {tag && (
                    <span className="ml-auto shrink-0 rounded px-1.5 py-0.5 text-xs font-medium bg-surface-muted text-text-muted">
                      {tag}
                    </span>
                  )}
                </div>
                <p className="pl-7 text-xs text-text-secondary leading-relaxed">
                  {step.description}
                </p>
                {step.suggested_sources &&
                  step.suggested_sources.length > 0 && (
                    <div className="pl-7 pt-1.5 space-y-1">
                      <p className="text-[10px] font-semibold uppercase tracking-widest text-text-muted">
                        Suggested Sources
                      </p>
                      <div className="flex flex-wrap gap-1">
                        {step.suggested_sources.map((src) => (
                          <span
                            key={src}
                            className="rounded px-1.5 py-0.5 text-xs font-medium bg-primary/10 text-primary"
                          >
                            {src}
                          </span>
                        ))}
                      </div>
                    </div>
                  )}
              </div>
            );
          })}
        </div>
      ) : (
        /* Fallback to plain text if no steps */
        <p className="whitespace-pre-wrap text-sm text-text-primary">
          {planData.plan}
        </p>
      )}
      {reasoningText && (
        <details className="group mt-3 border-t border-border/50 pt-2">
          <summary className="cursor-pointer list-none text-sm font-medium text-text-secondary hover:text-text-primary select-none flex items-center gap-1">
            {t.showReasoning}
            <Chevron />
          </summary>
          <div className="mt-2 bg-surface-muted rounded-md p-3">
            <ReasoningMarkdown text={reasoningText} />
          </div>
        </details>
      )}
    </div>
  );
}

function SuggestedSourcesMessage({
  sources,
}: {
  sources: SuggestedSourcesData;
}) {
  const t = useT();
  if (sources.length === 0) {
    return <p>{t.noSourceSuggestions}</p>;
  }

  return (
    <div className="space-y-2">
      <h3 className="font-semibold">{t.suggestedSourcesHeader}</h3>
      <ul className="list-disc pl-5 text-sm text-text-secondary">
        {sources.map((source) => (
          <li key={source}>{source}</li>
        ))}
      </ul>
    </div>
  );
}

function CollectionSummaryMessage({ data }: { data: CollectionSummaryData }) {
  const t = useT();
  return (
    <div className="space-y-3">
      <h3 className="font-semibold">{t.collectionSummaryHeader}</h3>
      <p className="whitespace-pre-wrap text-sm text-text-primary">
        {data.summary}
      </p>
      {data.sources_used.length > 0 && (
        <div className="border-t border-border/50 pt-2">
          <p className="text-sm font-medium text-text-secondary">
            {t.sourcesUsed}
          </p>
          <ul className="mt-1 list-disc pl-5 text-sm text-text-secondary">
            {data.sources_used.map((source) => (
              <li key={source}>{source}</li>
            ))}
          </ul>
        </div>
      )}
      <div className="border-t border-border/50 pt-2">
        <p className="text-sm font-medium text-text-secondary">{t.gaps}</p>
        <p className="mt-1 text-sm text-text-secondary">
          {data.gaps ?? t.noGapsIdentified}
        </p>
      </div>
    </div>
  );
}

type ConfidenceTier = "low" | "moderate" | "high" | "assessed";

function confidenceTierFromInt(score: number): ConfidenceTier {
  if (score >= 80) return "assessed";
  if (score >= 60) return "high";
  if (score >= 40) return "moderate";
  return "low";
}

const FINDING_TIER_STYLES: Record<ConfidenceTier, string> = {
  assessed: "bg-purple-600 text-white",
  high: "bg-emerald-600 text-white",
  moderate: "bg-amber-500 text-white",
  low: "bg-red-600 text-white",
};

const SOURCE_DISPLAY_NAMES: Record<string, string> = {
  knowledge_bank: "Knowledge Bank",
  otx: "AlienVault OTX",
  web_gov: "Government / Official",
  web_think_tank: "Think Tank",
  web_news: "News",
  web_search: "Web Search",
  web_other: "Web",
  pretrained: "Pretrained Knowledge",
  osint: "OSINT",
};

function formatRelevantTo(values: string[]): string {
  return values.join(", ");
}

/** Renders an APA citation string, turning the trailing URL (if any) into a clickable link. */
function ApaWithLink({ citation, url }: { citation: string; url: string }) {
  const urlIdx = citation.lastIndexOf("https://");
  if (urlIdx === -1) {
    return (
      <>
        {citation}{" "}
        <a href={url} target="_blank" rel="noopener noreferrer"
           className="text-primary underline underline-offset-2 hover:text-primary-dark break-all">
          {url}
        </a>
      </>
    );
  }
  return (
    <>
      {citation.slice(0, urlIdx)}
      <a href={citation.slice(urlIdx)} target="_blank" rel="noopener noreferrer"
         className="text-primary underline underline-offset-2 hover:text-primary-dark break-all">
        {citation.slice(urlIdx)}
      </a>
    </>
  );
}

function FindingDetailModal({
  finding,
  displayId,
  onClose,
}: {
  finding: ProcessingData["findings"][number] | null;
  displayId?: string;
  onClose: () => void;
}) {
  const [isHelpOpen, setIsHelpOpen] = useState(false);

  useEffect(() => {
    if (!finding) return;
    const handler = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    document.addEventListener("keydown", handler);
    return () => document.removeEventListener("keydown", handler);
  }, [finding, onClose]);

  const { pirData, collectionData } = useWorkspace();

  if (!finding) return null;

  const tier = confidenceTierFromInt(finding.confidence);
  const tierStyle = FINDING_TIER_STYLES[tier];
  const sourceLabel = SOURCE_DISPLAY_NAMES[finding.source] ?? finding.source;
  const sd = finding.supporting_data ?? {};

  // Resolve all source references into a unified list for APA display.
  const allItems = collectionData?.collected_data ?? [];

  type ResolvedSource =
    | { kind: "web"; url: string; apa: string | null; title: string | null }
    | { kind: "kb"; ref: string }
    | { kind: "file"; ref: string; apa: string | null; title: string | null }
    | { kind: "otx"; indicator: string };

  const resolvedSources: ResolvedSource[] = (() => {
    const sources: ResolvedSource[] = [];

    // 1. Web: explicit source_urls, then domain fallback
    const webUrls = sd.source_urls?.length
      ? sd.source_urls
      : (sd.domains ?? []).map((d) => `https://${d}`);
    for (const url of webUrls) {
      const match = allItems.find(
        (item) =>
          item.resource_id === url ||
          (item.resource_id && item.resource_id.startsWith(url)) ||
          (item.resource_id && url.startsWith(item.resource_id))
      );
      sources.push({ kind: "web", url, apa: match?.apa_citation ?? null, title: match?.title ?? null });
    }

    // 2. Uploaded files via source_refs
    for (const ref of sd.source_refs ?? []) {
      const match = allItems.find((item) => item.resource_id === ref);
      sources.push({ kind: "file", ref, apa: match?.apa_citation ?? null, title: match?.title ?? ref });
    }

    // 3. Knowledge base refs
    for (const ref of sd.kb_refs ?? []) {
      sources.push({ kind: "kb", ref });
    }

    // 4. OTX IoCs
    for (const indicator of sd.iocs ?? []) {
      sources.push({ kind: "otx", indicator });
    }

    return sources;
  })();

  type PirEntry = { label: string; item: PirData["pirs"][number] };
  const referencedPirs = finding.relevant_to
    .map((label): PirEntry | null => {
      const idx = parseInt(label.replace(/^PIR-/i, ""), 10) - 1;
      const item = pirData?.pirs?.[idx];
      return item ? { label, item } : null;
    })
    .filter((x): x is PirEntry => x !== null);

  return (
    <>
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 p-4"
      onClick={onClose}
    >
      <div
        role="dialog"
        aria-modal="true"
        className="relative w-full max-w-4xl max-h-[90vh] overflow-y-auto rounded-2xl border border-border bg-surface shadow-2xl flex flex-col"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="sticky top-0 z-10 bg-surface border-b border-border px-6 py-4">
          <div className="flex items-start justify-between gap-4">
            <div className="flex items-start gap-3 flex-1 min-w-0">
              <span className="shrink-0 rounded-md border border-border/50 bg-surface-muted px-2 py-1 font-mono text-xs font-bold text-text-secondary mt-0.5">
                {displayId ?? finding.id}
              </span>
              <div className="flex-1 min-w-0">
                <h2 className="text-base font-semibold text-text-primary leading-snug">
                  {finding.title}
                </h2>
                <div className="flex flex-wrap items-center gap-2 mt-1.5">
                  <span
                    className={`rounded-md px-2 py-0.5 text-xs font-bold tracking-wide ${tierStyle}`}
                  >
                    {tier.toUpperCase()}
                  </span>
                  <span className="text-xs text-text-muted">{sourceLabel}</span>
                  {finding.relevant_to.length > 0 && (
                    <div className="flex flex-wrap gap-1">
                      {finding.relevant_to.map((pir) => (
                        <span
                          key={pir}
                          className="rounded-md bg-primary/10 px-2 py-0.5 text-xs font-semibold text-primary"
                        >
                          {pir}
                        </span>
                      ))}
                    </div>
                  )}
                </div>
              </div>
            </div>
            <div className="flex shrink-0 items-center gap-2">
              <HelpButton onClick={() => setIsHelpOpen(true)} label="Finding guide" />
              <button
                aria-label="close"
                onClick={onClose}
                className="rounded-lg p-1.5 text-text-muted hover:bg-surface-elevated hover:text-text-primary transition-colors"
              >
                ✕
              </button>
            </div>
          </div>
        </div>

        {/* Body */}
        <div className="px-6 py-5 space-y-5 text-sm">
          {/* Finding */}
          <div>
            <p className="text-[10px] font-semibold uppercase tracking-widest text-text-muted mb-1">
              Finding
            </p>
            <p className="text-text-secondary leading-relaxed">
              {finding.finding}
            </p>
          </div>

          {/* Why it matters */}
          {finding.why_it_matters && (
            <div>
              <p className="text-[10px] font-semibold uppercase tracking-widest text-text-muted mb-1">
                Why It Matters
              </p>
              <p className="text-text-muted italic leading-relaxed">
                {finding.why_it_matters}
              </p>
            </div>
          )}

          {/* Sources (APA 7th) */}
          {resolvedSources.length > 0 && (
            <div className="border-t border-border/50 pt-4 space-y-2">
              <p className="text-[10px] font-semibold uppercase tracking-widest text-text-muted">
                Sources
              </p>
              <ol className="space-y-2 list-none">
                {resolvedSources.map((src, idx) => (
                  <li key={idx} className="flex gap-2 text-xs text-text-secondary leading-relaxed">
                    <span className="shrink-0 font-mono text-text-muted">[{idx + 1}]</span>
                    <span>
                      {src.kind === "web" && (
                        src.apa ? (
                          <ApaWithLink citation={src.apa} url={src.url} />
                        ) : (
                          <>
                            {src.title && <span className="italic">{src.title}. </span>}
                            <a href={src.url} target="_blank" rel="noopener noreferrer"
                               className="text-primary underline underline-offset-2 hover:text-primary-dark break-all">
                              {src.url}
                            </a>
                          </>
                        )
                      )}
                      {src.kind === "file" && (
                        src.apa ? (
                          <span>{src.apa}</span>
                        ) : (
                          <span className="italic">{src.title ?? src.ref}</span>
                        )
                      )}
                      {src.kind === "kb" && (
                        <span>
                          <span className="font-medium text-text-primary">Knowledge Base: </span>
                          <span className="font-mono">{src.ref}</span>
                        </span>
                      )}
                      {src.kind === "otx" && (
                        <span>
                          <span className="font-medium text-text-primary">AlienVault OTX — </span>
                          <span className="font-mono">{src.indicator}</span>
                        </span>
                      )}
                    </span>
                  </li>
                ))}
              </ol>
            </div>
          )}

          {/* Supporting data — technical metadata only (sources moved above) */}
          {((sd.attack_ids?.length ?? 0) > 0 ||
            (sd.entities?.length ?? 0) > 0) && (
            <div className="border-t border-border/50 pt-4 space-y-3">
              {(sd.attack_ids?.length ?? 0) > 0 && (
                <div>
                  <p className="text-xs font-medium text-text-secondary mb-1">
                    ATT&amp;CK Techniques
                  </p>
                  <div className="flex flex-wrap gap-1">
                    {sd.attack_ids!.map((id) => (
                      <span
                        key={id}
                        className="rounded border border-border/50 bg-surface-muted px-1.5 py-0.5 font-mono text-[11px] text-text-primary"
                      >
                        {id}
                      </span>
                    ))}
                  </div>
                </div>
              )}
              {(sd.entities?.length ?? 0) > 0 && (
                <div>
                  <p className="text-xs font-medium text-text-secondary mb-1">
                    Entities
                  </p>
                  <p className="text-xs text-text-primary">
                    {sd.entities!.join(", ")}
                  </p>
                </div>
              )}
            </div>
          )}

          {/* Uncertainties */}
          {(finding.uncertainties?.length ?? 0) > 0 && (
            <div className="border-t border-border/50 pt-4">
              <p className="text-[10px] font-semibold uppercase tracking-widest text-text-muted mb-2">
                Uncertainties
              </p>
              <ul className="list-disc pl-4 space-y-1 text-xs text-text-muted">
                {finding.uncertainties.map((u, i) => (
                  <li key={i}>{u}</li>
                ))}
              </ul>
            </div>
          )}

          {/* Referenced PIRs in full */}
          {referencedPirs.length > 0 && (
            <div className="border-t border-border/50 pt-4 space-y-3">
              <p className="text-[10px] font-semibold uppercase tracking-widest text-text-muted">
                Priority Intelligence Requirements
              </p>
              {referencedPirs.map(({ label, item }) => (
                <div key={label} className="rounded-lg bg-surface-muted border border-border/50 px-3 py-2.5 space-y-1">
                  <div className="flex items-center gap-2">
                    <span className="rounded-md bg-primary/10 px-2 py-0.5 text-xs font-semibold text-primary shrink-0">
                      {label}
                    </span>
                    <span className="text-[10px] font-medium uppercase tracking-wide text-text-muted">
                      {item.priority}
                    </span>
                  </div>
                  <p className="text-xs text-text-primary leading-relaxed">{item.question}</p>
                  {item.rationale && (
                    <p className="text-[11px] text-text-muted italic leading-relaxed">{item.rationale}</p>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
    <HelpModal
      isOpen={isHelpOpen}
      onClose={() => setIsHelpOpen(false)}
      title="Understanding Findings"
      sections={[
        {
          heading: "What is a Finding?",
          body: "A finding is a structured intelligence conclusion extracted from the raw collected data. Each finding has a title, a core statement, a confidence score, and supporting evidence drawn from the sources that were queried.",
        },
        {
          heading: "Confidence tiers",
          body: "Confidence reflects how well the evidence supports the finding. Low (below 40%) means limited or conflicting evidence. Moderate (40–69%) means partial corroboration. High (70–89%) means strong, consistent corroboration. Assessed (90%+) means the finding is robustly supported across multiple independent sources.",
        },
        {
          heading: "PIRs — Priority Intelligence Requirements",
          body: "The PIR badges (e.g. PIR-1, PIR-2) show which of your original intelligence requirements this finding is relevant to. These were generated in the Direction phase based on your topic.",
        },
        {
          heading: "ATT&CK techniques",
          body: "ATT&CK IDs (e.g. T1190) reference the MITRE ATT&CK framework — a globally recognised taxonomy of adversary tactics and techniques. They help map findings to known threat behaviours.",
        },
        {
          heading: "APA citations and source references",
          body: "Sources are listed in APA 7th edition format where available. Web sources include the URL and publication details. Uploaded files are referenced by their filename. Knowledge Base references point to your organisation's internal intelligence store.",
        },
      ]}
    />
    </>
  );
}

function ProcessingMessage({
  data,
  onGapCollect,
  onCollectMore,
}: {
  data: ProcessingData;
  onGapCollect?: (gap: string) => void;
  onCollectMore?: () => void;
}) {
  const t = useT();
  const reasoningText = (data.reasoning ?? "").trim();
  const [selectedFinding, setSelectedFinding] = useState<{
    finding: ProcessingData["findings"][number];
    displayId: string;
  } | null>(null);
  const [selectedGaps, setSelectedGaps] = useState<Set<number>>(new Set());
  const [collectMode, setCollectMode] = useState(false);

  const toggleGap = (idx: number) => {
    setSelectedGaps((prev) => {
      const next = new Set(prev);
      if (next.has(idx)) next.delete(idx);
      else next.add(idx);
      return next;
    });
  };

  const collectSelected = () => {
    if (!onGapCollect) return;
    const gaps = data.gaps.filter((_, i) => selectedGaps.has(i));
    if (gaps.length === 0) return;
    const prompt = gaps.map((g, i) => `${i + 1}. ${g}`).join("\n");
    onGapCollect(
      `Please collect additional intelligence to address the following gaps:\n\n${prompt}`,
    );
    setSelectedGaps(new Set());
    setCollectMode(false);
  };

  const collectAll = () => {
    if (!onGapCollect || data.gaps.length === 0) return;
    const prompt = data.gaps.map((g, i) => `${i + 1}. ${g}`).join("\n");
    onGapCollect(
      `Please collect additional intelligence to address the following gaps:\n\n${prompt}`,
    );
    setSelectedGaps(new Set());
    setCollectMode(false);
  };

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between gap-2">
        <h3 className="font-semibold">Processing Results</h3>
        <span className="rounded-full border border-border/50 bg-surface-muted px-2.5 py-0.5 text-xs text-text-muted">
          {data.findings.length} findings
        </span>
      </div>
      <div className="overflow-x-auto rounded-lg border border-border/50">
        <table className="w-full text-sm border-collapse">
          <thead>
            <tr className="bg-surface-muted text-text-muted">
              <th className="px-4 py-2.5 text-left font-semibold uppercase tracking-wide text-xs border-b border-border/50 whitespace-nowrap">
                ID
              </th>
              <th className="px-4 py-2.5 text-left font-semibold uppercase tracking-wide text-xs border-b border-border/50">
                Title
              </th>
              <th className="px-4 py-2.5 text-left font-semibold uppercase tracking-wide text-xs border-b border-border/50 whitespace-nowrap">
                Source
              </th>
              <th className="px-4 py-2.5 text-left font-semibold uppercase tracking-wide text-xs border-b border-border/50 whitespace-nowrap">
                Categories
              </th>
              <th className="px-4 py-2.5 text-left font-semibold uppercase tracking-wide text-xs border-b border-border/50 whitespace-nowrap">
                Confidence
              </th>
              <th className="px-4 py-2.5 text-left font-semibold uppercase tracking-wide text-xs border-b border-border/50 whitespace-nowrap">
                Relevant To
              </th>
            </tr>
          </thead>
          <tbody className="divide-y divide-border/50">
            {[...data.findings]
              .sort((a, b) => b.confidence - a.confidence)
              .map((f, idx) => {
                const tier = confidenceTierFromInt(f.confidence);
                const tierStyle = FINDING_TIER_STYLES[tier];
                const sourceLabel = SOURCE_DISPLAY_NAMES[f.source] ?? f.source;
                const displayId = `F-${String(idx + 1).padStart(2, "0")}`;
                return (
                  <tr
                    key={f.id}
                    onClick={() =>
                      setSelectedFinding({ finding: f, displayId })
                    }
                    className="cursor-pointer transition-colors hover:bg-primary-subtle group/row"
                  >
                    <td className="px-4 py-3 whitespace-nowrap">
                      <span className="font-mono text-xs font-semibold text-text-muted">
                        {displayId}
                      </span>
                    </td>
                    <td title={f.title} className="px-4 py-3 text-text-primary font-medium leading-snug group-hover/row:text-primary max-w-[28ch] truncate">
                      {f.title}
                    </td>
                    <td className="px-4 py-3 text-text-secondary whitespace-nowrap">
                      {sourceLabel}
                    </td>
                    <td className="px-4 py-3 whitespace-nowrap">
                      <div className="flex flex-wrap gap-1">
                        {(f.categories ?? []).map((cat) => (
                          <span
                            key={cat}
                            className="rounded px-1.5 py-0.5 text-xs font-medium bg-primary-subtle text-primary uppercase"
                          >
                            {cat}
                          </span>
                        ))}
                      </div>
                    </td>
                    <td className="px-4 py-3 whitespace-nowrap">
                      <span
                        className={`rounded-md px-2 py-0.5 text-xs font-semibold ${tierStyle}`}
                      >
                        {tier.toUpperCase()}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-text-secondary whitespace-nowrap">
                      {formatRelevantTo(f.relevant_to)}
                    </td>
                  </tr>
                );
              })}
          </tbody>
        </table>
      </div>
      {data.gaps.length > 0 && (
        <div className="border-t border-border/50 pt-3 space-y-3">
          <div className="flex items-center justify-between gap-2">
            <p className="text-sm font-semibold text-text-primary">
              Gaps{" "}
              <span className="ml-1 text-xs font-normal text-text-muted">
                ({data.gaps.length})
              </span>
            </p>
            {onGapCollect && !collectMode && (
              <button
                type="button"
                onClick={() => setCollectMode(true)}
                disabled={!!onCollectMore}
                title={onCollectMore ? "Use the Collect More button below to proceed" : undefined}
                className="rounded-md border border-border/50 px-3 py-1 text-xs font-medium text-text-secondary transition-colors disabled:opacity-40 disabled:cursor-not-allowed hover:enabled:border-primary hover:enabled:text-primary"
              >
                Collect More
              </button>
            )}
            {onGapCollect && collectMode && (
              <button
                type="button"
                onClick={() => {
                  setCollectMode(false);
                  setSelectedGaps(new Set());
                }}
                className="text-xs text-text-muted hover:text-text-secondary transition-colors"
              >
                Cancel
              </button>
            )}
          </div>
          <ul className="space-y-2">
            {data.gaps.map((gap, i) => (
              <li
                key={i}
                className={`flex items-start gap-3 text-sm text-text-secondary leading-snug ${collectMode ? "cursor-pointer" : ""}`}
                onClick={collectMode ? () => toggleGap(i) : undefined}
              >
                {collectMode && (
                  <input
                    type="checkbox"
                    checked={selectedGaps.has(i)}
                    onChange={() => toggleGap(i)}
                    onClick={(e) => e.stopPropagation()}
                    className="mt-0.5 shrink-0 size-4 accent-primary cursor-pointer"
                  />
                )}
                {!collectMode && (
                  <span className="mt-1.5 shrink-0 w-1.5 h-1.5 rounded-full bg-text-muted" />
                )}
                <span>{gap}</span>
              </li>
            ))}
          </ul>
          {onGapCollect && collectMode && (
            <div className="flex gap-2 pt-1">
              <button
                type="button"
                onClick={collectAll}
                className="rounded-md bg-primary px-3 py-1.5 text-xs font-medium text-text-inverse hover:bg-primary-dark transition-colors"
              >
                Collect All
              </button>
              <button
                type="button"
                onClick={collectSelected}
                disabled={selectedGaps.size === 0}
                className="rounded-md border border-border/50 px-3 py-1.5 text-xs font-medium text-text-secondary hover:border-primary hover:text-primary disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
              >
                Collect Selected ({selectedGaps.size})
              </button>
            </div>
          )}
        </div>
      )}
      {reasoningText && (
        <details className="group mt-3 border-t border-border/50 pt-2">
          <summary className="cursor-pointer list-none text-sm font-medium text-text-secondary hover:text-text-primary select-none flex items-center gap-1">
            {t.showReasoning}
            <Chevron />
          </summary>
          <div className="mt-2 bg-surface-muted rounded-md p-3">
            <ReasoningMarkdown text={reasoningText} />
          </div>
        </details>
      )}
      <FindingDetailModal
        finding={selectedFinding?.finding ?? null}
        displayId={selectedFinding?.displayId}
        onClose={() => setSelectedFinding(null)}
      />
    </div>
  );
}

// ── Reviewer content extraction ────────────────────────────────────────────────

interface ChatWindowProps {
  onSendMessage?: (message: string) => void;
  messages?: Message[];
  isConfirming?: boolean;
  isLoading?: boolean;
  stage?: DialogueStage;
  phase?: DialoguePhase;
  subState?: DialogueSubState;
  onApprove?: () => void;
  onReject?: () => void;
  onGatherMore?: () => void;
  onGatherMoreFromProcessing?: () => void;
  isSourceSelecting?: boolean;
  isCollecting?: boolean;
  collectionStatus?: CollectionStatus | null;
  availableSources?: string[];
  selectedSources?: string[];
  onToggleSourceSelection?: (source: string) => void;
  onSubmitSourceSelection?: (sourceTimeframes: Record<string, string>) => void;
  devPrefill?: string | null;
  onDevPrefillConsumed?: () => void;
  inputPrefill?: string | null;
  onInputPrefillConsumed?: () => void;
  onGapCollect?: (gap: string) => void;
}

function SourceSummaryTable({
  summaries,
}: {
  summaries: CollectionSourceSummary[];
}) {
  const t = useT();
  if (summaries.length === 0) return null;
  return (
    <div className="overflow-x-auto rounded border border-border/50">
      <table className="min-w-full text-sm">
        <thead className="bg-surface-muted">
          <tr>
            <th className="text-left px-3 py-1.5 font-medium text-text-secondary">
              {t.tableSource}
            </th>
            <th className="text-right px-3 py-1.5 font-medium text-text-secondary">
              {t.tableItems}
            </th>
          </tr>
        </thead>
        <tbody>
          {summaries.map((s) => (
            <tr key={s.display_name} className="border-t border-border/50">
              <td className="px-3 py-1.5 font-medium text-text-primary">
                {s.display_name}
              </td>
              <td className="px-3 py-1.5 text-right text-text-secondary">
                {s.count}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function CollectionDisplayMessage({
  data,
  runNumber,
}: {
  data: CollectionDisplayData;
  runNumber: number;
}) {
  const { mergeCollectionData, setCollectionData } = useWorkspace();
  const t = useT();

  useEffect(() => {
    if (data.replace) {
      setCollectionData({ collected_data: data.collected_data, source_summary: data.source_summary });
    } else {
      mergeCollectionData(data);
    }
  }, [data, mergeCollectionData, setCollectionData]);

  const header = t.collectionRunLabel(runNumber);

  if (data.parse_error) {
    return (
      <div className="space-y-2">
        <div>
          <h3 className="font-semibold">{header}</h3>
          <p className="mt-0.5 text-xs text-text-secondary">
            {t.collectionResultsSubtitle}
          </p>
        </div>
        <p className="text-sm text-error-text">{t.couldNotParseCollection}</p>
        <details className="group">
          <summary className="cursor-pointer list-none text-xs text-text-muted hover:text-text-secondary select-none flex items-center gap-1">
            {t.rawOutput} <Chevron />
          </summary>
          <pre className="mt-1 text-xs text-text-muted whitespace-pre-wrap break-all">
            {data.parse_error}
          </pre>
        </details>
      </div>
    );
  }

  return (
    <div className="space-y-3">
      <div>
        <h3 className="font-semibold">{header}</h3>
        <p className="mt-0.5 text-xs text-text-secondary">
          {t.collectionResultsSubtitle}
        </p>
      </div>
      <SourceSummaryTable summaries={data.source_summary} />
    </div>
  );
}

export default function ChatWindow({
  onSendMessage,
  messages = [],
  isConfirming = false,
  isLoading = false,
  stage,
  phase = "direction",
  subState,
  onApprove,
  onReject,
  onGatherMore,
  onGatherMoreFromProcessing,
  isSourceSelecting = false,
  isCollecting = false,
  collectionStatus = null,
  availableSources = [],
  selectedSources = [],
  onToggleSourceSelection,
  onSubmitSourceSelection,
  devPrefill,
  onDevPrefillConsumed,
  inputPrefill,
  onInputPrefillConsumed,
  onGapCollect,
}: ChatWindowProps) {
  const t = useT();
  const { settings } = useSettings();
  const contentWidthClass = "w-full max-w-5xl mx-auto px-6";
  const [inputValue, setInputValue] = useState("");
  // Local per-tier timeframe overrides for the current source selection.
  // Initialized from settings when source selection opens; adjustable per session.
  const [localTimeframes, setLocalTimeframes] = useState<Record<string, string>>(
    () => ({ ...settings.inputParameters.sourceTimeframes }),
  );

  // Re-sync with settings whenever source selection opens.
  useEffect(() => {
    if (isSourceSelecting) {
      setLocalTimeframes({ ...settings.inputParameters.sourceTimeframes });
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isSourceSelecting]);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const bottomPanelRef = useRef<HTMLDivElement>(null);
  const [bottomPanelHeight, setBottomPanelHeight] = useState(160);

  useEffect(() => {
    const el = bottomPanelRef.current;
    if (!el) return;
    const observer = new ResizeObserver(() => {
      setBottomPanelHeight(el.offsetHeight);
    });
    observer.observe(el);
    setBottomPanelHeight(el.offsetHeight);
    return () => observer.disconnect();
  }, []);

  useEffect(() => {
    const el = textareaRef.current;
    if (!el) return;
    el.style.height = "auto";
    el.style.height = `${el.scrollHeight}px`;
  }, [inputValue]);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, isLoading]);

  useEffect(() => {
    if (!devPrefill) return;
    onDevPrefillConsumed?.();
    const id = setTimeout(() => {
      onSendMessage?.(devPrefill);
    }, 80);
    return () => clearTimeout(id);
  }, [devPrefill, onDevPrefillConsumed, onSendMessage]);

  useEffect(() => {
    if (!inputPrefill) return;
    onInputPrefillConsumed?.();
    setInputValue(inputPrefill);
    setTimeout(() => textareaRef.current?.focus(), 50);
  }, [inputPrefill, onInputPrefillConsumed]);

  const submitMessage = () => {
    if (inputValue.trim() === "") return;
    onSendMessage?.(inputValue);
    setInputValue("");
  };

  const handleSubmit = (event: React.SyntheticEvent) => {
    event.preventDefault();
    submitMessage();
  };

  const hasMessages = messages.length > 0;
  const hasAnalysisMessage = messages.some(
    (message) => message.type === "analysis" && message.data,
  );
  const isAnalysisComplete = hasAnalysisMessage;
  const hasConversationContent = hasMessages || isAnalysisComplete;
  const isEmptyStateComposer = !hasConversationContent;

  const inputPlaceholder =
    stage === "plan_confirming" && subState === "awaiting_modifications"
      ? t.placeholderPlanModify
      : stage === "reviewing" &&
          phase === "collection" &&
          subState === "awaiting_modifications"
        ? t.placeholderSummaryModify
        : stage === "reviewing" &&
            phase === "collection" &&
            subState === "awaiting_gather_more"
          ? t.placeholderGatherMore
          : t.placeholderDefault;

  const collectionRunMap = useMemo(() => {
    const map = new Map<string, number>();
    let count = 0;
    for (const msg of messages) {
      if (
        msg.type === "collection" &&
        msg.data &&
        "collected_data" in (msg.data as object)
      ) {
        count++;
        map.set(msg.id, count);
      }
    }
    return map;
  }, [messages]);

  function renderMessageContent(message: Message) {
    if (
      message.type === "summary" &&
      message.data &&
      typeof message.data === "object" &&
      "summary" in message.data
    ) {
      return (
        <div className="space-y-2">
          <h3 className="font-semibold">Direction Summary</h3>
          <p className="text-sm text-text-secondary leading-relaxed">
            {(message.data as { summary: string }).summary}
          </p>
          <p className="text-xs text-text-muted italic">
            Review this summary and approve to continue to PIR generation, or
            reject to refine.
          </p>
        </div>
      );
    }

    if (message.type === "pir" && message.data && "pir_text" in message.data) {
      return <PirMessage pirData={message.data as PirData} />;
    }

    if (message.type === "plan" && message.data && "plan" in message.data) {
      return (
        <CollectionPlanMessage planData={message.data as CollectionPlanData} />
      );
    }

    if (message.type === "suggested_sources" && Array.isArray(message.data)) {
      return (
        <SuggestedSourcesMessage
          sources={message.data as SuggestedSourcesData}
        />
      );
    }

    if (
      message.type === "processing" &&
      message.data &&
      "findings" in message.data
    ) {
      return (
        <ProcessingMessage
          data={message.data as ProcessingData}
          onGapCollect={onGapCollect ? (gap) => onSendMessage?.(gap) : undefined}
          onCollectMore={isConfirming ? onGatherMoreFromProcessing : undefined}
        />
      );
    }

    if (
      message.type === "collection" &&
      message.data &&
      "collected_data" in message.data
    ) {
      return (
        <CollectionDisplayMessage
          data={message.data as CollectionDisplayData}
          runNumber={collectionRunMap.get(message.id) ?? 1}
        />
      );
    }

    if (
      message.type === "collection" &&
      message.data &&
      typeof message.data === "object" &&
      "sources_used" in message.data
    ) {
      return (
        <CollectionSummaryMessage
          data={message.data as CollectionSummaryData}
        />
      );
    }

    if (message.type === "processing") {
      return <p>{message.text}</p>;
    }

    return <p>{message.text}</p>;
  }

  return (
    <div className="flex-1 min-h-0 w-full relative flex flex-col">
      {hasConversationContent && (
        <div className="absolute inset-0 overflow-y-auto py-4" style={{ paddingBottom: bottomPanelHeight + 24 }}>
          <div className={`${contentWidthClass} flex flex-col`}>
            {messages.map((message) => (
              <div
                key={message.id}
                data-sender={message.sender}
                className={`p-3 rounded-lg mb-2 ${
                  message.sender === "user"
                    ? "self-end max-w-[75%]"
                    : message.type === "processing"
                      ? "self-start w-full bg-surface border border-border/50 text-text-primary"
                      : "self-start max-w-[75%] bg-surface border border-border/50 text-text-primary"
                }`}
                style={
                  message.sender === "user"
                    ? {
                        background: "var(--color-user-bubble)",
                        color: "var(--color-user-bubble-text)",
                      }
                    : undefined
                }
              >
                {renderMessageContent(message)}
              </div>
            ))}
            {isLoading && (
              <div className="self-start w-full mb-2">
                <div className="bg-surface border border-border/50 rounded-lg px-4 py-3 flex items-center gap-3">
                  <div className="flex items-center gap-1 shrink-0">
                    <span className="w-1.5 h-1.5 bg-primary rounded-full animate-bounce [animation-delay:0ms]" />
                    <span className="w-1.5 h-1.5 bg-primary rounded-full animate-bounce [animation-delay:150ms]" />
                    <span className="w-1.5 h-1.5 bg-primary rounded-full animate-bounce [animation-delay:300ms]" />
                  </div>
                  <p className="text-sm text-text-secondary">
                    {phase === "processing"
                      ? "Processing collection data, this may take a moment…"
                      : phase === "analysis"
                        ? "Generating analysis…"
                        : phase === "collection"
                          ? stage === "plan_confirming" || stage === "planning"
                            ? "Updating collection plan…"
                            : "Collecting intelligence…"
                          : "Working…"}
                  </p>
                </div>
              </div>
            )}
          </div>
          {isAnalysisComplete && (
            <div className={`${contentWidthClass} mt-4`}>
              <section className="rounded-xl border border-border/50 bg-surface p-4 shadow-sm">
                <AnalysisWorkspace />
              </section>
            </div>
          )}
          <div ref={messagesEndRef} />
        </div>
      )}

      {!isAnalysisComplete && (
        <div
          ref={bottomPanelRef}
          className={`flex flex-col items-center gap-4 pb-6 ${
            hasConversationContent
              ? "absolute bottom-0 left-0 right-0 pt-8 bg-linear-to-t from-surface-elevated via-surface-elevated/90 to-transparent"
              : "flex-1 justify-center"
          }`}
        >
          {!hasConversationContent && (
            <p className="text-2xl font-normal text-text-secondary text-center">
              {t.readyToStart}
            </p>
          )}

          <div className="w-full max-w-5xl px-6">
            <div className="relative">
{isSourceSelecting ? (
                <section className="rounded-lg border border-border bg-surface p-4">
                  <h3 className="text-sm font-semibold text-text-primary">
                    {t.selectSourcesHeader}
                  </h3>
                  <p className="mt-0.5 text-xs text-text-secondary">
                    {t.selectSourcesSubtitle}
                  </p>

                  {availableSources.length === 0 ? (
                    <p className="mt-3 text-xs text-text-secondary">
                      {t.noSourceSuggestionsAvailable}
                    </p>
                  ) : (
                    <div className="mt-3 grid grid-cols-2 gap-2">
                      {[...availableSources]
                        .sort((a, b) => a.localeCompare(b))
                        .map((source) => {
                          const isActive = selectedSources.includes(source);
                          const displayName = t.sourceNames[source] ?? source;
                          const description = t.sourceDescriptions[source];
                          return (
                            <button
                              key={source}
                              type="button"
                              onClick={() => onToggleSourceSelection?.(source)}
                              disabled={isLoading}
                              aria-pressed={isActive}
                              className={`flex items-start gap-3 rounded-lg border p-3 text-left transition-all active:scale-[0.98] disabled:cursor-not-allowed disabled:opacity-50 ${
                                isActive
                                  ? "border-primary bg-primary-subtle hover:border-primary-dark hover:bg-primary-subtle"
                                  : "border-border bg-surface hover:border-primary hover:bg-primary-subtle/40"
                              }`}
                            >
                              <span
                                className={`mt-0.5 flex h-4 w-4 shrink-0 items-center justify-center rounded border transition-colors ${
                                  isActive
                                    ? "border-primary bg-primary text-text-inverse"
                                    : "border-border bg-surface"
                                }`}
                              >
                                {isActive && (
                                  <svg
                                    width="10"
                                    height="10"
                                    viewBox="0 0 10 10"
                                    fill="none"
                                  >
                                    <path
                                      d="M1.5 5L4 7.5L8.5 2.5"
                                      stroke="currentColor"
                                      strokeWidth="1.5"
                                      strokeLinecap="round"
                                      strokeLinejoin="round"
                                    />
                                  </svg>
                                )}
                              </span>
                              <span className="min-w-0">
                                <span
                                  className={`block text-sm font-semibold leading-tight ${isActive ? "text-primary" : "text-text-primary"}`}
                                >
                                  {displayName}
                                </span>
                                {description && (
                                  <span
                                    className={`mt-0.5 block text-xs leading-tight ${isActive ? "text-primary/70" : "text-text-secondary"}`}
                                  >
                                    {description}
                                  </span>
                                )}
                              </span>
                            </button>
                          );
                        })}
                    </div>
                  )}

                  {/* Date windows — per-tier timeframe overrides, pre-filled from settings */}
                  <div className="mt-4 border-t border-border pt-3">
                    <p className="text-xs font-semibold text-text-secondary mb-2">
                      {t.dateWindowsLabel}
                    </p>
                    <p className="text-xs text-text-muted mb-3">{t.dateWindowsDesc}</p>
                    <div className="grid grid-cols-2 gap-x-4 gap-y-3">
                      {(Object.keys(t.sourceTimeframeLabels) as (keyof SourceTimeframes)[]).map((key) => (
                        <div key={key} className="flex flex-col gap-1">
                          <span className="text-xs text-text-secondary">
                            {t.sourceTimeframeLabels[key]}
                          </span>
                          <select
                            value={localTimeframes[key] ?? ""}
                            onChange={(e) =>
                              setLocalTimeframes((prev) => ({ ...prev, [key]: e.target.value }))
                            }
                            disabled={isLoading}
                            className="w-full rounded border border-border bg-surface px-2 py-1 text-xs text-text-primary focus:outline-none focus:ring-1 focus:ring-primary disabled:opacity-50"
                          >
                            {(Object.entries(t.timeframeOptions) as [string, string][]).map(
                              ([code, label]) => (
                                <option key={code} value={code}>
                                  {label}
                                </option>
                              ),
                            )}
                          </select>
                        </div>
                      ))}
                    </div>
                  </div>

                  <div className="mt-3 flex justify-end">
                    <button
                      type="button"
                      onClick={() => onSubmitSourceSelection?.(localTimeframes)}
                      disabled={
                        isLoading ||
                        availableSources.length === 0 ||
                        selectedSources.length === 0
                      }
                      className="rounded-lg bg-primary px-5 py-2 text-sm font-medium text-text-inverse hover:bg-primary-dark disabled:cursor-not-allowed disabled:opacity-40 transition-colors"
                    >
                      {t.startCollecting}
                    </button>
                  </div>
                </section>
              ) : isCollecting ? (
                <section className="rounded-lg border border-border bg-surface p-4">
                  <p className="text-xs font-semibold uppercase tracking-wider text-text-secondary mb-3">
                    {t.collecting}
                  </p>
                  {collectionStatus ? (
                    <ul className="flex flex-col gap-2">
                      {Object.entries(collectionStatus.sources).map(
                        ([source, info]) => {
                          const isActive =
                            collectionStatus.current_source === source;
                          const isDone = info.call_count > 0 && !isActive;
                          const showActivity =
                            isActive && collectionStatus.current_activity;
                          return (
                            <li key={source} className="flex flex-col gap-1">
                              <div className="flex items-center gap-3 text-sm">
                                <span
                                  className={`shrink-0 w-4 text-center font-medium ${
                                    isDone
                                      ? "text-success"
                                      : isActive
                                        ? "text-primary"
                                        : "text-text-muted"
                                  }`}
                                >
                                  {isDone ? "✓" : isActive ? "●" : "○"}
                                </span>
                                <span
                                  className={
                                    isDone
                                      ? "text-text-secondary"
                                      : isActive
                                        ? "text-text-primary font-medium"
                                        : "text-text-muted"
                                  }
                                >
                                  {source}
                                </span>
                                <span className="ml-auto text-xs text-text-muted tabular-nums">
                                  {info.call_count > 0
                                    ? `${info.call_count} ${info.call_count !== 1 ? t.resultPlural : t.resultSingular}`
                                    : "—"}
                                </span>
                                {isActive && !showActivity && (
                                  <span className="flex gap-0.5">
                                    <span className="w-1.5 h-1.5 rounded-full bg-primary animate-bounce [animation-delay:0ms]" />
                                    <span className="w-1.5 h-1.5 rounded-full bg-primary animate-bounce [animation-delay:150ms]" />
                                    <span className="w-1.5 h-1.5 rounded-full bg-primary animate-bounce [animation-delay:300ms]" />
                                  </span>
                                )}
                              </div>
                              {showActivity && (
                                <div className="flex items-center gap-2 pl-7 text-xs text-text-muted">
                                  <span>
                                    {collectionStatus.current_activity}
                                  </span>
                                  <span className="flex gap-0.5">
                                    <span className="w-1 h-1 rounded-full bg-text-muted animate-bounce [animation-delay:0ms]" />
                                    <span className="w-1 h-1 rounded-full bg-text-muted animate-bounce [animation-delay:150ms]" />
                                    <span className="w-1 h-1 rounded-full bg-text-muted animate-bounce [animation-delay:300ms]" />
                                  </span>
                                </div>
                              )}
                            </li>
                          );
                        },
                      )}
                    </ul>
                  ) : (
                    <p className="text-sm text-text-secondary">
                      {t.startingCollection}
                    </p>
                  )}
                </section>
              ) : isConfirming ? (
                phase === "processing" ? (
                  <section className="rounded-lg border border-border bg-surface p-4 space-y-3">
                    <div className="flex items-start justify-between gap-4">
                      <div className="min-w-0">
                        <h3 className="text-sm font-semibold text-text-primary">
                          Processing Review
                        </h3>
                        <p className="text-sm text-text-secondary">
                          Accept the analysis or go back to collect more data.
                        </p>
                      </div>
                      <div className="shrink-0 flex items-center gap-2">
                        <button
                          type="button"
                          onClick={() => onApprove?.()}
                          disabled={isLoading}
                          className="rounded-md bg-success px-4 py-2 text-sm font-medium text-text-inverse hover:bg-success-dark disabled:cursor-not-allowed disabled:opacity-50"
                        >
                          Accept
                        </button>
                        <button
                          type="button"
                          onClick={() => onGatherMoreFromProcessing?.()}
                          disabled={isLoading}
                          className="rounded-md bg-primary px-4 py-2 text-sm font-medium text-text-inverse hover:bg-primary-dark disabled:cursor-not-allowed disabled:opacity-50"
                        >
                          Collect More
                        </button>
                      </div>
                    </div>
                  </section>
                ) : phase === "collection" && stage === "reviewing" ? (
                  <section className="rounded-lg border border-border bg-surface p-4 space-y-3">
                    <div className="flex items-start justify-between gap-4">
                      <div className="min-w-0">
                        <h3 className="text-sm font-semibold text-text-primary">
                          Collection Review
                        </h3>
                        <p className="text-sm text-text-secondary">
                          Accept the collection, revise it, or gather more data.
                        </p>
                      </div>
                      <div className="shrink-0 flex items-center gap-2">
                        <button
                          type="button"
                          onClick={() => onApprove?.()}
                          disabled={isLoading}
                          className="rounded-md bg-success px-4 py-2 text-sm font-medium text-text-inverse hover:bg-success-dark disabled:cursor-not-allowed disabled:opacity-50"
                        >
                          Accept
                        </button>
                        <button
                          type="button"
                          onClick={() => onReject?.()}
                          disabled={isLoading}
                          className="rounded-md bg-error px-4 py-2 text-sm font-medium text-text-inverse hover:bg-error-dark disabled:cursor-not-allowed disabled:opacity-50"
                        >
                          Revise
                        </button>
                        <button
                          type="button"
                          onClick={() => onGatherMore?.()}
                          disabled={isLoading}
                          className="rounded-md bg-primary px-4 py-2 text-sm font-medium text-text-inverse hover:bg-primary-dark disabled:cursor-not-allowed disabled:opacity-50"
                        >
                          Collect More
                        </button>
                      </div>
                    </div>
                  </section>
                ) : (
                  <ApprovalPrompt
                    isLoading={isLoading}
                    stage={stage}
                    onApproveContinue={onApprove}
                    onRejectWithFeedback={() => onReject?.()}
                  />
                )
              ) : (
                <form
                  onSubmit={handleSubmit}
                  className={`flex items-center gap-2 border-2 border-border bg-surface shadow-sm ${
                    isEmptyStateComposer
                      ? "rounded-[22px] px-5 py-3"
                      : "rounded-xl px-3 py-2"
                  }`}
                >
                  <textarea
                    ref={textareaRef}
                    rows={1}
                    placeholder={inputPlaceholder}
                    value={inputValue}
                    onChange={(event) => setInputValue(event.target.value)}
                    onKeyDown={(e) => {
                      if (e.key === "Enter" && !e.shiftKey) {
                        e.preventDefault();
                        submitMessage();
                      }
                    }}
                    className={`flex-1 outline-none bg-transparent text-text-primary resize-none overflow-y-auto max-h-64 ${
                      isEmptyStateComposer ? "py-2 text-base" : "py-1"
                    }`}
                  />
                  <button
                    type="submit"
                    disabled={inputValue.trim() === ""}
                    aria-label={t.sendMessage}
                    className={`shrink-0 rounded-full transition-colors ${
                      isEmptyStateComposer ? "self-center p-3" : "self-end p-2"
                    } ${
                      inputValue.trim() === ""
                        ? "bg-surface-elevated text-text-muted cursor-not-allowed"
                        : "bg-primary text-text-inverse hover:bg-primary-dark"
                    }`}
                  >
                    <svg
                      width="20"
                      height="20"
                      viewBox="0 0 24 24"
                      fill="none"
                      stroke="currentColor"
                      strokeWidth="2.5"
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      aria-hidden="true"
                    >
                      <path d="M12 19V5M5 12l7-7 7 7" />
                    </svg>
                  </button>
                </form>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
