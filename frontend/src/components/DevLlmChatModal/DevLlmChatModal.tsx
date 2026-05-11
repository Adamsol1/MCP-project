import { useEffect, useMemo, useRef, useState } from "react";
import type { FormEvent } from "react";
import {
  sendDevLlmChat,
  type DevLlmChatMessage,
} from "../../services/devLlmChat/devLlmChat";
import type { AiProvider } from "../../types/settings";

interface DevLlmChatModalProps {
  isOpen: boolean;
  onClose: () => void;
  aiProvider: AiProvider;
}

const DEFAULT_SYSTEM_PROMPT =
  "You are in a developer test chat. Answer directly and briefly unless asked for detail.";

export function DevLlmChatModal({
  isOpen,
  onClose,
  aiProvider,
}: DevLlmChatModalProps) {
  const [messages, setMessages] = useState<DevLlmChatMessage[]>([]);
  const [input, setInput] = useState("");
  const [systemPrompt, setSystemPrompt] = useState(DEFAULT_SYSTEM_PROMPT);
  const [model, setModel] = useState("");
  const [isSending, setIsSending] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [lastRun, setLastRun] = useState<{
    provider: string;
    model: string;
  } | null>(null);
  const transcriptRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    if (transcriptRef.current) {
      transcriptRef.current.scrollTop = transcriptRef.current.scrollHeight;
    }
  }, [messages, isSending]);

  const requestMessages = useMemo(() => {
    const trimmedSystemPrompt = systemPrompt.trim();
    return [
      ...(trimmedSystemPrompt
        ? [{ role: "system" as const, content: trimmedSystemPrompt }]
        : []),
      ...messages,
    ];
  }, [messages, systemPrompt]);

  if (!isOpen) return null;

  const sendCurrentMessage = async () => {
    const content = input.trim();
    if (!content || isSending) return;

    const nextMessages: DevLlmChatMessage[] = [
      ...messages,
      { role: "user", content },
    ];
    setMessages(nextMessages);
    setInput("");
    setError(null);
    setIsSending(true);

    try {
      const response = await sendDevLlmChat(
        [
          ...(systemPrompt.trim()
            ? [{ role: "system" as const, content: systemPrompt.trim() }]
            : []),
          ...nextMessages,
        ],
        aiProvider,
        model,
      );
      setMessages((current) => [
        ...current,
        { role: "assistant", content: response.message },
      ]);
      setLastRun({ provider: response.provider, model: response.model });
    } catch (sendError) {
      const message =
        sendError instanceof Error ? sendError.message : "LLM request failed";
      setError(message);
    } finally {
      setIsSending(false);
    }
  };

  const handleSubmit = (event: FormEvent) => {
    event.preventDefault();
    void sendCurrentMessage();
  };

  const clearChat = () => {
    setMessages([]);
    setError(null);
    setLastRun(null);
  };

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 p-4"
      onClick={onClose}
    >
      <div
        role="dialog"
        aria-modal="true"
        aria-labelledby="dev-llm-chat-title"
        className="flex h-[88vh] w-full max-w-5xl overflow-hidden rounded-lg border border-border bg-surface text-text-primary shadow-2xl"
        onClick={(event) => event.stopPropagation()}
      >
        <aside className="hidden w-72 shrink-0 border-r border-border bg-surface-muted p-4 md:block">
          <div className="mb-5">
            <p className="text-xs font-semibold uppercase tracking-widest text-warning">
              Dev LLM Chat
            </p>
            <h2 id="dev-llm-chat-title" className="mt-1 text-base font-semibold">
              Direct model test
            </h2>
          </div>

          <label
            className="block text-xs font-semibold text-text-secondary"
            htmlFor="dev-system-prompt"
          >
            System prompt
          </label>
          <textarea
            id="dev-system-prompt"
            value={systemPrompt}
            onChange={(event) => setSystemPrompt(event.target.value)}
            className="mt-2 h-36 w-full resize-none rounded border border-border bg-surface px-3 py-2 text-sm text-text-primary focus:outline-none focus:ring-1 focus:ring-primary"
          />

          <label
            className="mt-4 block text-xs font-semibold text-text-secondary"
            htmlFor="dev-model"
          >
            Model override
          </label>
          <input
            id="dev-model"
            value={model}
            onChange={(event) => setModel(event.target.value)}
            placeholder="Use configured default"
            className="mt-2 w-full rounded border border-border bg-surface px-3 py-2 text-sm text-text-primary placeholder-text-muted focus:outline-none focus:ring-1 focus:ring-primary"
          />

          <div className="mt-4 rounded border border-border-muted bg-surface px-3 py-2 text-xs text-text-secondary">
            <p>Provider: {aiProvider === "gemini" ? "Gemini API" : "Local LLM"}</p>
            {lastRun && (
              <p className="mt-1 truncate">Last model: {lastRun.model}</p>
            )}
          </div>

          <button
            type="button"
            onClick={clearChat}
            className="mt-4 w-full rounded border border-border px-3 py-2 text-sm text-text-secondary hover:bg-surface-elevated hover:text-text-primary"
          >
            Clear chat
          </button>
        </aside>

        <section className="flex min-w-0 flex-1 flex-col">
          <header className="flex shrink-0 items-center justify-between border-b border-border px-4 py-3 md:hidden">
            <h2 className="text-base font-semibold">Dev LLM Chat</h2>
            <button
              type="button"
              aria-label="Close dev LLM chat"
              onClick={onClose}
              className="rounded p-1.5 text-text-muted hover:bg-surface-elevated hover:text-text-primary"
            >
              X
            </button>
          </header>

          <header className="hidden shrink-0 items-center justify-between border-b border-border px-5 py-3 md:flex">
            <div className="text-sm text-text-secondary">
              {requestMessages.length} message
              {requestMessages.length === 1 ? "" : "s"} in request
            </div>
            <button
              type="button"
              aria-label="Close dev LLM chat"
              onClick={onClose}
              className="rounded p-1.5 text-text-muted hover:bg-surface-elevated hover:text-text-primary"
            >
              X
            </button>
          </header>

          <div ref={transcriptRef} className="flex-1 overflow-y-auto px-4 py-5">
            {messages.length === 0 ? (
              <div className="flex h-full items-center justify-center text-sm text-text-muted">
                Send a prompt to test the configured LLM.
              </div>
            ) : (
              <div className="mx-auto flex max-w-3xl flex-col gap-3">
                {messages.map((message, index) => (
                  <div
                    key={`${message.role}-${index}`}
                    className={`max-w-[85%] rounded-lg px-3 py-2 text-sm leading-6 ${
                      message.role === "user"
                        ? "ml-auto bg-user-bubble text-user-bubble-text"
                        : "mr-auto border border-border bg-surface"
                    }`}
                  >
                    <p className="mb-1 text-[10px] font-semibold uppercase tracking-widest opacity-70">
                      {message.role}
                    </p>
                    <p className="whitespace-pre-wrap break-words">{message.content}</p>
                  </div>
                ))}
                {isSending && (
                  <div className="mr-auto rounded-lg border border-border bg-surface px-3 py-2 text-sm text-text-secondary">
                    Waiting for model...
                  </div>
                )}
              </div>
            )}
          </div>

          {error && (
            <div className="border-t border-error bg-error-subtle px-4 py-2 text-sm text-error-text">
              {error}
            </div>
          )}

          <form onSubmit={handleSubmit} className="shrink-0 border-t border-border p-4">
            <div className="mx-auto flex max-w-3xl gap-2">
              <textarea
                value={input}
                onChange={(event) => setInput(event.target.value)}
                onKeyDown={(event) => {
                  if (event.key === "Enter" && !event.shiftKey) {
                    event.preventDefault();
                    void sendCurrentMessage();
                  }
                }}
                placeholder="Message the LLM..."
                className="min-h-20 flex-1 resize-none rounded border border-border bg-surface px-3 py-2 text-sm text-text-primary placeholder-text-muted focus:outline-none focus:ring-1 focus:ring-primary"
              />
              <button
                type="submit"
                disabled={!input.trim() || isSending}
                className="h-10 self-end rounded bg-primary-dark px-4 text-sm font-medium text-text-inverse hover:bg-primary-hover disabled:cursor-not-allowed disabled:opacity-50"
              >
                Send
              </button>
            </div>
          </form>
        </section>
      </div>
    </div>
  );
}
