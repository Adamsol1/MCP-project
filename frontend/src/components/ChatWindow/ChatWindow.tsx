import { useState } from "react";

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

  const handleSubmit = (event: React.SubmitEvent) => {
    event.preventDefault();
    if (inputValue.trim() === "") return;
    onSendMessage?.(inputValue);
    setInputValue("");
  };

  return (
    <div className="w-full flex flex-col">
      {/* Message area — px-8 keeps bubbles away from the left/right edges */}
      <div className="flex-1 min-h-64 flex flex-col justify-center px-8 py-4">
        {messages.length === 0 && (
          <p className="text-2xl font-normal text-gray-500 text-center">
            Ready to start?
          </p>
        )}

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

      {/* Input area — mx-8 mb-6 gives the same horizontal breathing room as
          the message area above, and lifts it slightly off the bottom edge */}
      {isConfirming ? (
        <div className="flex items-center gap-4 p-4 mx-8 mb-6 border-t-2 border-gray-300">
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
        <form
          onSubmit={handleSubmit}
          className="flex items-center gap-2 border-2 border-gray-300 rounded-lg p-2 mx-8 mb-6"
        >
          <input
            type="text"
            placeholder="Ask anything..."
            value={inputValue}
            onChange={(event) => setInputValue(event.target.value)}
            className="flex-1 px-3 py-2 outline-none bg-transparent text-gray-700"
          />
          {/* Disable send button when input is empty */}
          <button
            disabled={inputValue.trim() === ""}
            className={`px-4 py-2 rounded-lg font-medium ${
              inputValue.trim() === ""
                ? "bg-gray-300 text-gray-500 cursor-not-allowed"
                : "bg-blue-500 text-white hover:bg-blue-600"
            }`}
          >
            Send
          </button>
        </form>
      )}
    </div>
  );
}
