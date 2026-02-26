import { useState } from "react";
import { sendMessage } from "../services/dialogue";
import { useSettings } from "../contexts/SettingsContext";
import { useConversation } from "./useConversation";
import { useToast } from "./useToast";
import type { Message, PirData, SummaryData } from "../types/conversation";

/**
 * Orchestrates all chat interactions for the active conversation.
 *
 * Combines read access to the active conversation's messages and isConfirming
 * flag (from ConversationContext) with local loading state, and connects user
 * actions to the backend dialogue service.
 *
 * Returned values:
 *   messages      — ordered message history for the active conversation.
 *   sendMessage   — adds the user message to chat, calls the backend, then adds
 *                   the system reply. Sets isLoading while in flight.
 *   isConfirming  — true when the backend has returned is_final: true, meaning
 *                   the chat is waiting for the user to approve a summary.
 *   isLoading     — true while any backend request is in flight.
 *   approve       — silently sends approval to the backend; displays the response.
 *   reject        — cancels the pending summary and prompts the user to refine.
 *   debugConfirm  — DEV ONLY: injects a fake summary to test the approval UI.
 */
export function useChat() {
  const { activeConversation, addMessage, setIsConfirming, createNewConversation } = useConversation();
  const { success, info } = useToast();
  const { settings } = useSettings();
  const [isLoading, setIsLoading] = useState(false);
  const [devPrefill, setDevPrefill] = useState<string | null>(null);

  // Read message history and confirmation state from the active conversation.
  // Fall back to empty / false when no conversation is selected.
  const messages = activeConversation?.messages ?? [];
  const isConfirming = activeConversation?.isConfirming ?? false;
  const buildSystemMessage = (response: {
    question: string;
    type: string;
    is_final: boolean;
  }): Message => {
    if (response.type === "summary" || response.type === "pir") {
      let data: SummaryData | PirData | undefined;
      try {
        data = JSON.parse(response.question);
      } catch {
        /* empty */
      }
      return {
        id: crypto.randomUUID(),
        text: response.question,
        sender: "system",
        type: response.type as Message["type"],
        data,
      };
    }
    // fallback for "question", "complete", etc.
    return {
      id: crypto.randomUUID(),
      text: response.question,
      sender: "system",
      type: response.type as Message["type"],
    };
  };

  /**
   * Sends a user message to the backend and appends both the user message and
   * the system reply to the active conversation.
   *
   * @param text     - The user's input text.
   * @param approved - Optional flag forwarded to the backend (used internally by approve()).
   */
  const handleSendMessage = async (text: string, approved?: boolean) => {
    // Auto-create a conversation when none is active (first visit, or after
    // deleting all conversations). createNewConversation() dispatches to the
    // reducer and returns the new Conversation synchronously so we have its
    // sessionId and perspectives before any async work begins.
    const conversation = activeConversation ?? createNewConversation();

    // Pass conversation.id explicitly for both addMessage calls.
    // After the awaited backend call React will have re-rendered, making the
    // addMessage closure stale — an explicit ID avoids relying on it.
    addMessage(
      { id: crypto.randomUUID(), text, sender: "user" },
      conversation.id,
    );

    setIsLoading(true);
    try {
      const response = await sendMessage(
        text,
        conversation.sessionId,
        conversation.perspectives,
        approved,
        settings.language,
        settings.inputParameters.timeframe,
      );
      addMessage(buildSystemMessage(response), conversation.id);
      setIsConfirming(response.is_final);
    } finally {
      setIsLoading(false);
    }
  };

  /**
   * Approves the pending summary.
   *
   * Sends the approval signal to the backend silently (no "approve" bubble added
   * to the chat), then appends the backend's follow-up response.
   */
  const approve = async () => {
    if (!activeConversation) return;
    setIsLoading(true);
    try {
      const response = await sendMessage(
        "approve",
        activeConversation.sessionId,
        activeConversation.perspectives,
        true,
        settings.language,
        settings.inputParameters.timeframe,
      );

      addMessage(buildSystemMessage(response));

      setIsConfirming(response.is_final);
      success("Request approved");
    } finally {
      setIsLoading(false);
    }
  };

  /**
   * DEV ONLY: Pre-fills the chat input with the given text and auto-sends it.
   * Triggers the ChatWindow to show the message in the textarea before submitting.
   */
  const triggerDevMessage = (text: string) => {
    setDevPrefill(text);
  };

  /** Clears the dev prefill — called by ChatWindow after it has consumed the value. */
  const clearDevPrefill = () => {
    setDevPrefill(null);
  };

  /**
   * DEV ONLY: Simulates the backend returning is_final: true so the approval UI
   * can be tested without a live backend. Remove before production.
   */
  const debugConfirm = () => {
    addMessage({
      id: crypto.randomUUID(),
      text: "Summary: Investigate APT29 activity targeting EU infrastructure over the last 6 months. Do you approve?",
      sender: "system",
    });
    setIsConfirming(true);
  };

  /**
   * Rejects the pending summary.
   *
   * Adds a prompt asking the user what they'd like to change, clears the
   * confirmation state, and shows an info toast.
   */
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
    devPrefill,
    triggerDevMessage,
    clearDevPrefill,
  };
}
