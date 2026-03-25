import { useEffect, useRef, useState } from "react";
import { ToastContainer } from "../Toast";
import ApprovalPrompt from "../ApprovalPrompt/ApprovalPrompt";
import CitationText from "../CitationText/CitationText";
import SourceList from "../SourceList/SourceList";
import type {
  CollectionDisplayData,
  CollectionPlanData,
  CollectionPlanStep,
  CollectionSourceSummary,
  CollectionSummaryData,
  Message,
  PirData,
  SuggestedSourcesData,
} from "../../types/conversation";
import type { DialogueStage, DialogueSubState } from "../../types/dialogue";
import { useWorkspace } from "../../contexts/WorkspaceContext/WorkspaceContext";

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


const PRIORITY_LABEL: Record<string, string> = {
  high: "High",
  medium: "Medium",
  low: "Low",
};




function PirMessage({ pirData }: { pirData: PirData }) {
  const { highlightedRefs, setHighlightedRefs, setPirData } = useWorkspace();

  useEffect(() => {
    setPirData(pirData);
  }, [pirData, setPirData]);

  const reasoningPoints = (pirData.reasoning ?? "")
    .split(/(?=\d+\.\s)/)
    .map((s) => s.trim())
    .filter(Boolean);

  return (
    <div className="space-y-2">
      <h3 className="font-semibold">
        Priority Intelligence Requirements (PIRs)
      </h3>
      {pirData.pir_text && (
        <CitationText
          text={pirData.pir_text}
          claims={pirData.claims}
          highlightedRefs={highlightedRefs}
          onRefHover={setHighlightedRefs}
        />
      )}
      <ol className="space-y-3 mt-1">
        {pirData.pirs.map((pir, i) => (
          <li key={i} className="flex flex-col gap-1">
            <span className="text-sm font-bold text-text-secondary uppercase tracking-wide">
              {i + 1}. {PRIORITY_LABEL[pir.priority]}
            </span>
            <p className="font-medium text-base leading-snug">{pir.question}</p>
            <details className="group pl-1">
              <summary className="cursor-pointer list-none text-sm text-text-muted hover:text-text-secondary select-none flex items-center">
                Rationale
                <Chevron />
              </summary>
              <p className="mt-1 text-sm text-text-secondary">
                <CitationText
                  text={pir.rationale}
                  claims={pirData.claims}
                  highlightedRefs={highlightedRefs}
                  onRefHover={setHighlightedRefs}
                />
              </p>
            </details>
          </li>
        ))}
      </ol>
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
              onSourceHover={setHighlightedRefs}
            />
          </div>
        </details>
      )}
      {reasoningPoints.length > 0 && (
        <details className="group mt-3 border-t border-border pt-2">
          <summary className="cursor-pointer list-none text-sm font-medium text-text-secondary hover:text-text-primary select-none flex items-center gap-1">
            Show reasoning
            <Chevron />
          </summary>
          <div className="mt-2 space-y-2 bg-surface-muted rounded-md p-2">
            {reasoningPoints.map((point, i) => (
              <p key={i} className="text-sm text-text-secondary">
                <CitationText
                  text={point}
                  claims={pirData.claims}
                  highlightedRefs={highlightedRefs}
                  onRefHover={setHighlightedRefs}
                />
              </p>
            ))}
          </div>
        </details>
      )}
    </div>
  );
}

