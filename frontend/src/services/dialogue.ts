import axios from "axios";
import type { DialogueStage, DialogueSubState } from "../types/dialogue";

/** Base URL for the backend REST API. */
const API_BACKEND_URL = "http://localhost:8000";

export interface DialogueApiResponse {
  question: string;
  type: string;
  is_final: boolean;
  stage?: DialogueStage;
  sub_state?: DialogueSubState;
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
 * @param message      - The user's text input.
 * @param sessionId    - UUID that identifies the current conversation on the backend.
 * @param perspectives - Geopolitical perspectives to apply (e.g. ["US", "EU"]).
 *                       Defaults to ["NEUTRAL"] when omitted.
 * @param approved     - Pass true when the user has explicitly approved a pending
 *                       summary. Omit (undefined) for normal conversational turns.
 * @returns The backend response object containing:
 *          - `question`  — the next system message text to display in the chat.
 *          - `is_final`  — true when the backend is requesting user approval.
 */
export async function sendMessage(
  message: string,
  sessionId: string,
  perspectives: string[] = ["NEUTRAL"],
  approved?: boolean,
) {
  const httpResonse = await axios.post<DialogueApiResponse>(
    `${API_BACKEND_URL}/api/dialogue/message`,
    { message, session_id: sessionId, perspectives, approved },
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
