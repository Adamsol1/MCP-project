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

/**
 * The value exposed by ConversationContext to any consuming component.
 *
 * Gives any component in the tree read access to the full conversation list
 * and the currently active conversation, plus stable callbacks to mutate state.
 * All callbacks are memoised with useCallback so their references are stable
 * across re-renders.
 */
export interface ConversationContextValue {
  /** All conversations in insertion order. */
  conversations: Conversation[];
  /** The currently selected conversation, or null when none exist. */
  activeConversation: Conversation | null;
  /** Create a brand-new conversation and make it the active one. */
  createNewConversation: () => void;
  /** Switch the active conversation to the one with the given id. */
  switchConversation: (id: string) => void;
  /** Permanently delete the conversation with the given id. */
  deleteConversation: (id: string) => void;
  /** DEV: Permanently delete all conversations. */
  deleteAllConversations: () => void;
  /** Rename the conversation with the given id to newTitle. */
  renameConversation: (id: string, newTitle: string) => void;
  /** Append a message to the active conversation's message list. */
  addMessage: (message: Message) => void;
  /** Set whether the active conversation is awaiting user approval. */
  setIsConfirming: (value: boolean) => void;
  /** Replace the geopolitical perspectives of the active conversation. */
  updatePerspectives: (perspectives: string[]) => void;
}

/**
 * Union of all actions that can be dispatched to conversationReducer.
 * Each variant maps to one public mutation in ConversationContextValue.
 */
type Action =
  | { type: "CREATE_CONVERSATION" }
  | { type: "SWITCH_CONVERSATION"; payload: string }
  | { type: "DELETE_CONVERSATION"; payload: string }
  | { type: "DELETE_ALL_CONVERSATIONS" }
  | { type: "RENAME_CONVERSATION"; payload: { id: string; newTitle: string } }
  | {
      type: "ADD_MESSAGE";
      payload: { conversationId: string; message: Message };
    }
  | { type: "SET_IS_CONFIRMING"; payload: boolean }
  | { type: "UPDATE_PERSPECTIVES"; payload: string[] };

/**
 * The React context object for conversations.
 * Initialised with null — a null value at runtime means the consuming component
 * is not wrapped in a ConversationProvider (caught by the useConversation guard).
 */
// eslint-disable-next-line react-refresh/only-export-components
export const ConversationContext =
  createContext<ConversationContextValue | null>(null);

/**
 * Pure reducer that computes the next ConversationStore from the current state
 * and an incoming action. Each case returns a new state object — the original
 * is never mutated directly.
 *
 * Notable behaviours:
 *  - DELETE_CONVERSATION falls back to the first remaining conversation (or null)
 *    as the new active item when the deleted one was currently active.
 *  - ADD_MESSAGE automatically sets the conversation title from the first user
 *    message (truncated to 50 characters), replacing the "New conversation" default.
 */
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
      // If the deleted conversation was active, fall back to the first remaining one.
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
    case "DELETE_ALL_CONVERSATIONS":
      return { ...state, conversations: [], activeConversationId: null };
    case "RENAME_CONVERSATION": {
      const { id, newTitle } = action.payload;
      return {
        ...state,
        conversations: state.conversations.map((conv) =>
          conv.id === id
            ? { ...conv, title: newTitle, updatedAt: Date.now() }
            : conv,
        ),
      };
    }
    case "ADD_MESSAGE": {
      const { conversationId, message } = action.payload;
      return {
        ...state,
        conversations: state.conversations.map((conv) => {
          if (conv.id !== conversationId) return conv;

          // Auto-set the title from the first user message (max 50 chars).
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

/**
 * Provides conversation state and mutation callbacks to the entire component tree.
 *
 * State is managed with useReducer and initialised by reading from localStorage
 * (via the loadConversationStore initialiser function), so conversations survive
 * page reloads. A useEffect persists every state change back to localStorage
 * immediately after each render to prevent data loss on tab close.
 *
 * All callback functions are wrapped in useCallback so their references stay
 * stable across re-renders — safe to pass as props to child components.
 */
export function ConversationProvider({ children }: { children: ReactNode }) {
  const [state, dispatch] = useReducer(
    conversationReducer,
    undefined,
    loadConversationStore,
  );

  // Persist the full store to localStorage after every state change.
  useEffect(() => {
    saveConversationStore(state);
  }, [state]);

  // Derive the active conversation object from the stored active id.
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

  const deleteAllConversations = useCallback(() => {
    dispatch({ type: "DELETE_ALL_CONVERSATIONS" });
  }, []);

  const renameConversation = useCallback((id: string, newTitle: string) => {
    dispatch({ type: "RENAME_CONVERSATION", payload: { id, newTitle } });
  }, []);

  /**
   * Appends a message to the active conversation.
   * Does nothing if there is no active conversation.
   * activeConversation is listed as a dependency so the closure always
   * captures the latest active conversation id.
   */
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
    deleteAllConversations,
    renameConversation,
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
