import { vi, describe, it, expect, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';

vi.mock('@/api/hooks/useNotificationHooks', () => ({
  useMarkNotificationRead: vi.fn(),
  useSubmitNotificationFeedback: vi.fn(),
}));

import { useMarkNotificationRead, useSubmitNotificationFeedback } from '@/api/hooks/useNotificationHooks';
import { NotificationInlineMessage } from './NotificationInlineMessage';
import type { ChatMessage } from '@/stores/useChatStore';

const mockMarkReadMutate = vi.fn();
const mockFeedbackMutate = vi.fn();

beforeEach(() => {
  vi.clearAllMocks();
  vi.mocked(useMarkNotificationRead).mockReturnValue({
    mutate: mockMarkReadMutate,
    isPending: false,
  } as ReturnType<typeof useMarkNotificationRead>);

  vi.mocked(useSubmitNotificationFeedback).mockReturnValue({
    mutate: mockFeedbackMutate,
    isPending: false,
  } as ReturnType<typeof useSubmitNotificationFeedback>);
});

const baseMessage: ChatMessage = {
  id: 'notif-abc123',
  text: 'The agent finished the analysis.',
  sender: 'notification',
  timestamp: new Date('2026-02-17T10:00:00Z'),
  notification_id: 'abc123',
  notification_category: 'agent_result',
  notification_title: 'Analysis complete',
  notification_feedback: null,
};

describe('NotificationInlineMessage', () => {
  it('renders title and body', () => {
    render(<NotificationInlineMessage message={baseMessage} />);
    expect(screen.getByText('Analysis complete')).toBeTruthy();
    expect(screen.getByText('The agent finished the analysis.')).toBeTruthy();
  });

  it('shows feedback buttons when no feedback exists', () => {
    render(<NotificationInlineMessage message={baseMessage} />);
    expect(screen.getByRole('button', { name: 'Mark as helpful' })).toBeTruthy();
    expect(screen.getByRole('button', { name: 'Mark as not helpful' })).toBeTruthy();
  });

  it('shows selected state when useful feedback exists', () => {
    const msg = { ...baseMessage, notification_feedback: 'useful' as const };
    render(<NotificationInlineMessage message={msg} />);
    const thumbsUp = screen.getByRole('button', { name: 'Mark as helpful' });
    expect(thumbsUp.className).toContain('text-brand-primary');
  });

  it('shows selected state when not_useful feedback exists', () => {
    const msg = { ...baseMessage, notification_feedback: 'not_useful' as const };
    render(<NotificationInlineMessage message={msg} />);
    const thumbsDown = screen.getByRole('button', { name: 'Mark as not helpful' });
    expect(thumbsDown.className).toContain('text-brand-primary');
  });

  it('calls mark-read on mount', () => {
    render(<NotificationInlineMessage message={baseMessage} />);
    expect(mockMarkReadMutate).toHaveBeenCalledWith('abc123');
  });

  it('does not call mark-read when notification_id is missing', () => {
    const msg = { ...baseMessage, notification_id: undefined };
    render(<NotificationInlineMessage message={msg} />);
    expect(mockMarkReadMutate).not.toHaveBeenCalled();
  });
});
