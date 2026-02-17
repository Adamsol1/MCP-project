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
    // Send approval silently to backend — no visible "approve" message in chat
    const response = await sendMessage("approve", sessionId, perspectives, true);
    const systemMessage: Message = {
      id: crypto.randomUUID(),
      text: response.question,
      sender: "system",
    };
    setMessages((prev) => [...prev, systemMessage]);
    setIsConfirming(response.is_final);
  };

  // DEBUG: Simulate backend returning is_final: true — remove before production
  const debugConfirm = () => {
    const summary: Message = {
      id: crypto.randomUUID(),
      text: "Summary: Investigate APT29 activity targeting EU infrastructure over the last 6 months. Do you approve?",
      sender: "system",
    };
    setMessages((prev) => [...prev, summary]);
    setIsConfirming(true);
  };

  const reject = () => {
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
    debugConfirm,
  };
}
