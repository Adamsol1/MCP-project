import axios from "axios";
import type {
  DialogueAction,
  DialoguePhase,
  DialogueStage,
  DialogueSubState,
} from "../../types/dialogue";
import type { Message, PhaseReviewItem } from "../../types/conversation";
import { API_BACKEND_URL } from "../apiConfig";

const DIALOGUE_REQUEST_TIMEOUT_MS = 10 * 60 * 1000;
const DEV_REQUEST_TIMEOUT_MS = 30 * 1000;
const COLLECTION_STATUS_TIMEOUT_MS = 10 * 1000;

/** Shape of every backend response to a `sendMessage` call. */
export interface DialogueApiResponse {
  question: string;
  action: DialogueAction;
  stage?: DialogueStage;
  phase?: DialoguePhase;
  sub_state?: DialogueSubState;
  /** Present only during phase-review transitions; lists per-phase activity summaries. */
  review_activity?: PhaseReviewItem[];
}

/** Configuration for a council debate run passed through `DialogueSendOptions.councilSettings`. */
export interface CouncilRunSettings {
  mode: string;
  rounds: number;
  timeout_seconds: number;
  vote_retry_enabled: boolean;
  vote_retry_attempts: number;
}

/** Optional extras forwarded to `sendMessage` beyond the core message/session fields. */
export interface DialogueSendOptions {
  aiProvider?: "gemini" | "local";
  selectedSources?: string[];
  gatherMore?: boolean;
  councilDebatePoint?: string;
  councilFindingIds?: string[];
  councilPerspectives?: string[];
  councilSettings?: CouncilRunSettings;
  /** Per-source-tier timeframe codes for this submission (overrides settings defaults). */
  sourceTimeframes?: Record<string, string>;
}

/** (Dev only) Full internal state of a dialogue session returned by dev endpoints. */
export interface DialogueDevStateResponse {
  session_id: string;
  stage: DialogueStage;
  phase: DialoguePhase;
  sub_state: DialogueSubState;
  question_count: number;
  max_questions: number;
  /** Context fields the backend still needs before it considers the context sufficient. */
  missing_context_fields: string[];
  has_sufficient_context: boolean;
  awaiting_user_decision: boolean;
  has_modifications: boolean;
}

/** (Dev only) Summary of a saved session snapshot available for restoration. */
export interface DialogueDevSnapshot {
  session_id: string;
  title: string;
  stage: DialogueStage;
  phase: DialoguePhase;
  updated_at: string | null;
  /** Presence flags for each artifact type (true = artifact exists in this snapshot). */
  artifacts: Record<string, boolean>;
}

/** A hydrated `Message` without the client-side `id` field, as returned by the backend. */
export type DialogueDevHydratedMessage = Omit<Message, "id">;

/** (Dev only) Response from `restoreDevDialogueSnapshot`: dev state plus the restored message history. */
export interface DialogueDevRestoreResponse extends DialogueDevStateResponse {
  source_session_id: string;
  messages: DialogueDevHydratedMessage[];
}

/**
 * Sends a user message to the backend dialogue endpoint and returns the response.
 *
 * The backend maintains conversation state keyed by sessionId, so every request
 * within the same conversation must use the same sessionId.
 *
 * @param message           - The user's text input.
 * @param sessionId         - UUID that identifies the current conversation on the backend.
 * @param perspectives      - Geopolitical perspectives to apply (e.g. ["US", "EU"]).
 *                            Defaults to ["Global"] when omitted.
 * @param approved          - Pass true when the user has explicitly approved a pending
 *                            summary. Omit (undefined) for normal conversational turns.
 * @param language          - BCP-47 language code from the user's settings (e.g. "en", "no").
 *                            Instructs the backend / MCP tools to generate responses in
 *                            the selected language. Defaults to "en".
 * @param settingsTimeframe - Timeframe string from the user's settings parameters
 *                            (e.g. "Last 30 days"). When non-empty and the backend context
 *                            has no timeframe yet, the backend pre-fills it so the AI
 *                            skips the timeframe clarifying question. Defaults to "".
 * @returns The backend response object containing:
 *          - `question`  - the next system message text to display in the chat.
 *          - `action`    - canonical backend action.
 *          - `stage`     - canonical backend stage (optional fallback inferred from action).
 */
