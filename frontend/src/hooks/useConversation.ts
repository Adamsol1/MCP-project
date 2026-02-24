import { useContext } from "react";
import { ConversationContext } from "../contexts/ConversationContext";

/**
 * Convenience hook for reading from and writing to ConversationContext.
 *
 * Reads from ConversationContext, which is populated by ConversationProvider
 * in main.tsx. Throws a descriptive error if called outside of a
 * ConversationProvider, preventing silent failures from a missing provider.
 *
 * @returns The full ConversationContextValue — the conversation list,
 *          the active conversation, and all mutation callbacks
 *          (createNewConversation, switchConversation, addMessage, etc.).
 */
export function useConversation() {
  const context = useContext(ConversationContext);
  if (!context) {
    throw new Error(
      "useConversation must be used within a ConversationProvider"
    );
  }
  return context;
}
