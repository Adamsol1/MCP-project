export interface Message {
  id: string;
  text: string;
  sender: "user" | "system";
}

export interface Conversation {
  id: string;
  title: string;
  messages: Message[];
  perspectives: string[];
  sessionId: string;
  isConfirming: boolean;
  createdAt: number;
  updatedAt: number;
}

export interface ConversationStore {
  conversations: Conversation[];
  activeConversationId: string | null;
}