export async function sendMessage(
  message: string,
  sessionId: string,
  perspectives: string[] = ["NEUTRAL"],
  approved?: boolean,
  language: string = "en",
  settingsTimeframe: string = "",
  options: DialogueSendOptions = {},
) {
  const httpResonse = await axios.post<DialogueApiResponse>(
    `${API_BACKEND_URL}/api/dialogue/message`,
    {
      message,
      session_id: sessionId,
      perspectives,
      approved,
      language,
      ai_provider: options.aiProvider ?? "gemini",
      settings_timeframe: settingsTimeframe,
      settings_source_timeframes: options.sourceTimeframes ?? {},
      selected_sources: options.selectedSources ?? [],
      gather_more: options.gatherMore ?? false,
      council_debate_point: options.councilDebatePoint ?? "",
      council_finding_ids: options.councilFindingIds ?? [],
      council_perspectives: options.councilPerspectives ?? [],
      council_settings: options.councilSettings ?? null,
    },
    { timeout: DIALOGUE_REQUEST_TIMEOUT_MS },
  );

  return httpResonse.data;
}

export interface CollectionSourceStatus {
  call_count: number;
  last_called_at: string | null;
}

export interface PendingElicitation {
  message: string;
  options: string[];
}

export interface CollectionStatus {
  session_id: string;
  status: "collecting" | "complete";
  current_source: string | null;
  current_activity: string | null;
  sources: Record<string, CollectionSourceStatus>;
}

/**
 * Polls the backend for the current data-collection progress of a session.
 *
 * Used to drive the live "collecting sources" UI while the backend gathers
 * evidence before transitioning to the analysis phase.
 *
 * @param sessionId - UUID of the conversation whose collection status to fetch.
 * @returns The collection status object, or null if the request fails (e.g. no
 *          active collection for that session).
 */
export async function getCollectionStatus(
  sessionId: string,
): Promise<CollectionStatus | null> {
  try {
    const res = await axios.get<CollectionStatus>(
      `${API_BACKEND_URL}/api/dialogue/collection-status/${sessionId}`,
      { timeout: COLLECTION_STATUS_TIMEOUT_MS },
    );
    return res.data;
  } catch {
    return null;
  }
}

/**
 * Fetches any elicitation prompt that the backend is currently waiting on the
 * user to answer (e.g. a clarifying multiple-choice question injected mid-collection).
 *
 * @param sessionId - UUID of the conversation to check.
 * @returns The pending elicitation object (message + options), or null when
 *          there is no pending elicitation or the request fails.
 */
export async function getPendingElicitation(
  sessionId: string,
): Promise<PendingElicitation | null> {
  try {
    const res = await axios.get<{
      pending_elicitation: PendingElicitation | null;
    }>(`${API_BACKEND_URL}/api/dialogue/elicitation/pending/${sessionId}`, {
      timeout: COLLECTION_STATUS_TIMEOUT_MS,
    });
    return res.data.pending_elicitation;
  } catch {
    return null;
  }
}

/**
 * Submits the user's answer to a pending elicitation prompt.
 *
 * Should be called after the user selects one of the options returned by
 * `getPendingElicitation`. The backend unblocks the collection pipeline on
 * receipt.
 *
 * @param sessionId - UUID of the conversation containing the pending elicitation.
 * @param choice    - The option string the user selected.
 */
export async function respondToElicitation(
  sessionId: string,
  choice: string,
): Promise<void> {
  await axios.post(
    `${API_BACKEND_URL}/api/dialogue/elicitation/${sessionId}/respond`,
    { choice },
    { timeout: COLLECTION_STATUS_TIMEOUT_MS },
  );
}

/**
 * (Dev only) Fetches the full internal state of a dialogue session from the backend.
 *
 * Returns low-level fields like `missing_context_fields` and `has_sufficient_context`
 * that are not exposed in normal API responses, useful for debugging state transitions.
 *
 * @param sessionId - UUID of the session to inspect.
 * @returns A `DialogueDevStateResponse` with stage, phase, sub-state, and diagnostic flags.
 */
