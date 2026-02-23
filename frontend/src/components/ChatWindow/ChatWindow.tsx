import { useState, useRef, useEffect } from "react";

interface Message {
  id: string;
  text: string;
  sender: "user" | "system";
}

interface ChatWindowProps {
  onSendMessage?: (message: string) => void;
  messages?: Message[];
  isConfirming?: boolean;
  onApprove?: () => void;
  onReject?: () => void;
}

/**
 * ChatWindow renders the main conversation area.
 *
 * Layout (top → bottom):
 *   1. Message list  — scrollable area showing user and system bubbles.
 *   2. Input area    — either a text input + Send button (normal mode)
 *                      or Approve / Reject buttons (isConfirming mode).
 *
 * Props:
 *   messages       — ordered array of messages to display.
 *   onSendMessage  — called with the trimmed input string on form submit.
 *   isConfirming   — when true, replaces the input with approval buttons.
 *   onApprove      — called when the user clicks Approve.
 *   onReject       — called when the user clicks Reject.
 */
export default function ChatWindow({
  onSendMessage,
  messages = [],
  isConfirming = false,
  onApprove,
  onReject,
}: ChatWindowProps) {
  const [inputValue, setInputValue] = useState("");
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  // Auto-resize the textarea to fit its content on every keystroke.
  // Step 1: reset to 'auto' so the element can shrink when text is deleted.
  // Step 2: set height to scrollHeight (the true content height).
  // The CSS max-h-64 cap kicks in automatically — once scrollHeight exceeds it,
  // overflow-y-auto takes over and the box scrolls instead of growing further.
  useEffect(() => {
    const el = textareaRef.current;
    if (!el) return;
    el.style.height = "auto";
    el.style.height = `${el.scrollHeight}px`;
  }, [inputValue]);

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

  return (
    <div className="h-full w-full flex flex-col">
      {/* Message list — only rendered (and takes space) when messages exist.
          Outer div handles full-width scrolling.
          Inner div caps content to max-w-3xl (matching the input below) and
          centres it — so the column stays readable even on very wide screens. */}
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
          </div>
        </div>
      )}

      {/* Input zone —
          Empty state:  flex-1 + justify-center → fills the screen and centers content.
          Active state: no flex-1               → sits naturally at the bottom.
          px-6 is on the inner max-w-3xl div (not the parent) so it matches the
          message column above — both content edges land at the same position. */}
      <div
        className={`flex flex-col items-center gap-4 pb-6 ${
          hasMessages ? "pt-2" : "flex-1 justify-center"
        }`}
      >
        {/* Placeholder shown only in empty state */}
        {!hasMessages && (
          <p className="text-2xl font-normal text-gray-500 text-center">
            Ready to start?
          </p>
        )}

        <div className="w-full max-w-3xl px-6">
          {isConfirming ? (
            <div className="flex items-center gap-4 p-4 border-t-2 border-gray-300">
              <button
                onClick={onApprove}
                className="px-4 py-2 bg-green-500 text-white rounded-lg hover:bg-green-600"
              >
                Approve
              </button>
              <button
                onClick={onReject}
                className="px-4 py-2 bg-red-500 text-white rounded-lg hover:bg-red-600"
              >
                Reject
              </button>
            </div>
          ) : (
            /* relative on the form lets the button be absolute-positioned.
               pb-12 on the form reserves space at the bottom so the textarea
               text never slides under the button. */
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
                  if (e.key === "Enter" && !e.shiftKey) {
                    e.preventDefault();
                    submitMessage();
                  }
                }}
                className="w-full pl-1 pr-2 py-1 outline-none bg-transparent text-gray-700 resize-none overflow-y-auto max-h-64"
              />
              {/* Absolutely positioned so it sits in the bottom-right corner of
                  the form box — the scrollbar is now flush at the textarea's
                  right edge (= the form border), unobstructed by the button. */}
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
