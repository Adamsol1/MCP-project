import axios from "axios";
import type {
  DialogueAction,
  DialogueStage,
  DialogueSubState,
} from "../types/dialogue";

/** Base URL for the backend REST API. */
const API_BACKEND_URL = "http://localhost:8000";

export interface DialogueApiResponse {
  question: string;
  action: DialogueAction;
  stage?: DialogueStage;
  sub_state?: DialogueSubState;
}

export interface DialogueSendOptions {
  selectedSources?: string[];
  gatherMore?: boolean;
}

export interface DialogueDevStateResponse {
  session_id: string;
  stage: DialogueStage;
  sub_state: DialogueSubState;
  question_count: number;
  max_questions: number;
  missing_context_fields: string[];
  has_sufficient_context: boolean;
  awaiting_user_decision: boolean;
  has_modifications: boolean;
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
 *                            Defaults to ["NEUTRAL"] when omitted.
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
      settings_timeframe: settingsTimeframe,
      selected_sources: options.selectedSources ?? [],
      gather_more: options.gatherMore ?? false,
    },
  );

  return httpResonse.data;
}

export async function getDevDialogueState(sessionId: string) {
  const httpResponse = await axios.get<DialogueDevStateResponse>(
    `${API_BACKEND_URL}/api/dialogue/dev/state`,
    {
      params: { session_id: sessionId },
    },
  );
  return httpResponse.data;
}

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
  );
  return httpResponse.data;
}

export async function resetDevDialogueState(sessionId: string) {
  const httpResponse = await axios.post<DialogueDevStateResponse>(
    `${API_BACKEND_URL}/api/dialogue/dev/reset`,
    null,
    {
      params: { session_id: sessionId },
    },
  );
  return httpResponse.data;
}
