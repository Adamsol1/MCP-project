import { sendMessage } from "../services/dialogue";
import type { Message } from "../types/conversation";
import { useConversation } from "./useConversation";

export function useChat() {
  const { activeConversation, addMessage, setIsConfirming } = useConversation();

  const messages = activeConversation?.messages ?? [];
  const isConfirming = activeConversation?.isConfirming ?? false;

  const handleSendMessage = async (text: string, approved?: boolean) => {
    if (!activeConversation) return;
    addMessage({
      id: crypto.randomUUID(),
      text,
      sender: "user",
    });

    // 2. Call the backend service with current perspectives and add system response
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
  };
  const approve = async () => {
    if (!activeConversation) return;
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
