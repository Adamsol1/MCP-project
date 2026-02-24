import { useState, useRef, useEffect } from "react";
import { ToastContainer } from "../Toast";

/** Shape of a single message displayed in the chat. */
interface Message {
  id: string;
  text: string;
  sender: "user" | "system";
}

/** Props for the ChatWindow component. */
interface ChatWindowProps {
  /** Called with the trimmed input string when the user submits a message. */
  onSendMessage?: (message: string) => void;
  /** Ordered array of messages to render. Defaults to an empty array. */
  messages?: Message[];
  /**
   * When true, replaces the text input with Approve / Reject buttons.
   * Set by the backend returning is_final: true.
   */
  isConfirming?: boolean;
  /** When true, disables Approve / Reject and shows the loading throbber. */
  isLoading?: boolean;
  /** Called when the user clicks Approve in confirmation mode. */
  onApprove?: () => void;
  /** Called when the user clicks Reject in confirmation mode. */
  onReject?: () => void;
  /** DEV: When set, pre-fills the textarea with this text and auto-sends it. */
  devPrefill?: string | null;
  /** DEV: Called once the prefill value has been consumed so parent can clear it. */
  onDevPrefillConsumed?: () => void;
}

/**
 * Main conversation area — renders the message history and the input zone.
 *
 * Layout (top → bottom):
 *   1. Message list  — scrollable column of user (right, blue) and system
 *                      (left, grey) bubbles. Only present when messages exist.
 *   2. Input zone    — either a growing textarea + send button (normal mode)
 *                      or Approve / Reject buttons (isConfirming mode).
 *
 * Empty state: the input zone expands to fill the full height and centres its
 * content, giving a clean "Ready to start?" landing view. Once messages exist,
 * the zone collapses to the bottom of the screen.
 *
 * The ToastContainer is rendered here (above the input) so notifications pop up
 * adjacent to the input field rather than in a distant screen corner.
 */
