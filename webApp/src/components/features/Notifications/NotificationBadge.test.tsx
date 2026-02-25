/* eslint-disable @typescript-eslint/no-explicit-any */
import { vi, describe, it, expect, beforeEach } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';

vi.mock('@/api/hooks/useNotificationHooks', () => ({
  useUnreadCount: vi.fn(),
  useNotifications: vi.fn(),
  useMarkNotificationRead: vi.fn(),
  useMarkAllRead: vi.fn(),
  useSubmitNotificationFeedback: vi.fn(),
}));

import {
  useUnreadCount,
  useNotifications,
  useMarkNotificationRead,
  useMarkAllRead,
  useSubmitNotificationFeedback,
} from '@/api/hooks/useNotificationHooks';
import { NotificationBadge } from './NotificationBadge';

const mockUseUnreadCount = vi.mocked(useUnreadCount);
const mockUseNotifications = vi.mocked(useNotifications);
const mockMarkRead = vi.fn();
const mockMarkAllRead = vi.fn();
const mockSubmitFeedback = vi.fn();

const sampleNotifications = [
  {
    id: 'n1',
    title: 'Agent completed task',
    body: 'The architect agent finished the review.',
    category: 'agent_result',
    metadata: {},
    read: false,
    created_at: '2026-02-17T10:00:00Z',
  },
  {
    id: 'n2',
    title: 'Approval needed',
    body: 'Action requires your approval.',
    category: 'approval_needed',
    metadata: {},
    read: true,
    created_at: '2026-02-16T08:00:00Z',
  },
];

