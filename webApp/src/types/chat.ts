// Custom chat types for Clarity v2
// These types are specific to the chat functionality and AI interactions

export interface ChatRequest {
  message: string;
  session_id?: string;
  agent_name?: string;
  context?: Record<string, any>;
}

export interface ChatResponse {
  message: string;
  session_id: string;
  agent_name: string;
  actions?: AgentAction[];
  metadata?: Record<string, any>;
  timestamp: string;
}

export interface AgentAction {
  type: string;
  data: Record<string, any>;
  status: 'pending' | 'in_progress' | 'completed' | 'failed';
  result?: any;
  error?: string;
}

export interface ChatSession {
  id: string;
  title?: string;
  created_at: string;
  updated_at: string;
  message_count: number;
}

export interface ChatMessage {
  id: string;
  session_id: string;
  role: 'user' | 'assistant' | 'system';
  content: string;
  actions?: AgentAction[];
  timestamp: string;
}

// Tool execution types
export interface ToolCall {
  id: string;
  name: string;
  arguments: Record<string, any>;
}

export interface ToolResult {
  id: string;
  result: any;
  error?: string;
  metadata?: Record<string, any>;
}

// Chat state types for Zustand store
export interface ChatState {
  sessions: ChatSession[];
  currentSession: ChatSession | null;
  messages: ChatMessage[];
  isLoading: boolean;
  error: string | null;
  
  // Actions
  createSession: (title?: string) => Promise<ChatSession>;
  loadSession: (sessionId: string) => Promise<void>;
  sendMessage: (message: string, agentName?: string) => Promise<ChatResponse>;
  clearError: () => void;
  refreshSessions: () => Promise<void>;
} 