/**
 * React Query hooks for the notifications system.
 */

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useAuthStore } from '@/features/auth/useAuthStore';
import { supabase } from '@/lib/supabaseClient';

const NOTIFICATIONS_QUERY_KEY = 'notifications';
const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:3001';

// Types
export interface Notification {
  id: string;
  title: string;
  body: string;
  category: string;
  metadata: Record<string, unknown>;
  read: boolean;
  created_at: string;
}

export interface UnreadCount {
  count: number;
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
async function fetchNotifications(unreadOnly = false, limit = 50, offset = 0): Promise<Notification[]> {
  const headers = await getAuthHeaders();
  const params = new window.URLSearchParams({
    limit: limit.toString(),
    offset: offset.toString(),
  });
  if (unreadOnly) params.append('unread_only', 'true');

  const response = await fetch(`${API_BASE_URL}/api/notifications?${params}`, { headers });
  if (!response.ok) throw new Error('Failed to fetch notifications');
  return response.json();
}

async function fetchUnreadCount(): Promise<UnreadCount> {
  const headers = await getAuthHeaders();
  const response = await fetch(`${API_BASE_URL}/api/notifications/unread/count`, { headers });
  if (!response.ok) throw new Error('Failed to fetch unread count');
  return response.json();
}

async function markNotificationRead(notificationId: string): Promise<{ success: boolean }> {
  const headers = await getAuthHeaders();
  const response = await fetch(`${API_BASE_URL}/api/notifications/${notificationId}/read`, {
    method: 'POST',
    headers,
  });
  if (!response.ok) throw new Error('Failed to mark notification as read');
  return response.json();
}

async function markAllNotificationsRead(): Promise<{ success: boolean; count: number }> {
  const headers = await getAuthHeaders();
  const response = await fetch(`${API_BASE_URL}/api/notifications/read-all`, {
    method: 'POST',
    headers,
  });
  if (!response.ok) throw new Error('Failed to mark all as read');
  return response.json();
}

// Hooks

export function useNotifications(unreadOnly = false, limit = 50) {
  const user = useAuthStore((state) => state.user);

  return useQuery<Notification[], Error>({
    queryKey: [NOTIFICATIONS_QUERY_KEY, user?.id, unreadOnly, limit],
    queryFn: () => fetchNotifications(unreadOnly, limit),
    enabled: !!user,
    refetchInterval: 15000,
  });
}

export function useUnreadCount() {
  const user = useAuthStore((state) => state.user);

  return useQuery<UnreadCount, Error>({
    queryKey: [NOTIFICATIONS_QUERY_KEY, 'unread', 'count', user?.id],
    queryFn: fetchUnreadCount,
    enabled: !!user,
    refetchInterval: 15000,
  });
}

export function useMarkNotificationRead() {
  const queryClient = useQueryClient();

  return useMutation<{ success: boolean }, Error, string>({
    mutationFn: markNotificationRead,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: [NOTIFICATIONS_QUERY_KEY] });
    },
  });
}

export function useMarkAllRead() {
  const queryClient = useQueryClient();

  return useMutation<{ success: boolean; count: number }, Error, void>({
    mutationFn: markAllNotificationsRead,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: [NOTIFICATIONS_QUERY_KEY] });
    },
  });
}