function CollectionPlanMessage({ planData }: { planData: CollectionPlanData }) {
  return (
    <div className="space-y-3">
      <h3 className="font-semibold">Collection Plan</h3>

      {/* Structured steps — shown when the AI returns step breakdown */}
      {planData.steps && planData.steps.length > 0 ? (
        <div className="space-y-2">
          {planData.steps.map((step: CollectionPlanStep, index: number) => (
            <div
              key={index}
              className="rounded-lg border border-border-muted bg-surface px-3 py-2 space-y-0.5"
            >
              <p className="text-xs font-semibold text-text-primary">{step.title}</p>
              <p className="text-xs text-text-secondary">{step.description}</p>
            </div>
          ))}
        </div>
      ) : (
        /* Fallback to plain text if no steps */
        <p className="whitespace-pre-wrap text-sm text-text-primary">{planData.plan}</p>
      )}

      {planData.suggested_sources.length > 0 && (
        <div className="border-t border-border pt-2">
          <p className="text-sm font-medium text-text-secondary">Suggested sources</p>
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
  if (sources.length === 0) {
    return <p>No source suggestions were returned.</p>;
  }

  return (
    <div className="space-y-2">
      <h3 className="font-semibold">Suggested Sources</h3>
      <ul className="list-disc pl-5 text-sm text-text-secondary">
        {sources.map((source) => (
          <li key={source}>{source}</li>
        ))}
      </ul>
    </div>
  );
}

function CollectionSummaryMessage({
  data,
}: {
  data: CollectionSummaryData;
}) {
  return (
    <div className="space-y-3">
      <h3 className="font-semibold">Collection Summary</h3>
      <p className="whitespace-pre-wrap text-sm text-text-primary">{data.summary}</p>
      {data.sources_used.length > 0 && (
        <div className="border-t border-border pt-2">
          <p className="text-sm font-medium text-text-secondary">Sources used</p>
          <ul className="mt-1 list-disc pl-5 text-sm text-text-secondary">
            {data.sources_used.map((source) => (
              <li key={source}>{source}</li>
            ))}
          </ul>
        </div>
      )}
      <div className="border-t border-border pt-2">
        <p className="text-sm font-medium text-text-secondary">Gaps</p>
        <p className="mt-1 text-sm text-text-secondary">
          {data.gaps ?? "No gaps identified."}
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
  return (
    <section className="rounded-xl border-2 border-border bg-surface p-4">
      <h3 className="text-lg font-semibold text-text-primary">Collection Review</h3>
      <p className="mt-1 text-sm text-text-secondary">
        Accept the collected data or collect more from additional sources.
      </p>

      <div className="mt-4 flex flex-wrap items-center gap-3">
        <button
          type="button"
          onClick={() => onAccept?.()}
          disabled={isLoading}
          className="rounded-lg bg-success px-4 py-2 text-text-inverse hover:bg-success-dark disabled:cursor-not-allowed disabled:opacity-50"
        >
          Accept
        </button>

        <button
          type="button"
          onClick={() => onGatherMore?.()}
          disabled={isLoading}
          className="rounded-lg bg-primary px-4 py-2 text-text-inverse hover:bg-primary-dark disabled:cursor-not-allowed disabled:opacity-50"
        >
          Collect More Data
        </button>
      </div>
    </section>
  );
}

interface ChatWindowProps {
  onSendMessage?: (message: string) => void;
  messages?: Message[];
  isConfirming?: boolean;
  isLoading?: boolean;
  stage?: DialogueStage;
  subState?: DialogueSubState;
  onApprove?: () => void;
  onReject?: () => void;
  onGatherMore?: () => void;
  isSourceSelecting?: boolean;
  isCollecting?: boolean;
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
  if (summaries.length === 0) return null;
  return (
    <div className="overflow-x-auto rounded border border-border-muted">
      <table className="min-w-full text-sm">
        <thead className="bg-surface-muted">
          <tr>
            <th className="text-left px-3 py-1.5 font-medium text-text-secondary">Source</th>
            <th className="text-right px-3 py-1.5 font-medium text-text-secondary">Items</th>
            <th className="text-left px-3 py-1.5 font-medium text-text-secondary">Resources</th>
            <th className="text-left px-3 py-1.5 font-medium text-text-secondary">Status</th>
          </tr>
        </thead>
        <tbody>
          {summaries.map((s) => (
            <tr key={s.display_name} className="border-t border-border-muted">
              <td className="px-3 py-1.5 font-medium text-text-primary">{s.display_name}</td>
              <td className="px-3 py-1.5 text-right text-text-secondary">{s.count}</td>
              <td className="px-3 py-1.5 text-xs text-text-muted">
                {s.resource_ids.length > 0 ? s.resource_ids.join(", ") : "—"}
              </td>
              <td className="px-3 py-1.5">
                <span
                  className={`inline-block w-2 h-2 rounded-full mr-1.5 ${
                    s.has_content ? "bg-success" : "bg-warning-dark"
                  }`}
                />
                <span className="text-xs text-text-secondary">
                  {s.has_content ? "Data found" : "Empty"}
                </span>
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
}: {
  data: CollectionDisplayData;
}) {
  const { setCollectionData, setActivePhase } = useWorkspace();

  useEffect(() => {
    setCollectionData(data);
    setActivePhase("collection");
  }, [data, setCollectionData, setActivePhase]);

  if (data.parse_error) {
    return (
      <div className="space-y-2">
        <h3 className="font-semibold">Collection Results</h3>
        <p className="text-sm text-error-text">Could not parse collection output.</p>
        <details className="group">
          <summary className="cursor-pointer list-none text-xs text-text-muted hover:text-text-secondary select-none flex items-center gap-1">
            Raw output <Chevron />
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
      <h3 className="font-semibold">Collection Results</h3>
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
  subState,
  onApprove,
  onReject,
  onGatherMore,
  isSourceSelecting = false,
  isCollecting = false,
  availableSources = [],
  selectedSources = [],
  onToggleSourceSelection,
  onSubmitSourceSelection,
  devPrefill,
  onDevPrefillConsumed,
}: ChatWindowProps) {
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
    setInputValue(devPrefill);
    onDevPrefillConsumed?.();
    const id = setTimeout(() => {
      onSendMessage?.(devPrefill);
      setInputValue("");
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

  const inputPlaceholder =
    stage === "plan_confirming" && subState === "awaiting_modifications"
      ? "Describe the changes you want in the collection plan..."
      : stage === "reviewing" && subState === "awaiting_modifications"
      ? "Describe how to modify the collection summary..."
      : stage === "reviewing" && subState === "awaiting_gather_more"
      ? "Describe what to gather more information about..."
      : "Ask anything...";

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
      return <CollectionPlanMessage planData={message.data as CollectionPlanData} />;
    }

    if (
      message.type === "suggested_sources" &&
      Array.isArray(message.data)
    ) {
      return <SuggestedSourcesMessage sources={message.data as SuggestedSourcesData} />;
    }

    if (
      message.type === "collection" &&
      message.data &&
      "collected_data" in message.data
    ) {
      return <CollectionDisplayMessage data={message.data as CollectionDisplayData} />;
    }

    if (
      message.type === "collection" &&
      message.data &&
      typeof message.data === "object" &&
      "sources_used" in message.data
    ) {
      return (
        <CollectionSummaryMessage data={message.data as CollectionSummaryData} />
      );
    }

    return <p>{message.text}</p>;
  }

  return (
    <div className="h-full w-full flex flex-col">
      {hasMessages && (
        <div className="flex-1 min-h-0 overflow-y-auto py-4">
          <div className="w-full max-w-3xl mx-auto px-6 flex flex-col">
            {messages.map((message) => (
              <div
                key={message.id}
                data-sender={message.sender}
                className={`max-w-[75%] p-3 rounded-lg mb-2 ${
                  message.sender === "user"
                    ? "self-end bg-primary text-text-inverse"
                    : "self-start bg-surface-muted text-text-primary"
                }`}
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
            <div ref={messagesEndRef} />
          </div>
        </div>
      )}

      <div
        className={`flex flex-col items-center gap-4 pb-6 ${
          hasMessages ? "pt-2" : "flex-1 justify-center"
        }`}
      >
        {!hasMessages && (
          <p className="text-2xl font-normal text-text-secondary text-center">
            Ready to start?
          </p>
        )}

        <div className="w-full max-w-3xl px-6">
          <div className="relative">
            <ToastContainer position="above-input" />
            {isSourceSelecting ? (
              <section className="rounded-xl border-2 border-gray-300 bg-white p-4">
                <h3 className="text-lg font-semibold text-gray-800">Select Sources</h3>
                <p className="mt-1 text-sm text-gray-600">
                  Choose one or more data sources before collection starts.
                </p>

                {availableSources.length === 0 ? (
                  <p className="mt-4 text-sm text-gray-600">
                    No source suggestions available.
                  </p>
                ) : (
                  <div className="mt-4 space-y-2">
                    {availableSources.map((source) => (
                      <label
                        key={source}
                        className="flex items-center gap-2 text-sm text-gray-700"
                      >
                        <input
                          type="checkbox"
                          checked={selectedSources.includes(source)}
                          onChange={() => onToggleSourceSelection?.(source)}
                          disabled={isLoading}
                        />
                        {source}
                      </label>
                    ))}
                  </div>
                )}

                <button
                  type="button"
                  onClick={() => onSubmitSourceSelection?.()}
                  disabled={
                    isLoading ||
                    availableSources.length === 0 ||
                    selectedSources.length === 0
                  }
                  className="mt-4 rounded-lg bg-blue-600 px-4 py-2 text-white hover:bg-blue-700 disabled:cursor-not-allowed disabled:opacity-50"
                >
                  Start Collecting
                </button>
              </section>
            ) : isCollecting ? (
              <section className="rounded-xl border-2 border-gray-300 bg-white p-4">
                <h3 className="text-lg font-semibold text-gray-800">Collecting Data</h3>
                <p className="mt-1 text-sm text-gray-600">
                  The system is collecting and reviewing data from the selected sources.
                </p>
              </section>
            ) : isConfirming ? (
              stage === "reviewing" ? (
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
                className="relative border-2 border-border rounded-xl p-3 pb-12"
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
                  className="w-full pl-1 pr-2 py-1 outline-none bg-transparent text-text-primary resize-none overflow-y-auto max-h-64"
                />
                <button
                  type="submit"
                  disabled={inputValue.trim() === ""}
                  aria-label="Send message"
                  className={`absolute bottom-2 right-2 p-2 rounded-full transition-colors ${
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
    </div>
  );
}
