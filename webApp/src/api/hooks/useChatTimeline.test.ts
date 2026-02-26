import { vi, describe, it, expect } from 'vitest';
import { renderHook } from '@testing-library/react';

vi.mock('@/stores/useChatStore', () => ({
  useChatStore: vi.fn(),
}));

vi.mock('@/api/hooks/useNotificationHooks', () => ({
  useNotifications: vi.fn(),
}));

import { useChatStore } from '@/stores/useChatStore';
import { useNotifications } from '@/api/hooks/useNotificationHooks';
import { useChatTimeline } from './useChatTimeline';
import type { ChatMessage } from '@/stores/useChatStore';

const mockUseChatStore = vi.mocked(useChatStore);
const mockUseNotifications = vi.mocked(useNotifications);

const chatMessages: ChatMessage[] = [
  {
    id: 'msg-1',
    text: 'Hello',
    sender: 'user',
    timestamp: new Date('2026-02-17T10:00:00Z'),
  },
  {
    id: 'msg-2',
    text: 'Hi there',
    sender: 'ai',
    timestamp: new Date('2026-02-17T10:01:00Z'),
  },
];

describe('useChatTimeline', () => {
  it('returns only chat messages when no notifications', () => {
    mockUseChatStore.mockReturnValue(chatMessages as unknown as ReturnType<typeof useChatStore>);
    mockUseNotifications.mockReturnValue({ data: [] } as ReturnType<typeof useNotifications>);

    const { result } = renderHook(() => useChatTimeline());
    expect(result.current).toHaveLength(2);
    expect(result.current[0].sender).toBe('user');
    expect(result.current[1].sender).toBe('ai');
  });

  it('merges notifications into message timeline', () => {
    mockUseChatStore.mockReturnValue(chatMessages as unknown as ReturnType<typeof useChatStore>);
    mockUseNotifications.mockReturnValue({
      data: [
        {
          id: 'n1',
          title: 'Task done',
          body: 'The task is complete',
          category: 'agent_result',
          metadata: {},
          read: false,
          created_at: '2026-02-17T10:00:30Z',
          type: 'notify',
          requires_approval: false,
        },
      ],
    } as ReturnType<typeof useNotifications>);

    const { result } = renderHook(() => useChatTimeline());
    expect(result.current).toHaveLength(3);
    // Sorted by timestamp: msg-1 (10:00), notif (10:00:30), msg-2 (10:01)
    expect(result.current[0].id).toBe('msg-1');
    expect(result.current[1].id).toBe('notif-n1');
    expect(result.current[2].id).toBe('msg-2');
  });

  it('filters out agent_only notifications', () => {
    mockUseChatStore.mockReturnValue(chatMessages as unknown as ReturnType<typeof useChatStore>);
    mockUseNotifications.mockReturnValue({
      data: [
        {
          id: 'n-hidden',
          title: 'Internal',
          body: 'Should not appear',
          category: 'heartbeat',
          metadata: {},
          read: false,
          created_at: '2026-02-17T10:00:30Z',
          type: 'agent_only',
          requires_approval: false,
        },
      ],
    } as ReturnType<typeof useNotifications>);

    const { result } = renderHook(() => useChatTimeline());
    expect(result.current).toHaveLength(2);
    expect(result.current.find((m) => m.id === 'notif-n-hidden')).toBeUndefined();
  });

  it('maps approval notifications with sender=approval', () => {
    mockUseChatStore.mockReturnValue([] as unknown as ReturnType<typeof useChatStore>);
    mockUseNotifications.mockReturnValue({
      data: [
        {
          id: 'approval-1',
          title: 'Needs approval',
          body: 'Approve the email?',
          category: 'approval_needed',
          metadata: { tool_name: 'send_email', action_id: 'act-1' },
          read: false,
          created_at: '2026-02-17T11:00:00Z',
          type: 'notify',
          requires_approval: true,
          pending_action_id: 'act-1',
        },
      ],
    } as ReturnType<typeof useNotifications>);

    const { result } = renderHook(() => useChatTimeline());
    expect(result.current).toHaveLength(1);
    const item = result.current[0];
    expect(item.sender).toBe('approval');
    expect(item.action_id).toBe('act-1');
    expect(item.action_tool_name).toBe('send_email');
  });

  it('keeps resolved approval cards in timeline (AC-27)', () => {
    mockUseChatStore.mockReturnValue([] as unknown as ReturnType<typeof useChatStore>);
    mockUseNotifications.mockReturnValue({
      data: [
        {
          id: 'approval-resolved',
          title: 'Action approved',
          body: 'Task deleted',
          category: 'approval_needed',
          metadata: { tool_name: 'delete_tasks', action_status: 'approved' },
          read: true,
          created_at: '2026-02-17T11:00:00Z',
          type: 'notify',
          requires_approval: true,
          pending_action_id: 'act-1',
        },
      ],
    } as ReturnType<typeof useNotifications>);

    const { result } = renderHook(() => useChatTimeline());
    expect(result.current).toHaveLength(1);
    expect(result.current[0].id).toBe('notif-approval-resolved');
  });

  it('filters out silent notifications (AC-28)', () => {
    mockUseChatStore.mockReturnValue([] as unknown as ReturnType<typeof useChatStore>);
    mockUseNotifications.mockReturnValue({
      data: [
        {
          id: 'silent-audit',
          title: 'Audit trail',
          body: 'Action completed',
          category: 'audit',
          metadata: {},
          read: false,
          created_at: '2026-02-17T11:00:00Z',
          type: 'silent',
          requires_approval: false,
        },
      ],
    } as ReturnType<typeof useNotifications>);

    const { result } = renderHook(() => useChatTimeline());
    expect(result.current).toHaveLength(0);
  });

  it('sorts items by timestamp', () => {
    mockUseChatStore.mockReturnValue([
      { id: 'msg-late', text: 'Late', sender: 'user', timestamp: new Date('2026-02-17T12:00:00Z') },
      { id: 'msg-early', text: 'Early', sender: 'user', timestamp: new Date('2026-02-17T09:00:00Z') },
    ] as unknown as ReturnType<typeof useChatStore>);
    mockUseNotifications.mockReturnValue({
      data: [
        {
          id: 'n-mid',
          title: 'Mid',
          body: 'Middle',
          category: 'info',
          metadata: {},
          read: false,
          created_at: '2026-02-17T10:30:00Z',
          type: 'notify',
          requires_approval: false,
        },
      ],
    } as ReturnType<typeof useNotifications>);

    const { result } = renderHook(() => useChatTimeline());
    expect(result.current[0].id).toBe('msg-early');
    expect(result.current[1].id).toBe('notif-n-mid');
    expect(result.current[2].id).toBe('msg-late');
  });
});
