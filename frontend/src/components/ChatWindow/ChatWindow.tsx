import { useEffect, useRef, useState } from "react";
import type { ReactNode } from "react";
import { ToastContainer } from "../Toast";
import ApprovalPrompt from "../ApprovalPrompt/ApprovalPrompt";
import CitationText from "../CitationText/CitationText";
import SourceList from "../SourceList/SourceList";
import type { Message, PirData } from "../../types/conversation";
import type { DialogueStage } from "../../types/dialogue";

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

function renderWithBold(text: string): ReactNode {
  const parts = text.split(/\*\*(.*?)\*\*/g);
  return parts.map((part, i) =>
    i % 2 === 1 ? <strong key={i}>{part}</strong> : part,
  );
}

function PirMessage({ pirData }: { pirData: PirData }) {
  const [highlightedRef, setHighlightedRef] = useState<string | null>(null);

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
          pirText={pirData.pir_text}
          claims={pirData.claims}
          highlightedRef={highlightedRef}
          onRefHover={setHighlightedRef}
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
              <p className="mt-1 text-sm text-text-secondary">{pir.rationale}</p>
            </details>
          </li>
        ))}
      </ol>
      {pirData.sources && pirData.sources.length > 0 && (
        <div className="mt-3 border-t border-border pt-2">
          <p className="text-sm font-medium text-text-secondary mb-2">Sources</p>
          <SourceList
            sources={pirData.sources}
            highlightedRef={highlightedRef}
            onSourceHover={setHighlightedRef}
          />
        </div>
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
                {renderWithBold(point)}
              </p>
            ))}
          </div>
        </details>
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
  onApprove?: () => void;
  onReject?: () => void;
  devPrefill?: string | null;
  onDevPrefillConsumed?: () => void;
}

export default function ChatWindow({
  onSendMessage,
  messages = [],
  isConfirming = false,
  isLoading = false,
  stage,
  onApprove,
  onReject,
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

  function renderMessageContent(message: Message) {
    if (message.type === "summary" && message.data && "summary" in message.data) {
      return <p>{message.data.summary}</p>;
    }

    if (message.type === "pir" && message.data && "pir_text" in message.data) {
      return <PirMessage pirData={message.data as PirData} />;
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
            {isConfirming ? (
              <ApprovalPrompt
                isLoading={isLoading}
                stage={stage}
                onApproveContinue={onApprove}
                onRejectWithFeedback={() => onReject?.()}
              />
            ) : (
              <form
                onSubmit={handleSubmit}
                className="relative border-2 border-border rounded-xl p-3 pb-12"
              >
                <textarea
                  ref={textareaRef}
                  rows={1}
                  placeholder="Ask anything..."
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
