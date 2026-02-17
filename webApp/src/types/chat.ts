export interface ChatRequest {
  agent_name: string;
  message: string;
  session_id: string;
}

export interface ChatResponse {
  session_id: string;
  response: string;
  tool_name?: string | null;
  tool_input?: Record<string, unknown> | null;
  error?: string | null;
}
