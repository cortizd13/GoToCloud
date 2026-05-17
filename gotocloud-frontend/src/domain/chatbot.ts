export interface ChatbotMessageRequest {
  message: string;
  sessionId?: string;
  model?: string;
}

export interface ChatbotMessageResponse {
  sessionId: string;
  reply: string;
  toolCalls: string[];
  ended: boolean;
}
