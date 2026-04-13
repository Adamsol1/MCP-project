import { useEffect, useRef, useState } from "react";
import { ToastContainer } from "../Toast";
import { useT } from "../../i18n/useT";
import ApprovalPrompt from "../ApprovalPrompt/ApprovalPrompt";
import CitationText from "../CitationText/CitationText";
import SourceList from "../SourceList/SourceList";
import AnalysisPrototypeView from "../AnalysisPrototypeView/AnalysisPrototypeView";
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

  useEffect(() => {
    setPirData(pirData);
  }, [pirData, setPirData]);

  const handleHoveredRefs = (value: string[] | string | null) => {
    setHighlightedRefs(Array.isArray(value) ? value : value ? [value] : []);
  };

  const reasoningPoints = (pirData.reasoning ?? "")
    .split(/(?=\d+\.\s)/)
    .map((s) => s.trim())
    .filter(Boolean);

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
        {pirData.pirs.map((pir, i) => (
          <div
            key={i}
            className="rounded-lg border border-border-muted bg-surface px-3 py-2.5 space-y-1"
          >
            <div className="flex items-center gap-2">
              <span className="flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-primary/10 text-xs font-bold text-primary">
                {i + 1}
              </span>
              <p className="text-sm font-semibold text-text-primary leading-tight flex-1">
                {pir.question}
              </p>
              <span
                className={`ml-auto shrink-0 rounded px-1.5 py-0.5 text-xs font-semibold uppercase ${PRIORITY_COLOR[pir.priority] ?? "text-text-muted"} bg-surface-muted`}
              >
                {PRIORITY_LABEL[pir.priority] ?? pir.priority}
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
      {pirData.sources && pirData.sources.length > 0 && (
        <details className="group mt-3 border-t border-border pt-2" open>
          <summary className="cursor-pointer list-none text-xs font-medium uppercase tracking-wider text-text-muted hover:text-text-secondary select-none flex items-center gap-1">
            Sources ({pirData.sources.length})
            <Chevron />
          </summary>
          <div className="mt-1.5">
            <SourceList
              sources={pirData.sources}
              highlightedRefs={highlightedRefs}
              onSourceHover={handleHoveredRefs}
            />
          </div>
        </details>
      )}
      {reasoningPoints.length > 0 && (
        <details className="group mt-3 border-t border-border pt-2">
          <summary className="cursor-pointer list-none text-sm font-medium text-text-secondary hover:text-text-primary select-none flex items-center gap-1">
            {t.showReasoning}
            <Chevron />
          </summary>
          <ol className="mt-2 space-y-3 bg-surface-muted rounded-md p-3 list-none">
            {reasoningPoints.map((point, i) => (
              <li
                key={i}
                className="text-sm text-text-secondary leading-relaxed flex gap-2"
              >
                <span className="shrink-0 w-5 h-5 rounded-full bg-border/60 flex items-center justify-center text-[10px] font-bold text-text-muted mt-0.5">
                  {i + 1}
                </span>
                <div className="flex-1">
                  <CitationText
                    text={point.replace(/^\d+\.\s*/, "")}
                    claims={pirData.claims}
                    highlightedRefs={highlightedRefs}
                    onRefHover={handleHoveredRefs}
                  />
                </div>
              </li>
            ))}
          </ol>
        </details>
      )}
    </div>
  );
}

function CollectionPlanMessage({ planData }: { planData: CollectionPlanData }) {
  const t = useT();
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
                className="rounded-lg border border-border-muted bg-surface px-3 py-2.5 space-y-1"
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

      {planData.suggested_sources.length > 0 && (
        <div className="border-t border-border pt-2">
          <p className="text-sm font-medium text-text-secondary">
            {t.suggestedSources}
          </p>
          <ul className="mt-1 list-disc pl-5 text-sm text-text-secondary">
            {planData.suggested_sources.map((source) => (
              <li key={source}>{source}</li>
            ))}
          </ul>
        </div>
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
        <div className="border-t border-border pt-2">
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
      <div className="border-t border-border pt-2">
        <p className="text-sm font-medium text-text-secondary">{t.gaps}</p>
        <p className="mt-1 text-sm text-text-secondary">
          {data.gaps ?? t.noGapsIdentified}
        </p>
      </div>
    </div>
  );
}

function CollectionReviewPrompt({
  isLoading,
  onAccept,
  onGatherMore,
}: {
  isLoading: boolean;
  onAccept?: () => void;
  onGatherMore?: () => void;
}) {
  const t = useT();
  return (
    <section className="rounded-lg border border-border bg-surface p-4 flex items-center gap-4">
      <div className="flex-1 min-w-0">
        <h3 className="text-sm font-semibold text-text-primary">
          {t.collectionReviewHeader}
        </h3>
        <p className="text-sm text-text-secondary">
          {t.collectionReviewSubtitle}
        </p>
      </div>

      <div className="shrink-0 flex items-center gap-2">
        <button
          type="button"
          onClick={() => onAccept?.()}
          disabled={isLoading}
          className="rounded-md bg-success px-4 py-2 text-sm font-medium text-text-inverse hover:bg-success-dark disabled:cursor-not-allowed disabled:opacity-50"
        >
          {t.accept}
        </button>

        <button
          type="button"
          onClick={() => onGatherMore?.()}
          disabled={isLoading}
          className="rounded-md bg-primary px-4 py-2 text-sm font-medium text-text-inverse hover:bg-primary-dark disabled:cursor-not-allowed disabled:opacity-50"
        >
          {t.collectMoreData}
        </button>
      </div>
    </section>
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
  high:     "bg-emerald-600 text-white",
  moderate: "bg-amber-500 text-white",
  low:      "bg-red-600 text-white",
};

const SOURCE_DISPLAY_NAMES: Record<string, string> = {
  knowledge_bank: "Internal Knowledge Bank",
  otx:            "AlienVault OTX",
  web_gov:        "Government / Official",
  web_think_tank: "Think Tank",
  web_news:       "News",
  web_search:     "Web Search",
  web_other:      "Web",
  pretrained:     "Pretrained Knowledge",
  osint:          "OSINT",
};

function FindingConfidenceBadge({ f }: { f: ProcessingData["findings"][number] }) {
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!open) return;
    const handler = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false);
    };
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, [open]);

  const tier = confidenceTierFromInt(f.confidence);
  const tierStyle = FINDING_TIER_STYLES[tier];
  const sourceLabel = SOURCE_DISPLAY_NAMES[f.source] ?? f.source;

  const sd = f.supporting_data ?? {};
  const hasDetails =
    (sd.kb_refs?.length ?? 0) > 0 ||
    (sd.attack_ids?.length ?? 0) > 0 ||
    (sd.entities?.length ?? 0) > 0 ||
    (sd.domains?.length ?? 0) > 0 ||
    (f.uncertainties?.length ?? 0) > 0;

  return (
    <div className="relative shrink-0" ref={ref}>
      <button
        onClick={() => setOpen((v) => !v)}
        className={`flex items-center gap-1 rounded px-1.5 py-0.5 text-xs font-semibold cursor-pointer transition-opacity hover:opacity-80 ${tierStyle}`}
        title="Click for source details"
      >
        <span>{tier.toUpperCase()}</span>
        <span className="opacity-70 font-normal">{f.confidence}%</span>
      </button>

      {open && (
        <div className="absolute right-0 top-full mt-1 z-50 w-64 rounded-lg border border-border bg-surface shadow-xl p-3 space-y-2.5 text-xs">
          <p className="font-semibold text-text-primary text-sm">Confidence Details</p>

          <div className="flex items-center justify-between">
            <span className="text-text-muted">AI confidence</span>
            <span className="font-medium">{f.confidence}%</span>
          </div>

          <div className="flex items-center justify-between">
            <span className="text-text-muted">Source type</span>
            <span className="font-medium">{sourceLabel}</span>
          </div>

          {hasDetails && (
            <div className="border-t border-border-muted pt-2 space-y-2">
              {(sd.kb_refs?.length ?? 0) > 0 && (
                <div>
                  <p className="font-medium text-text-secondary mb-0.5">Knowledge base refs</p>
                  <div className="flex flex-wrap gap-1">
                    {sd.kb_refs!.map((r) => (
                      <span key={r} className="rounded border border-border-muted bg-surface-muted px-1.5 py-0.5 font-mono text-[11px] text-text-primary">
                        {r}
                      </span>
                    ))}
                  </div>
                </div>
              )}
              {(sd.attack_ids?.length ?? 0) > 0 && (
                <div>
                  <p className="font-medium text-text-secondary mb-0.5">ATT&CK techniques</p>
                  <div className="flex flex-wrap gap-1">
                    {sd.attack_ids!.map((id) => (
                      <span key={id} className="rounded border border-border-muted bg-surface-muted px-1.5 py-0.5 font-mono text-[11px] text-text-primary">
                        {id}
                      </span>
                    ))}
                  </div>
                </div>
              )}
              {(sd.entities?.length ?? 0) > 0 && (
                <div>
                  <p className="font-medium text-text-secondary mb-0.5">Entities</p>
                  <p className="text-text-primary">{sd.entities!.join(", ")}</p>
                </div>
              )}
              {(sd.domains?.length ?? 0) > 0 && (
                <div>
                  <p className="font-medium text-text-secondary mb-0.5">Domains</p>
                  <div className="flex flex-wrap gap-1">
                    {sd.domains!.map((d) => (
                      <span key={d} className="rounded border border-border-muted bg-surface-muted px-1.5 py-0.5 font-mono text-[10px] text-text-primary">
                        {d}
                      </span>
                    ))}
                  </div>
                </div>
              )}
              {(f.uncertainties?.length ?? 0) > 0 && (
                <div>
                  <p className="font-medium text-text-secondary mb-0.5">Uncertainties</p>
                  <ul className="list-disc pl-3 space-y-0.5 text-text-primary">
                    {f.uncertainties.map((u, i) => (
                      <li key={i}>{u}</li>
                    ))}
                  </ul>
                </div>
              )}
            </div>
          )}

          <p className="border-t border-border-muted pt-2 text-text-muted italic">
            Full source breakdown (OTX, web) available in the Analysis view after processing.
          </p>
        </div>
      )}
    </div>
  );
}

