import axios from "axios";
import { API_BACKEND_URL } from "../apiConfig";

const DEV_LLM_CHAT_TIMEOUT_MS = 10 * 60 * 1000;

export type DevLlmChatRole = "system" | "user" | "assistant";

export interface DevLlmChatMessage {
  role: DevLlmChatRole;
  content: string;
}

export interface DevLlmChatResponse {
  message: string;
  provider: string;
  model: string;
}

export async function sendDevLlmChat(
  messages: DevLlmChatMessage[],
  aiProvider?: "gemini" | "local",
  model?: string,
): Promise<DevLlmChatResponse> {
  const response = await axios.post<DevLlmChatResponse>(
    `${API_BACKEND_URL}/api/dev/llm-chat`,
    {
      messages,
      ai_provider: aiProvider,
      model: model?.trim() || null,
    },
    { timeout: DEV_LLM_CHAT_TIMEOUT_MS },
  );
  return response.data;
}
