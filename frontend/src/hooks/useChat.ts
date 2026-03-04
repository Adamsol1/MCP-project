import { useState } from "react";
import {
  getDevDialogueState,
  resetDevDialogueState,
  sendMessage,
  setDevDialogueState,
  type DialogueApiResponse,
} from "../services/dialogue";
import type { DialogueStage, DialogueSubState } from "../types/dialogue";
import { useConversation } from "./useConversation";
import { useToast } from "./useToast";

function inferStageFromResponse(
  response: DialogueApiResponse,
): { stage: DialogueStage; subState: DialogueSubState } {
  if (response.stage) {
    const subState =
      response.sub_state ??
      (response.stage === "summary_confirming" ||
      response.stage === "pir_confirming"
        ? "awaiting_decision"
        : null);
    return { stage: response.stage, subState };
  }

  if (response.type === "summary") {
    return { stage: "summary_confirming", subState: "awaiting_decision" };
  }
  if (response.type === "pir") {
    return { stage: "pir_confirming", subState: "awaiting_decision" };
  }
  if (response.type === "complete") {
    return { stage: "complete", subState: null };
  }
  if (response.is_final) {
    return { stage: "summary_confirming", subState: "awaiting_decision" };
  }
  return { stage: "gathering", subState: null };
}

export function useChat() {
  const { activeConversation, addMessage, setIsConfirming, setStage } =
    useConversation();
  const { success, info, error } = useToast();
  const [isLoading, setIsLoading] = useState(false);
  const [devPrefill, setDevPrefill] = useState<string | null>(null);

  const messages = activeConversation?.messages ?? [];
  const stage = activeConversation?.stage ?? "initial";
  const subState = activeConversation?.subState ?? null;
  const isConfirming =
    (stage === "summary_confirming" || stage === "pir_confirming") &&
    subState !== "awaiting_modifications";

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
      const next = inferStageFromResponse(response);
      setStage(next.stage, next.subState);
    } finally {
      setIsLoading(false);
    }
  };

  const approve = async () => {
    if (!activeConversation) return;
    setIsLoading(true);
    try {
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
      const next = inferStageFromResponse(response);
      setStage(next.stage, next.subState);
      success("Request approved");
    } finally {
      setIsLoading(false);
    }
  };

  const triggerDevMessage = (text: string) => {
    setDevPrefill(text);
  };

  const clearDevPrefill = () => {
    setDevPrefill(null);
  };

  const debugConfirm = () => {
    addMessage({
      id: crypto.randomUUID(),
      text: "Summary: Investigate APT29 activity targeting EU infrastructure over the last 6 months. Do you approve?",
      sender: "system",
    });
    setStage("summary_confirming", "awaiting_decision");
  };

  const reject = () => {
    addMessage({
      id: crypto.randomUUID(),
      text: "What would you like to change?",
      sender: "system",
    });
    if (stage === "summary_confirming" || stage === "pir_confirming") {
      setStage(stage, "awaiting_modifications");
    } else {
      setIsConfirming(false);
    }
    info("Request rejected - what would you like to change?");
  };

  const jumpToDevStage = async (
    nextStage: DialogueStage,
    nextSubState: DialogueSubState = "awaiting_decision",
  ) => {
    if (!activeConversation) return;
    try {
      const response = await setDevDialogueState(
        activeConversation.sessionId,
        nextStage,
        nextSubState,
      );
      setStage(response.stage, response.sub_state);
      info(`Moved to stage: ${response.stage}`);
    } catch {
      error("Failed to set dev stage");
    }
  };

  const syncDevStage = async () => {
    if (!activeConversation) return;
    try {
      const response = await getDevDialogueState(activeConversation.sessionId);
      setStage(response.stage, response.sub_state);
      info(`Synced stage: ${response.stage}`);
    } catch {
      error("Failed to sync dev stage");
    }
  };

  const resetDevStage = async () => {
    if (!activeConversation) return;
    try {
      const response = await resetDevDialogueState(activeConversation.sessionId);
      setStage(response.stage, response.sub_state);
      info("Reset stage to initial");
    } catch {
      error("Failed to reset dev stage");
    }
  };

  return {
    messages,
    sendMessage: handleSendMessage,
    isConfirming,
    stage,
    subState,
    isLoading,
    approve,
    reject,
    debugConfirm,
    jumpToDevStage,
    syncDevStage,
    resetDevStage,
    devPrefill,
    triggerDevMessage,
    clearDevPrefill,
  };
}