function ProcessingMessage({ data }: { data: ProcessingData }) {
  return (
    <div className="space-y-3">
      <h3 className="font-semibold">Processing Results</h3>
      <details className="group" open>
        <summary className="cursor-pointer list-none text-sm font-medium text-text-secondary hover:text-text-primary select-none flex items-center gap-1">
          {data.findings.length} findings <Chevron />
        </summary>
        <div className="mt-2 space-y-2">
          {data.findings.map((f) => (
            <div
              key={f.id}
              className="rounded border border-border-muted bg-surface px-3 py-2 text-sm"
            >
              <div className="flex items-start justify-between gap-2">
                <p className="font-medium text-text-primary leading-snug">{f.title}</p>
                <FindingConfidenceBadge f={f} />
              </div>
              <p className="text-xs text-text-secondary mt-1">{f.finding}</p>
              {f.why_it_matters && (
                <p className="text-xs text-text-muted mt-1 italic">
                  {f.why_it_matters}
                </p>
              )}
              <p className="text-xs text-text-muted mt-1">
                {f.relevant_to.join(", ")} · {f.source}
              </p>
            </div>
          ))}
        </div>
      </details>
      {data.gaps.length > 0 && (
        <div className="border-t border-border pt-2">
          <p className="text-sm font-medium text-text-secondary">Gaps</p>
          <ul className="mt-1 list-disc pl-5 text-sm text-text-muted">
            {data.gaps.map((gap, i) => (
              <li key={i}>{gap}</li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}

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
  onSubmitSourceSelection?: () => void;
  devPrefill?: string | null;
  onDevPrefillConsumed?: () => void;
}

function SourceSummaryTable({
  summaries,
}: {
  summaries: CollectionSourceSummary[];
}) {
  const t = useT();
  if (summaries.length === 0) return null;
  return (
    <div className="overflow-x-auto rounded border border-border-muted">
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
            <tr key={s.display_name} className="border-t border-border-muted">
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

function CollectionDisplayMessage({ data }: { data: CollectionDisplayData }) {
  const { setCollectionData } = useWorkspace();
  const t = useT();

  useEffect(() => {
    setCollectionData(data);
  }, [data, setCollectionData]);

  if (data.parse_error) {
    return (
      <div className="space-y-2">
        <h3 className="font-semibold">{t.collectionResultsHeader}</h3>
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
      <h3 className="font-semibold">{t.collectionResultsHeader}</h3>
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
}: ChatWindowProps) {
  const t = useT();
  const contentWidthClass = "w-full max-w-5xl mx-auto px-6";
  const [inputValue, setInputValue] = useState("");
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);

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
  const isAnalysisComplete = stage === "complete";
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

  function renderMessageContent(message: Message) {
    if (
      message.type === "summary" &&
      message.data &&
      typeof message.data === "object" &&
      "summary" in message.data
    ) {
      return <p>{message.data.summary}</p>;
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
      return <ProcessingMessage data={message.data as ProcessingData} />;
    }

    if (
      message.type === "collection" &&
      message.data &&
      "collected_data" in message.data
    ) {
      return (
        <CollectionDisplayMessage
          data={message.data as CollectionDisplayData}
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
    <div className="flex-1 min-h-0 w-full flex flex-col">
      {hasConversationContent && (
        <div className="flex-1 min-h-0 overflow-y-auto py-4">
          <div className={`${contentWidthClass} flex flex-col`}>
            {messages.map((message) => (
              <div
                key={message.id}
                data-sender={message.sender}
                className={`max-w-[75%] p-3 rounded-lg mb-2 ${
                  message.sender === "user"
                    ? "self-end"
                    : "self-start bg-surface-muted text-text-primary"
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
              <div className="self-start bg-surface-muted rounded-lg p-3 mb-2">
                <div className="flex items-center gap-1">
                  <span className="w-2 h-2 bg-text-muted rounded-full animate-bounce" />
                  <span className="w-2 h-2 bg-text-muted rounded-full animate-bounce [animation-delay:150ms]" />
                  <span className="w-2 h-2 bg-text-muted rounded-full animate-bounce [animation-delay:300ms]" />
                </div>
              </div>
            )}
          </div>
          {isAnalysisComplete && (
            <div className={`${contentWidthClass} mt-4`}>
              <section className="rounded-xl border border-border-muted bg-surface p-4 shadow-sm">
                <AnalysisPrototypeView />
              </section>
            </div>
          )}
          <div ref={messagesEndRef} />
        </div>
      )}

      {!isAnalysisComplete && (
        <div
          className={`flex flex-col items-center gap-4 pb-6 ${
            hasConversationContent ? "pt-2" : "flex-1 justify-center"
          }`}
        >
          {!hasConversationContent && (
            <p className="text-2xl font-normal text-text-secondary text-center">
              {t.readyToStart}
            </p>
          )}

          <div
            className={`w-full px-6 ${
              isEmptyStateComposer ? "max-w-4xl" : "max-w-3xl"
            }`}
          >
            <div className="relative">
              <ToastContainer position="above-input" />
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

                  <div className="mt-3 flex justify-end">
                    <button
                      type="button"
                      onClick={() => onSubmitSourceSelection?.()}
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
                stage === "processing" ||
                (stage === "reviewing" && phase === "processing") ? (
                  <section className="rounded-lg border border-border bg-surface p-4 flex items-center gap-4">
                    <div className="flex-1 min-w-0">
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
                        Gather More
                      </button>
                    </div>
                  </section>
                ) : stage === "reviewing" && phase === "collection" ? (
                  <CollectionReviewPrompt
                    isLoading={isLoading}
                    onAccept={onApprove}
                    onGatherMore={onGatherMore}
                  />
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