export async function getDevDialogueState(sessionId: string) {
  const httpResponse = await axios.get<DialogueDevStateResponse>(
    `${API_BACKEND_URL}/api/dialogue/dev/state`,
    {
      params: { session_id: sessionId },
      timeout: DEV_REQUEST_TIMEOUT_MS,
    },
  );
  return httpResponse.data;
}

/**
 * (Dev only) Lists all saved dialogue snapshots available for restoration.
 *
 * Snapshots represent persisted session states (stage + phase + artifacts) that
 * can be loaded into a target session via `restoreDevDialogueSnapshot` to
 * reproduce specific scenarios without replaying the full conversation.
 *
 * @returns An array of `DialogueDevSnapshot` summary objects.
 */
export async function listDevDialogueSnapshots() {
  const httpResponse = await axios.get<DialogueDevSnapshot[]>(
    `${API_BACKEND_URL}/api/dialogue/dev/snapshots`,
    { timeout: DEV_REQUEST_TIMEOUT_MS },
  );
  return httpResponse.data;
}

/**
 * (Dev only) Restores a saved snapshot into a target session at a specific stage/phase.
 *
 * Copies artifacts from `sourceSessionId` into `targetSessionId` and fast-forwards
 * the backend state machine to `targetStage`/`targetPhase`, allowing developers to
 * jump directly to a mid-conversation state for testing without replaying the full flow.
 *
 * @param sourceSessionId - UUID of the snapshot session to copy artifacts from.
 * @param targetSessionId - UUID of the session that will receive the restored state.
 * @param targetStage     - The `DialogueStage` to set on the target session.
 * @param targetPhase     - The `DialoguePhase` to set on the target session.
 * @returns A `DialogueDevRestoreResponse` including the hydrated message history
 *          and the resulting state of the target session.
 */
export async function restoreDevDialogueSnapshot(
  sourceSessionId: string,
  targetSessionId: string,
  targetStage: DialogueStage,
  targetPhase: DialoguePhase,
) {
  const httpResponse = await axios.post<DialogueDevRestoreResponse>(
    `${API_BACKEND_URL}/api/dialogue/dev/restore`,
    {
      source_session_id: sourceSessionId,
      target_session_id: targetSessionId,
      target_stage: targetStage,
      target_phase: targetPhase,
    },
    { timeout: DIALOGUE_REQUEST_TIMEOUT_MS },
  );
  return httpResponse.data;
}

/**
 * (Dev only) Forcibly sets the stage and sub-state of a dialogue session.
 *
 * Bypasses normal state-machine transitions, allowing developers to place a
 * session at any stage for testing. `subState` is only forwarded to the backend
 * for confirming stages (`summary_confirming`, `pir_confirming`); it is ignored
 * for all other stages.
 *
 * @param sessionId - UUID of the session to mutate.
 * @param stage     - The target `DialogueStage`.
 * @param subState  - The target `DialogueSubState` (default: `"awaiting_decision"`).
 * @returns The updated `DialogueDevStateResponse` reflecting the new state.
 */
export async function setDevDialogueState(
  sessionId: string,
  stage: DialogueStage,
  subState: DialogueSubState = "awaiting_decision",
) {
  const normalizedSubState =
    stage === "summary_confirming" || stage === "pir_confirming"
      ? subState
      : null;

  const httpResponse = await axios.post<DialogueDevStateResponse>(
    `${API_BACKEND_URL}/api/dialogue/dev/state`,
    {
      session_id: sessionId,
      stage,
      sub_state: normalizedSubState,
    },
    { timeout: DEV_REQUEST_TIMEOUT_MS },
  );
  return httpResponse.data;
}

/**
 * (Dev only) Resets a dialogue session back to its initial state.
 *
 * Clears all collected context, artifacts, and state-machine progress for the
 * given session, equivalent to starting the conversation over from scratch.
 * Useful for re-running a flow without creating a new session ID.
 *
 * @param sessionId - UUID of the session to reset.
 * @returns The resulting `DialogueDevStateResponse` after the reset.
 */
export async function resetDevDialogueState(sessionId: string) {
  const httpResponse = await axios.post<DialogueDevStateResponse>(
    `${API_BACKEND_URL}/api/dialogue/dev/reset`,
    null,
    {
      params: { session_id: sessionId },
      timeout: DEV_REQUEST_TIMEOUT_MS,
    },
  );
  return httpResponse.data;
}
