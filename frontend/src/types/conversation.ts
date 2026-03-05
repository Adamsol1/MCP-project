import type { DialogueStage, DialogueSubState } from "./dialogue";

/** A single chat message exchanged between the user and the system. */
export interface Message {
  /** Unique identifier (UUID) for this message. */
  id: string;
  /** The text content of the message. */
  text: string;
  /** Who sent the message — the human user or the AI system. */
  sender: "user" | "system";
  type?: "question" | "summary" | "pir" | "complete"; // The type of message, which can be "text", "summary", or "error".
  data?: SummaryData | PirData; // JSON obj
}

/**
 * A conversation session between the user and the backend.
 *
 * Each conversation has its own message history, a set of active geopolitical
 * perspectives, and a backend session identifier used for routing API calls.
 * The title starts as "New conversation" and is automatically updated to the
 * first user message (truncated to 50 characters).
 */
export interface Conversation {
  /** Unique identifier (UUID) for this conversation. */
  id: string;
  /** Display title shown in the sidebar. */
  title: string;
  /** Ordered list of messages in this conversation. */
  messages: Message[];
  /** Active geopolitical perspectives applied to analysis (e.g. ["US", "EU"]). */
  perspectives: string[];
  /** UUID sent to the backend to correlate all requests within this conversation. */
  sessionId: string;
  /**
   * Whether the conversation is currently awaiting user approval of an
   * AI-generated summary. When true, the ChatWindow replaces the text input
   * with Approve / Reject buttons.
   */
  isConfirming: boolean;
  /** Canonical dialogue stage received from backend. */
  stage: DialogueStage;
  /** Optional under-state for confirm stages, used by devtools/UI behavior. */
  subState: DialogueSubState;
  /** Unix timestamp (ms) when this conversation was created. */
  createdAt: number;
  /** Unix timestamp (ms) of the last mutation — used for sidebar sort order. */
  updatedAt: number;
}

/**
 * The shape of the data persisted to and loaded from localStorage.
 * Holds the full list of conversations and tracks which one is currently active.
 */
export interface ConversationStore {
  /** All conversations the user has created, in insertion order. */
  conversations: Conversation[];
  /** The id of the currently selected conversation, or null when none exist. */
  activeConversationId: string | null;
}

/**
 * Summary text
 */
export interface SummaryData {
  summary: string;
}

/**
 * Metadata about a source used in the conversation,
 * including author, year, title, and publisher.
 */
export interface CitationMetadata {
  author: string;
  year: string;
  title: string;
  publisher: string;
}

/**
 * Metadata about a source used in the conversation, including its unique ID,
 * reference string, type, and citation metadata.
 */
export interface Source {
  id: string;
  ref: string;
  source_type: string;
  citation?: CitationMetadata;
}

/**
 * A claim made by the AI system, including its unique ID, text content,
 * and reference to the source that supports it.
 */
export interface Claim {
  id: string;
  text: string;
  source_ref: string;
  source_id: string;
}

/**
 * A Priority Information Requirement (PIR) item, which includes the question being asked,
 * its priority level, the rationale behind it, and the source IDs that informed this PIR.
 */
export interface PirItem {
  question: string;
  priority: "high" | "medium" | "low";
  rationale: string;
  source_ids: string[]; // List of source IDs that informed this PIR
}

/**
 * The Pir generation data, that has:
 * - Reult: What the AI did
 * - PirItem[]: List of pirs generated
 * - Resoning: Reasoning behind AI's desicions
 */
export interface PirData {
  pir_text: string;
  claims: Claim[];
  sources: Source[];
  pirs: PirItem[];
  reasoning: string;
}
