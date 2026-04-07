import type { Conversation } from "../types/conversation";

export function canReuseConversationForAnalysisDemo(
  conversation: Conversation | null | undefined,
) {
  if (!conversation) {
    return false;
  }

  return (
    conversation.title === "New conversation" &&
    conversation.messages.length === 0 &&
    conversation.stage === "initial" &&
    conversation.subState === null
  );
}