export default function ChatWindow({
  onSendMessage,
  messages = [],
  isConfirming = false,
  isLoading = false,
  onApprove,
  onReject,
  devPrefill,
  onDevPrefillConsumed,
}: ChatWindowProps) {
  const [inputValue, setInputValue] = useState("");

  // Ref to the textarea DOM node — used for programmatic height adjustment.
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  // Ref to an invisible div at the bottom of the message list — scrolled into
  // view whenever new messages arrive.
  const messagesEndRef = useRef<HTMLDivElement>(null);

  /**
   * Auto-resizes the textarea to fit its content on every keystroke.
   *
   * Step 1: reset height to 'auto' so the element can shrink when text is deleted.
   * Step 2: set height to scrollHeight (the true content height).
   * The CSS max-h-64 cap kicks in automatically — once scrollHeight exceeds it,
   * overflow-y-auto takes over and the box scrolls instead of growing further.
   */
  useEffect(() => {
    const el = textareaRef.current;
    if (!el) return;
    el.style.height = "auto";
    el.style.height = `${el.scrollHeight}px`;
  }, [inputValue]);

  /**
   * Scrolls the message list to the bottom whenever new messages arrive or the
   * loading throbber appears. Uses smooth scrolling for a polished feel.
   */
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, isLoading]);

  /**
   * DEV ONLY: When devPrefill is set, fills the textarea with the predefined
   * text and auto-sends it after a short delay so the text is briefly visible.
   */
  useEffect(() => {
    if (!devPrefill) return;
    setInputValue(devPrefill);
    onDevPrefillConsumed?.();
    const id = setTimeout(() => {
      onSendMessage?.(devPrefill);
      setInputValue("");
    }, 80);
    return () => clearTimeout(id);
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [devPrefill]);

  /** Submits the current input value if it is non-empty, then clears the field. */
  const submitMessage = () => {
    if (inputValue.trim() === "") return;
    onSendMessage?.(inputValue);
    setInputValue("");
  };

  /** Prevents the form's default page-reload behaviour and delegates to submitMessage. */
  const handleSubmit = (event: React.SyntheticEvent) => {
    event.preventDefault();
    submitMessage();
  };

  const hasMessages = messages.length > 0;

  return (
    <div className="h-full w-full flex flex-col">
      {/*
        Message list — only rendered (and takes up space) when messages exist.
        The outer div handles scrolling across the full width.
        The inner div caps content to max-w-3xl and centres it so the column
        stays readable on very wide screens, matching the input zone below.
      */}
      {hasMessages && (
        <div className="flex-1 min-h-0 overflow-y-auto py-4">
          <div className="w-full max-w-3xl mx-auto px-6 flex flex-col">
            {messages.map((message) => (
              <div
                key={message.id}
                data-sender={message.sender}
                className={`max-w-[75%] p-3 rounded-lg mb-2 ${
                  message.sender === "user"
                    ? "self-end bg-blue-500 text-white"
                    : "self-start bg-gray-50 text-gray-700"
                }`}
              >
                <p>{message.text}</p>
              </div>
            ))}
            {/* Animated three-dot throbber shown while a backend response is in flight. */}
            {isLoading && (
              <div className="self-start bg-gray-50 rounded-lg p-3 mb-2">
                <div className="flex items-center gap-1">
                  <span className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" />
                  <span className="w-2 h-2 bg-gray-400 rounded-full animate-bounce [animation-delay:150ms]" />
                  <span className="w-2 h-2 bg-gray-400 rounded-full animate-bounce [animation-delay:300ms]" />
                </div>
              </div>
            )}
            {/* Invisible sentinel — scrolled into view to keep the list pinned to the bottom. */}
            <div ref={messagesEndRef} />
          </div>
        </div>
      )}

      {/*
        Input zone:
          Empty state  → flex-1 + justify-center fills the screen and centres content.
          Active state → no flex-1, sits naturally at the bottom.
        px-6 lives on the inner max-w-3xl div (not the outer wrapper) so the
        content edges align with the message column above.
      */}
      <div
        className={`flex flex-col items-center gap-4 pb-6 ${
          hasMessages ? "pt-2" : "flex-1 justify-center"
        }`}
      >
        {/* "Ready to start?" placeholder — only shown in the empty state. */}
        {!hasMessages && (
          <p className="text-2xl font-normal text-gray-500 text-center">
            Ready to start?
          </p>
        )}

        {/* Toast notifications float above the input (fixed, bottom-32, centred). */}
        <ToastContainer position="above-input" />

        <div className="w-full max-w-3xl px-6">
          {isConfirming ? (
            /* Confirmation mode: Approve / Reject replace the text input. */
            <div className="flex items-center gap-4 p-4 border-t-2 border-gray-300">
              <button
                onClick={onApprove}
                disabled={isLoading}
                className="px-4 py-2 bg-green-500 text-white rounded-lg hover:bg-green-600 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                Approve
              </button>
              <button
                onClick={onReject}
                disabled={isLoading}
                className="px-4 py-2 bg-red-500 text-white rounded-lg hover:bg-red-600 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                Reject
              </button>
            </div>
          ) : (
            /*
             * Normal mode: growing textarea inside a relative-positioned form.
             * relative on the form lets the send button be absolute-positioned
             * in the bottom-right corner.
             * pb-12 reserves space so textarea text never slides under the button.
             */
            <form
              onSubmit={handleSubmit}
              className="relative border-2 border-gray-300 rounded-xl p-3 pb-12"
            >
              <textarea
                ref={textareaRef}
                rows={1}
                placeholder="Ask anything..."
                value={inputValue}
                onChange={(event) => setInputValue(event.target.value)}
                onKeyDown={(e) => {
                  // Enter alone submits; Shift+Enter inserts a newline.
                  if (e.key === "Enter" && !e.shiftKey) {
                    e.preventDefault();
                    submitMessage();
                  }
                }}
                className="w-full pl-1 pr-2 py-1 outline-none bg-transparent text-gray-700 resize-none overflow-y-auto max-h-64"
              />
              {/* Send button — absolutely positioned in the bottom-right corner
                  of the form so the textarea scrollbar is unobstructed. */}
              <button
                type="submit"
                disabled={inputValue.trim() === ""}
                aria-label="Send message"
                className={`absolute bottom-2 right-2 p-2 rounded-full transition-colors ${
                  inputValue.trim() === ""
                    ? "bg-gray-200 text-gray-400 cursor-not-allowed"
                    : "bg-blue-500 text-white hover:bg-blue-600"
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
  );
}
