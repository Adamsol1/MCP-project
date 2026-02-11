import { useState } from "react";
import { sendMessage } from "../services/dialogue";

interface Message {
  id: string;
  text: string;
  sender: "user" | "system";
}

export function useChat(perspectives: string[] = ["NEUTRAL"]) {
  const [messages, setMessages] = useState<Message[]>([]);
  const [sessionId] = useState(() => crypto.randomUUID());
  const [isConfirming, setIsConfirming] = useState(false);

  const handleSendMessage = async (text: string, approved?: boolean) => {
    // 1. Create user message and add to state
    const userMessage: Message = {
      id: crypto.randomUUID(),
      text: text,
      sender: "user",
    };
    setMessages((prev) => [...prev, userMessage]);

    // 2. Call the backend service with current perspectives and add system response
    const response = await sendMessage(text, sessionId, perspectives, approved);
    const systemMessage: Message = {
      id: crypto.randomUUID(),
      text: response.question,
      sender: "system",
    };
    setMessages((prev) => [...prev, systemMessage]);

    setIsConfirming(response.is_final);
  };
  const approve = async () => {
    await handleSendMessage("approve", true);
  };

  const reject = async () => {
    const feedbackMessage: Message = {
      id: crypto.randomUUID(),
      text: "What would you like to change?",
      sender: "system",
    };
    setMessages((prev) => [...prev, feedbackMessage]);
    setIsConfirming(false);
  };

  return {
    messages,
    sendMessage: handleSendMessage,
    isConfirming,
    approve,
    reject,
  };
}
