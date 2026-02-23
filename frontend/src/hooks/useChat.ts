import { useState } from "react";
import { sendMessage } from "../services/dialogue";
import type { Message } from "../types/conversation";
import { useConversation } from "./useConversation";
import { useToast } from "./useToast";

export function useChat() {
  const { activeConversation, addMessage, setIsConfirming } = useConversation();
  const { success, info } = useToast();
  const [isLoading, setIsLoading] = useState(false);

  const messages = activeConversation?.messages ?? [];
  const isConfirming = activeConversation?.isConfirming ?? false;

  const handleSendMessage = async (text: string, approved?: boolean) => {
    if (!activeConversation) return;
    addMessage({
      id: crypto.randomUUID(),
      text,
      sender: "user",
    });

    setIsLoading(true);
    try {
      const response = await sendMessage(
        text,
        activeConversation.sessionId,
        activeConversation.perspectives,
        approved,
      );
      addMessage({
        id: crypto.randomUUID(),
        text: response.question,
        sender: "system",
      });
      setIsConfirming(response.is_final);
    } finally {
      setIsLoading(false);
    }
  };

  const approve = async () => {
    if (!activeConversation) return;
    setIsLoading(true);
    try {
      // Send approval silently to backend — no visible "approve" message in chat
      const response = await sendMessage(
        "approve",
        activeConversation.sessionId,
        activeConversation.perspectives,
        true,
      );
      addMessage({
        id: crypto.randomUUID(),
        text: response.question,
        sender: "system",
      });
      setIsConfirming(response.is_final);
      success("Request approved");
    } finally {
      setIsLoading(false);
    }
  };

  // DEBUG: Simulate backend returning is_final: true — remove before production
  const debugConfirm = () => {
    addMessage({
      id: crypto.randomUUID(),
      text: "Summary: Investigate APT29 activity targeting EU infrastructure over the last 6 months. Do you approve?",
      sender: "system",
    });
    setIsConfirming(true);
  };

  const reject = () => {
    addMessage({
      id: crypto.randomUUID(),
      text: "What would you like to change?",
      sender: "system",
    });
    setIsConfirming(false);
    info("Request rejected — what would you like to change?");
  };

  return {
    messages,
    sendMessage: handleSendMessage,
    isConfirming,
    isLoading,
    approve,
    reject,
    debugConfirm,
  };
}
