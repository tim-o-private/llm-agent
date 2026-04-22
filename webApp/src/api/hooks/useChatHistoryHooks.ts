/**
 * React Query hooks for the chat history API.
 *
 * Provides session listing (with channel filter) and message fetching
 * for the unified session registry.
 */

import { useEffect, useState } from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { supabase } from '@/lib/supabaseClient';
import { authHeaders } from '@/lib/apiClient';
import { loadHistoricalMessages, PARSED_MESSAGES_QUERY_KEY } from '@/stores/useChatStore';

function useAuthUserId(): string | null {
  const [userId, setUserId] = useState<string | null>(null);
  useEffect(() => {
    supabase.auth.getSession().then(({ data: { session } }) => {
      setUserId(session?.user?.id ?? null);
    });
    const {
      data: { subscription },
    } = supabase.auth.onAuthStateChange((_event, session) => {
      setUserId(session?.user?.id ?? null);
    });
    return () => subscription.unsubscribe();
  }, []);
  return userId;
}

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

// API functions

async function fetchChatSessions(
  channel?: string,
  limit = 50,
  offset = 0,
): Promise<ChatSession[]> {
  const headers = await authHeaders();
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
  const headers = await authHeaders();
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
  const userId = useAuthUserId();

  return useQuery<ChatSession[], Error>({
    queryKey: [CHAT_HISTORY_QUERY_KEY, 'sessions', userId, channel, limit],
    queryFn: () => fetchChatSessions(channel, limit),
    enabled: !!userId,
  });
}

export function useChatMessages(sessionId: string | null, limit = 50) {
  const userId = useAuthUserId();

  return useQuery<ChatHistoryMessage[], Error>({
    queryKey: [CHAT_HISTORY_QUERY_KEY, 'messages', sessionId, userId, limit],
    queryFn: () => fetchChatMessages(sessionId!, limit),
    enabled: !!userId && !!sessionId,
    refetchInterval: 5000,
  });
}

/**
 * Prefetches parsed messages for all conversations once the session list loads.
 * Populates React Query cache so switchToConversationAsync finds data instantly.
 */
export function usePrefetchConversationMessages(sessions: ChatSession[] | undefined) {
  const queryClient = useQueryClient();

  useEffect(() => {
    if (!sessions || sessions.length === 0) return;

    // Deduplicate by chat_id, keep most recent per chat_id
    const seen = new Set<string>();
    const uniqueChatIds: string[] = [];
    for (const session of sessions) {
      if (session.chat_id && !seen.has(session.chat_id)) {
        seen.add(session.chat_id);
        uniqueChatIds.push(session.chat_id);
      }
    }

    // Prefetch messages for each conversation (React Query deduplicates concurrent calls)
    for (const chatId of uniqueChatIds) {
      queryClient.prefetchQuery({
        queryKey: [PARSED_MESSAGES_QUERY_KEY, chatId],
        queryFn: () => loadHistoricalMessages(chatId),
        staleTime: 1000 * 60 * 5, // 5 minutes — match default
      });
    }
  }, [sessions, queryClient]);
}
