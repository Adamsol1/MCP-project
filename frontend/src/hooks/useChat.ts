import { useState } from "react";
import { sendMessage } from "../services/dialogue";

interface Message {
  id: string;
  text: string;
  sender: "user" | "system";
}

export function useChat() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [sessionId] = useState(() => crypto.randomUUID());

  const handleSendMessage = async (text: string) => {
    // 1. Create user message and add to state
    const userMessage: Message = {
      id: crypto.randomUUID(),
      text: text,
      sender: "user",
    };
    setMessages((prev) => [...prev, userMessage]);

    // 2. Call the backend service and add system response
    const response = await sendMessage(text, sessionId);
    const systemMessage: Message = {
      id: crypto.randomUUID(),
      text: response.question,
      sender: "system",
    };
    setMessages((prev) => [...prev, systemMessage]);
  };
  return { messages, sendMessage: handleSendMessage };
}
