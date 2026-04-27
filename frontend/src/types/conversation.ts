import type { AnalysisResponse, CouncilNote } from "./analysis";
import type {
  DialoguePhase,
  DialogueStage,
  DialogueSubState,
} from "./dialogue";

/** A single chat message exchanged between the user and the system. */
export interface Message {
  /** Unique identifier (UUID) for this message. */
  id: string;
  /** The text content of the message. */
  text: string;
  /** Who sent the message - the human user or the AI system. */
  sender: "user" | "system";
  type?:
    | "question"
    | "summary"
    | "pir"
    | "plan"
    | "suggested_sources"
    | "collection"
    | "processing"
    | "analysis"
    | "council"
    | "error"
    | "complete";
  data?:
    | SummaryData
    | PirData
    | CollectionPlanData
    | SuggestedSourcesData
    | CollectionSummaryData
    | CollectionDisplayData
    | ProcessingData
    | AnalysisResponse
    | CouncilNote;
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
   * AI-generated output. When true, the ChatWindow replaces the text input
   * with decision controls.
   */
  isConfirming: boolean;
  /** Canonical dialogue stage received from backend. */
  stage: DialogueStage;
  /** Canonical backend phase used for tracker and workspace routing. */
  phase: DialoguePhase;
  /** Optional under-state for confirm stages, used by devtools/UI behavior. */
  subState: DialogueSubState;
  /** Unix timestamp (ms) when this conversation was created. */
  createdAt: number;
  /** Unix timestamp (ms) of the last mutation - used for sidebar sort order. */
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
 * Direction summary payload.
 */
export interface SummaryData {
  summary: string;
}

/**
 * A single step in the collection plan with a short title and detailed description.
 */
export interface CollectionPlanStep {
  title: string;
  description: string;
  suggested_sources?: string[];
}

/**
 * Collection plan payload generated from approved PIRs.
 */
export interface CollectionPlanData {
  plan: string;
  steps?: CollectionPlanStep[];
  suggested_sources: string[];
}

/**
 * Source names suggested by the backend for source selection.
 */
export type SuggestedSourcesData = string[];

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
  source_ids: string[];
}

/**
 * The PIR generation data.
 */
export interface PirData {
  pir_text: string;
  claims: Claim[];
  sources: Source[];
  pirs: PirItem[];
  reasoning: string;
}

/**
 * Collection summary payload shown during collection review.
 */
export interface CollectionSummaryData {
  summary: string;
  sources_used: string[];
  gaps: string | null;
}

/**
 * The data structure for displaying collected information from various sources during the collection review stage.
 */
export interface CollectedItem {
  source: string;
  resource_id: string | null;
  content: string;
  // Optional fields populated by the url_context second pass (fetch_page items only)
  title?: string;
  apa_citation?: string;
  author?: string;
  date?: string;
  publisher?: string;
}

/**
 * Summary of the sources used in the collection, including their display names, counts, resource IDs, and whether they contain content.
 */
export interface CollectionSourceSummary {
  display_name: string;
  count: number;
  resource_ids: string[];
  has_content: boolean;
}

/**
 * A single AI review attempt for any phase (direction, collection, processing).
 * Replaces the old ActivitySummaryItem — decoupled from the collection object.
 */
export interface PhaseReviewItem {
  phase: "direction" | "collection" | "processing" | "analysis";
  attempt: number;
  reviewer_approved: boolean;
  reviewer_suggestions: string | null;
  /** Sources queried by the collector — only populated in the collection phase. */
  sources_used: string[];
  /** Full transcript of what the AI generated in this attempt. */
  generated_content: string | null;
}

export interface ProcessingFinding {
  id: string;
  title: string;
  finding: string;
  evidence_summary: string;
  source: string;
  confidence: number;
  relevant_to: string[];
  why_it_matters: string;
  uncertainties: string[];
  supporting_data?: {
    entities?: string[];
    timestamps?: string[];
    locations?: string[];
    kb_refs?: string[];
    attack_ids?: string[];
    domains?: string[];
    source_urls?: string[];
    source_refs?: string[];
    iocs?: string[];
  };
}

export interface ProcessingData {
  findings: ProcessingFinding[];
  gaps: string[];
}

/**
 * The data structure for displaying the collected information from various sources during the collection review stage, including the collected data, a summary of the sources used, and any parsing errors encountered.
 */
export interface CollectionDisplayData {
  collected_data: CollectedItem[];
  source_summary: CollectionSourceSummary[];
  parse_error?: string;
}
