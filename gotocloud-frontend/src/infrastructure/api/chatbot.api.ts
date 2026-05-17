import type { ChatbotMessageRequest, ChatbotMessageResponse } from "../../domain/chatbot";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://127.0.0.1:8000";

type ChatbotMessageApiResponse = {
  session_id: string;
  reply: string;
  tool_calls: string[];
  ended: boolean;
};

export async function sendChatbotMessage(
  request: ChatbotMessageRequest,
  signal?: AbortSignal,
): Promise<ChatbotMessageResponse> {
  const response = await fetch(`${API_BASE_URL}/chat/message`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      message: request.message,
      session_id: request.sessionId,
    }),
    signal,
  });

  if (!response.ok) {
    let message = "No se pudo conectar con Camila";
    try {
      const body = await response.json();
      message = body.detail ?? message;
    } catch {
      message = response.statusText || message;
    }
    throw new Error(message);
  }

  const data = (await response.json()) as ChatbotMessageApiResponse;

  return {
    sessionId: data.session_id,
    reply: data.reply,
    toolCalls: data.tool_calls,
    ended: data.ended,
  };
}
