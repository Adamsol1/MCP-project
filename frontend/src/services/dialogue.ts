import axios from "axios";

/** Base URL for the backend REST API. */
const API_BACKEND_URL = "http://localhost:8000";

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
 *          - `question`  — the next system message text to display in the chat.
 *          - `is_final`  — true when the backend is requesting user approval.
 */
export async function sendMessage(
  message: string,
  sessionId: string,
  perspectives: string[] = ["NEUTRAL"],
  approved?: boolean,
  language: string = "en",
  settingsTimeframe: string = "",
) {
  const httpResonse = await axios.post(
    `${API_BACKEND_URL}/api/dialogue/message`,
    {
      message,
      session_id: sessionId,
      perspectives,
      approved,
      language,
      settings_timeframe: settingsTimeframe,
    },
  );

  return httpResonse.data;
}
