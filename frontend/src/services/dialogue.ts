import axios from "axios";

const API_BACKEND_URL = "http://localhost:8000"; //Backend server URL

export async function sendMessage(
  message: string,
  sessionId: string,
  perspectives: string[] = ["NEUTRAL"],
) {
  const httpResonse = await axios.post(
    `${API_BACKEND_URL}/api/dialogue/message`,
    { message, session_id: sessionId, perspectives },
  );

  return httpResonse.data;
}