describe('NotificationBadge', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockUseUnreadCount.mockReturnValue({ data: { count: 0 } } as any);
    mockUseNotifications.mockReturnValue({ data: [] } as any);
    vi.mocked(useMarkNotificationRead).mockReturnValue({ mutate: mockMarkRead } as any);
    vi.mocked(useMarkAllRead).mockReturnValue({ mutate: mockMarkAllRead } as any);
    vi.mocked(useSubmitNotificationFeedback).mockReturnValue({
      mutate: mockSubmitFeedback,
      isPending: false,
    } as any);
  });

  it('renders bell icon', () => {
    render(<NotificationBadge />);
    const button = screen.getByTitle('Notifications');
    expect(button).toBeInTheDocument();
  });

  it('shows unread count badge when count > 0', () => {
    mockUseUnreadCount.mockReturnValue({ data: { count: 3 } } as any);
    render(<NotificationBadge />);
    expect(screen.getByText('3')).toBeInTheDocument();
  });

  it('shows 9+ when count exceeds 9', () => {
    mockUseUnreadCount.mockReturnValue({ data: { count: 15 } } as any);
    render(<NotificationBadge />);
    expect(screen.getByText('9+')).toBeInTheDocument();
  });

  it('hides unread badge when count is 0', () => {
    mockUseUnreadCount.mockReturnValue({ data: { count: 0 } } as any);
    render(<NotificationBadge />);
    expect(screen.queryByText('0')).not.toBeInTheDocument();
    // The badge span should not exist at all
    expect(screen.getByTitle('Notifications').querySelector('span')).toBeNull();
  });

  it('opens dropdown on click', () => {
    render(<NotificationBadge />);
    fireEvent.click(screen.getByTitle('Notifications'));
    expect(screen.getByText('Notifications')).toBeInTheDocument();
  });

  it('closes dropdown on outside click', () => {
    render(<NotificationBadge />);
    fireEvent.click(screen.getByTitle('Notifications'));
    expect(screen.getByText('No notifications')).toBeInTheDocument();

    // Simulate outside click
    fireEvent.mouseDown(document);
    expect(screen.queryByText('No notifications')).not.toBeInTheDocument();
  });

  it('shows empty state when no notifications', () => {
    mockUseNotifications.mockReturnValue({ data: [] } as any);
    render(<NotificationBadge />);
    fireEvent.click(screen.getByTitle('Notifications'));
    expect(screen.getByText('No notifications')).toBeInTheDocument();
  });

  it('shows notification items', () => {
    mockUseNotifications.mockReturnValue({ data: sampleNotifications } as any);
    render(<NotificationBadge />);
    fireEvent.click(screen.getByTitle('Notifications'));
    expect(screen.getByText('Agent completed task')).toBeInTheDocument();
    expect(screen.getByText('Approval needed')).toBeInTheDocument();
  });

  it('calls markRead when clicking check button on unread notification', () => {
    mockUseNotifications.mockReturnValue({ data: sampleNotifications } as any);
    render(<NotificationBadge />);
    fireEvent.click(screen.getByTitle('Notifications'));

    const markReadButton = screen.getByTitle('Mark as read');
    fireEvent.click(markReadButton);
    expect(mockMarkRead).toHaveBeenCalledWith('n1');
  });

  it('shows mark all read button when there are unread notifications', () => {
    mockUseUnreadCount.mockReturnValue({ data: { count: 2 } } as any);
    mockUseNotifications.mockReturnValue({ data: sampleNotifications } as any);
    render(<NotificationBadge />);
    fireEvent.click(screen.getByTitle(/unread notifications/));
    expect(screen.getByText('Mark all read')).toBeInTheDocument();
  });

  it('calls markAllRead when clicking mark all read button', () => {
    mockUseUnreadCount.mockReturnValue({ data: { count: 2 } } as any);
    mockUseNotifications.mockReturnValue({ data: sampleNotifications } as any);
    render(<NotificationBadge />);
    fireEvent.click(screen.getByTitle(/unread notifications/));

    fireEvent.click(screen.getByText('Mark all read'));
    expect(mockMarkAllRead).toHaveBeenCalled();
  });

  it('updates button title based on unread count', () => {
    mockUseUnreadCount.mockReturnValue({ data: { count: 5 } } as any);
    render(<NotificationBadge />);
    expect(screen.getByTitle('5 unread notifications')).toBeInTheDocument();
  });

  it('renders feedback buttons for notifications without feedback', () => {
    mockUseNotifications.mockReturnValue({ data: sampleNotifications } as any);
    render(<NotificationBadge />);
    fireEvent.click(screen.getByTitle('Notifications'));

    const helpfulButtons = screen.getAllByTitle('Helpful');
    const notHelpfulButtons = screen.getAllByTitle('Not helpful');
    expect(helpfulButtons).toHaveLength(2);
    expect(notHelpfulButtons).toHaveLength(2);
  });

  it('dims non-selected button when feedback already submitted', () => {
    const notificationsWithFeedback = [
      {
        ...sampleNotifications[0],
        feedback: 'useful' as const,
        feedback_at: '2026-02-17T11:00:00Z',
      },
    ];
    mockUseNotifications.mockReturnValue({ data: notificationsWithFeedback } as any);
    render(<NotificationBadge />);
    fireEvent.click(screen.getByTitle('Notifications'));

    const thumbsDownButton = screen.getByTitle('Not helpful');
    expect(thumbsDownButton).toHaveClass('opacity-30');

    const thumbsUpButton = screen.getByTitle('Helpful');
    expect(thumbsUpButton).toHaveClass('text-brand-primary');
  });

  it('disables buttons while submitting feedback', () => {
    vi.mocked(useSubmitNotificationFeedback).mockReturnValue({
      mutate: mockSubmitFeedback,
      isPending: true,
    } as any);
    mockUseNotifications.mockReturnValue({ data: sampleNotifications } as any);
    render(<NotificationBadge />);
    fireEvent.click(screen.getByTitle('Notifications'));

    const helpfulButtons = screen.getAllByTitle('Helpful');
    const notHelpfulButtons = screen.getAllByTitle('Not helpful');
    helpfulButtons.forEach((btn) => expect(btn).toBeDisabled());
    notHelpfulButtons.forEach((btn) => expect(btn).toBeDisabled());
  });

  it('calls mutation with correct notification ID and feedback value', () => {
    mockUseNotifications.mockReturnValue({ data: sampleNotifications } as any);
    render(<NotificationBadge />);
    fireEvent.click(screen.getByTitle('Notifications'));

    const helpfulButtons = screen.getAllByTitle('Helpful');
    fireEvent.click(helpfulButtons[0]);
    expect(mockSubmitFeedback).toHaveBeenCalledWith({ notificationId: 'n1', feedback: 'useful' });
  });
});
