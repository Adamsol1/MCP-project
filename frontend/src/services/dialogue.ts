import axios from "axios";

/** Base URL for the backend REST API. */
const API_BACKEND_URL = "http://localhost:8000";

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
  const httpResonse = await axios.post(
    `${API_BACKEND_URL}/api/dialogue/message`,
    { message, session_id: sessionId, perspectives, approved },
  );

  return httpResonse.data;
}
