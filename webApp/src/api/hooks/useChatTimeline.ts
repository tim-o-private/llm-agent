/**
 * Merges chat messages from Zustand store with notifications from React Query
 * into a unified timeline sorted by timestamp.
 *
 * Follows A4: notifications stay in React Query (server state),
 * messages stay in Zustand (client state); merge is a derived computation.
 *
 * Only shows notifications belonging to the current chat session (session_id
 * filtering) so that unrelated notifications from other chats or background
 * jobs don't flood the timeline.
 */

import { useMemo } from 'react';
import { useChatStore, type ChatMessage } from '@/stores/useChatStore';
import { useNotifications } from '@/api/hooks/useNotificationHooks';

export function useChatTimeline(): ChatMessage[] {
  const messages = useChatStore((s) => s.messages);
  const activeChatId = useChatStore((s) => s.activeChatId);
  const { data: notifications } = useNotifications(false, 100, activeChatId);

  const notificationMessages: ChatMessage[] = useMemo(() => {
    return (notifications ?? [])
      .filter((n) => {
        // Never show agent-only notifications
        if (n.type === 'agent_only') return false;
        // Always show approval cards — resolved cards fold result into the same card (AC-27)
        if (n.requires_approval) return true;
        // Hide silent notifications and read non-approval notifications
        if (n.type === 'silent') return false;
        if (n.read) return false;
        return true;
      })
      .map((n) => ({
        id: `notif-${n.id}`,
        text: n.body,
        sender: n.requires_approval ? ('approval' as const) : ('notification' as const),
        timestamp: new Date(n.created_at),
        notification_id: n.id,
        notification_category: n.category,
        notification_title: n.title,
        notification_feedback: n.feedback,
        action_id: n.pending_action_id ?? (n.metadata?.action_id as string | undefined),
        action_tool_name: n.metadata?.tool_name as string | undefined,
        action_tool_args: n.metadata?.tool_args as Record<string, unknown> | undefined,
        action_status: n.metadata?.action_status as string | undefined,
      }));
  }, [notifications]);

  return useMemo(() => {
    return [...messages, ...notificationMessages].sort(
      (a, b) => a.timestamp.getTime() - b.timestamp.getTime(),
    );
  }, [messages, notificationMessages]);
}
