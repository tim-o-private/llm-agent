import { vi, describe, it, expect, beforeEach } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';

vi.mock('@/api/hooks/useActionsHooks', () => ({
  useApproveAction: vi.fn(),
  useRejectAction: vi.fn(),
}));

vi.mock('@/api/hooks/useNotificationHooks', () => ({
  useMarkNotificationRead: vi.fn(),
}));

import { useApproveAction, useRejectAction } from '@/api/hooks/useActionsHooks';
import { useMarkNotificationRead } from '@/api/hooks/useNotificationHooks';
import { ApprovalInlineMessage } from './ApprovalInlineMessage';
import type { ChatMessage } from '@/stores/useChatStore';

const mockApproveMutate = vi.fn();
const mockRejectMutate = vi.fn();
const mockMarkReadMutate = vi.fn();

beforeEach(() => {
  vi.mocked(useApproveAction).mockReturnValue({
    mutate: mockApproveMutate,
    isPending: false,
  } as ReturnType<typeof useApproveAction>);

  vi.mocked(useRejectAction).mockReturnValue({
    mutate: mockRejectMutate,
    isPending: false,
  } as ReturnType<typeof useRejectAction>);

  vi.mocked(useMarkNotificationRead).mockReturnValue({
    mutate: mockMarkReadMutate,
    isPending: false,
  } as ReturnType<typeof useMarkNotificationRead>);
});

const baseMessage: ChatMessage = {
  id: 'notif-approval-1',
  text: 'Approval required for send_email',
  sender: 'approval',
  timestamp: new Date('2026-02-17T10:00:00Z'),
  notification_id: 'notif-1',
  action_id: 'action-xyz',
  action_tool_name: 'send_email',
  action_tool_args: { to: 'test@example.com', subject: 'Hello', body: 'Test message', extra: 'extra' },
  action_status: 'pending',
};

describe('ApprovalInlineMessage', () => {
  it('renders tool name', () => {
    render(<ApprovalInlineMessage message={baseMessage} />);
    expect(screen.getByText('send_email')).toBeTruthy();
  });

  it('renders truncated args (max 3 by default)', () => {
    render(<ApprovalInlineMessage message={baseMessage} />);
    expect(screen.getByText(/to:/)).toBeTruthy();
    expect(screen.getByText(/subject:/)).toBeTruthy();
  });

  it('shows expand button when args exceed 3', () => {
    render(<ApprovalInlineMessage message={baseMessage} />);
    expect(screen.getByText(/Show 1 more/)).toBeTruthy();
  });

  it('expands args on click', () => {
    render(<ApprovalInlineMessage message={baseMessage} />);
    fireEvent.click(screen.getByText(/Show 1 more/));
    expect(screen.getByText(/extra:/)).toBeTruthy();
    expect(screen.getByText('Show less')).toBeTruthy();
  });

  it('renders approve and reject buttons when status is pending', () => {
    render(<ApprovalInlineMessage message={baseMessage} />);
    expect(screen.getByRole('button', { name: /approve action/i })).toBeTruthy();
    expect(screen.getByRole('button', { name: /reject action/i })).toBeTruthy();
  });

  it('calls approve mutation when approve button clicked', () => {
    render(<ApprovalInlineMessage message={baseMessage} />);
    fireEvent.click(screen.getByRole('button', { name: /approve action/i }));
    expect(mockApproveMutate).toHaveBeenCalledWith('action-xyz');
  });

  it('calls reject mutation when reject button clicked', () => {
    render(<ApprovalInlineMessage message={baseMessage} />);
    fireEvent.click(screen.getByRole('button', { name: /reject action/i }));
    expect(mockRejectMutate).toHaveBeenCalledWith({ actionId: 'action-xyz' });
  });

  it('shows resolved state when status is approved', () => {
    const msg = { ...baseMessage, action_status: 'approved' };
    render(<ApprovalInlineMessage message={msg} />);
    expect(screen.getByText(/Approved/)).toBeTruthy();
    expect(screen.queryByRole('button', { name: /approve action/i })).toBeNull();
  });

  it('shows resolved state when status is rejected', () => {
    const msg = { ...baseMessage, action_status: 'rejected' };
    render(<ApprovalInlineMessage message={msg} />);
    expect(screen.getByText('Rejected')).toBeTruthy();
    expect(screen.queryByRole('button', { name: /approve action/i })).toBeNull();
  });

  it('disables buttons during pending mutation', () => {
    vi.mocked(useApproveAction).mockReturnValue({
      mutate: mockApproveMutate,
      isPending: true,
    } as ReturnType<typeof useApproveAction>);

    render(<ApprovalInlineMessage message={baseMessage} />);
    const approveBtn = screen.getByRole('button', { name: /approve action/i }) as HTMLButtonElement;
    const rejectBtn = screen.getByRole('button', { name: /reject action/i }) as HTMLButtonElement;
    expect(approveBtn.disabled).toBe(true);
    expect(rejectBtn.disabled).toBe(true);
  });

  it('calls mark-read on mount', () => {
    render(<ApprovalInlineMessage message={baseMessage} />);
    expect(mockMarkReadMutate).toHaveBeenCalledWith('notif-1');
  });
});
