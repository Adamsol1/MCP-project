import { useContext } from "react";
import { ConversationContext } from "../contexts/ConversationContext";

// Thin wrapper around ConversationContext, following the same pattern as useToast.
// Throws an error if used outside of a ConversationProvider.
export function useConversation() {
  const context = useContext(ConversationContext);
  if (!context) {
    throw new Error(
      "useConversation must be used within a ConversationProvider"
    );
  }
  return context;
}
