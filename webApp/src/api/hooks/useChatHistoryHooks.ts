/**
 * React Query hooks for the chat history API.
 *
 * Provides session listing (with channel filter) and message fetching
 * for the unified session registry.
 */

import { useQuery } from '@tanstack/react-query';
import { useAuthStore } from '@/features/auth/useAuthStore';
import { supabase } from '@/lib/supabaseClient';

const CHAT_HISTORY_QUERY_KEY = 'chat-history';
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || '';

// Types

export interface ChatSession {
  id: string;
  user_id: string;
  chat_id: string | null;
  agent_name: string;
  channel: string;
  session_id: string | null;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface ChatHistoryMessage {
  id: number;
  session_id: string;
  message: Record<string, unknown>;
  created_at: string;
}

// Helper to get auth headers
async function getAuthHeaders(): Promise<Record<string, string>> {
  const {
    data: { session },
  } = await supabase.auth.getSession();
  if (!session?.access_token) {
    throw new Error('User not authenticated');
  }
  return {
    'Content-Type': 'application/json',
    Authorization: `Bearer ${session.access_token}`,
  };
}

// API functions

async function fetchChatSessions(
  channel?: string,
  limit = 50,
  offset = 0,
): Promise<ChatSession[]> {
  const headers = await getAuthHeaders();
  const params = new window.URLSearchParams({
    limit: limit.toString(),
    offset: offset.toString(),
  });
  if (channel) params.append('channel', channel);

  const response = await fetch(`${API_BASE_URL}/api/chat/sessions?${params}`, { headers });
  if (!response.ok) throw new Error('Failed to fetch chat sessions');
  return response.json();
}

async function fetchChatMessages(
  sessionId: string,
  limit = 50,
  beforeId?: number,
): Promise<ChatHistoryMessage[]> {
  const headers = await getAuthHeaders();
  const params = new window.URLSearchParams({
    limit: limit.toString(),
  });
  if (beforeId !== undefined) params.append('before_id', beforeId.toString());

  const response = await fetch(
    `${API_BASE_URL}/api/chat/sessions/${encodeURIComponent(sessionId)}/messages?${params}`,
    { headers },
  );
  if (!response.ok) throw new Error('Failed to fetch chat messages');
  return response.json();
}

// Hooks

export function useChatSessions(channel?: string, limit = 50) {
  const user = useAuthStore((state) => state.user);

  return useQuery<ChatSession[], Error>({
    queryKey: [CHAT_HISTORY_QUERY_KEY, 'sessions', user?.id, channel, limit],
    queryFn: () => fetchChatSessions(channel, limit),
    enabled: !!user,
  });
}

export function useChatMessages(sessionId: string | null, limit = 50) {
  const user = useAuthStore((state) => state.user);

  return useQuery<ChatHistoryMessage[], Error>({
    queryKey: [CHAT_HISTORY_QUERY_KEY, 'messages', sessionId, user?.id, limit],
    queryFn: () => fetchChatMessages(sessionId!, limit),
    enabled: !!user && !!sessionId,
    refetchInterval: 5000,
  });
}
