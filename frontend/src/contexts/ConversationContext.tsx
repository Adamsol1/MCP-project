import {
  createContext,
  useReducer,
  useCallback,
  useEffect,
  type ReactNode,
} from "react";
import type {
  Conversation,
  Message,
  ConversationStore,
} from "../types/conversation";
import {
  loadConversationStore,
  saveConversationStore,
  createConversation,
} from "../services/conversationStorage";

export interface ConversationContextValue {
  conversations: Conversation[];
  activeConversation: Conversation | null;
  createNewConversation: () => void;
  switchConversation: (id: string) => void;
  deleteConversation: (id: string) => void;
  addMessage: (message: Message) => void;
  setIsConfirming: (value: boolean) => void;
  updatePerspectives: (perspectives: string[]) => void;
}

type Action =
  | { type: "CREATE_CONVERSATION" }
  | { type: "SWITCH_CONVERSATION"; payload: string }
  | { type: "DELETE_CONVERSATION"; payload: string }
  | {
      type: "ADD_MESSAGE";
      payload: { conversationId: string; message: Message };
    }
  | { type: "SET_IS_CONFIRMING"; payload: boolean }
  | { type: "UPDATE_PERSPECTIVES"; payload: string[] };

export const ConversationContext =
  createContext<ConversationContextValue | null>(null);

function conversationReducer(
  state: ConversationStore,
  action: Action,
): ConversationStore {
  switch (action.type) {
    case "CREATE_CONVERSATION": {
      const newConversation = createConversation();
      return {
        ...state,
        conversations: [...state.conversations, newConversation],
        activeConversationId: newConversation.id,
      };
    }
    case "SWITCH_CONVERSATION":
      return { ...state, activeConversationId: action.payload };
    case "DELETE_CONVERSATION": {
      const filteredConversations = state.conversations.filter(
        (conv) => conv.id !== action.payload,
      );
      const newActiveId =
        state.activeConversationId === action.payload
          ? filteredConversations.length > 0
            ? filteredConversations[0].id
            : null
          : state.activeConversationId;
      return {
        ...state,
        conversations: filteredConversations,
        activeConversationId: newActiveId,
      };
    }
    case "ADD_MESSAGE": {
      const { conversationId, message } = action.payload;
      return {
        ...state,
        conversations: state.conversations.map((conv) => {
          if (conv.id !== conversationId) return conv;

          // Title: set from first user message, truncated to 50 chars
          let newTitle = conv.title;
          if (message.sender === "user" && conv.title === "New conversation") {
            newTitle =
              message.text.length > 50
                ? message.text.slice(0, 50) + "..."
                : message.text;
          }

          return {
            ...conv,
            messages: [...conv.messages, message],
            title: newTitle,
            updatedAt: Date.now(),
          };
        }),
      };
    }

    case "SET_IS_CONFIRMING": {
      return {
        ...state,
        conversations: state.conversations.map((conv) =>
          conv.id === state.activeConversationId
            ? { ...conv, isConfirming: action.payload }
            : conv,
        ),
      };
    }
    case "UPDATE_PERSPECTIVES":
      return {
        ...state,
        conversations: state.conversations.map((conv) =>
          conv.id === state.activeConversationId
            ? { ...conv, perspectives: action.payload }
            : conv,
        ),
      };
    default:
      return state;
  }
}

export function ConversationProvider({ children }: { children: ReactNode }) {
  const [state, dispatch] = useReducer(
    conversationReducer,
    undefined,
    loadConversationStore,
  );

  useEffect(() => {
    saveConversationStore(state);
  }, [state]);

  const activeConversation =
    state.conversations.find((c) => c.id === state.activeConversationId) ??
    null;

  const createNewConversation = useCallback(() => {
    dispatch({ type: "CREATE_CONVERSATION" });
  }, []);

  const switchConversation = useCallback((id: string) => {
    dispatch({ type: "SWITCH_CONVERSATION", payload: id });
  }, []);

  const deleteConversation = useCallback((id: string) => {
    dispatch({ type: "DELETE_CONVERSATION", payload: id });
  }, []);

  const addMessage = useCallback(
    (message: Message) => {
      if (!activeConversation) return;
      dispatch({
        type: "ADD_MESSAGE",
        payload: { conversationId: activeConversation.id, message },
      });
    },
    [activeConversation],
  );

  const setIsConfirming = useCallback((value: boolean) => {
    dispatch({ type: "SET_IS_CONFIRMING", payload: value });
  }, []);

  const updatePerspectives = useCallback((perspectives: string[]) => {
    dispatch({ type: "UPDATE_PERSPECTIVES", payload: perspectives });
  }, []);

  const value: ConversationContextValue = {
    conversations: state.conversations,
    activeConversation,
    createNewConversation,
    switchConversation,
    deleteConversation,
    addMessage,
    setIsConfirming,
    updatePerspectives,
  };

  return (
    <ConversationContext.Provider value={value}>
      {children}
    </ConversationContext.Provider>
  );
}
