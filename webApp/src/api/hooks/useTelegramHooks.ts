/**
 * React Query hooks for Telegram account linking.
 */

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useAuthStore } from '@/features/auth/useAuthStore';
import { supabase } from '@/lib/supabaseClient';

const TELEGRAM_QUERY_KEY = 'telegram';
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || '';

// Types
export interface TelegramStatus {
  linked: boolean;
  linked_at: string | null;
  linked_session_id: string | null;
}

export interface LinkToken {
  token: string;
  bot_username: string;
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
async function fetchTelegramStatus(): Promise<TelegramStatus> {
  const headers = await getAuthHeaders();
  const response = await fetch(`${API_BASE_URL}/api/telegram/status`, { headers });
  if (!response.ok) throw new Error('Failed to fetch Telegram status');
  return response.json();
}

async function fetchLinkToken(): Promise<LinkToken> {
  const headers = await getAuthHeaders();
  const response = await fetch(`${API_BASE_URL}/api/telegram/link-token`, { headers });
  if (!response.ok) throw new Error('Failed to generate link token');
  return response.json();
}

async function unlinkTelegram(): Promise<{ success: boolean }> {
  const headers = await getAuthHeaders();
  const response = await fetch(`${API_BASE_URL}/api/telegram/unlink`, {
    method: 'POST',
    headers,
  });
  if (!response.ok) throw new Error('Failed to unlink Telegram');
  return response.json();
}

// Hooks

export function useTelegramStatus() {
  const user = useAuthStore((state) => state.user);

  return useQuery<TelegramStatus, Error>({
    queryKey: [TELEGRAM_QUERY_KEY, 'status', user?.id],
    queryFn: fetchTelegramStatus,
    enabled: !!user,
    staleTime: 60_000,
  });
}

export function useGenerateLinkToken() {
  return useMutation<LinkToken, Error, void>({
    mutationFn: fetchLinkToken,
  });
}

export function useUnlinkTelegram() {
  const queryClient = useQueryClient();

  return useMutation<{ success: boolean }, Error, void>({
    mutationFn: unlinkTelegram,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: [TELEGRAM_QUERY_KEY] });
    },
  });
}
