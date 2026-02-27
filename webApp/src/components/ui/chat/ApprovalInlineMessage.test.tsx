import { vi, describe, it, expect, beforeEach } from 'vitest';
import { render, screen, fireEvent, act } from '@testing-library/react';

vi.mock('@/api/hooks/useActionsHooks', () => ({
  useApproveAction: vi.fn(),
  useRejectAction: vi.fn(),
}));

vi.mock('@/api/hooks/useNotificationHooks', () => ({
  useMarkNotificationRead: vi.fn(),
}));

vi.mock('@/stores/useChatStore', () => ({
  useChatStore: vi.fn(),
}));

import { useApproveAction, useRejectAction } from '@/api/hooks/useActionsHooks';
import { useMarkNotificationRead } from '@/api/hooks/useNotificationHooks';
import { useChatStore } from '@/stores/useChatStore';
import { ApprovalInlineMessage } from './ApprovalInlineMessage';
import type { ChatMessage } from '@/stores/useChatStore';
import type { ActionResult } from '@/api/hooks/useActionsHooks';

const mockApproveMutate = vi.fn();
const mockRejectMutate = vi.fn();
const mockMarkReadMutate = vi.fn();

beforeEach(() => {
  vi.clearAllMocks();

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

  // Return activeChatId for the selector-based call
  vi.mocked(useChatStore).mockReturnValue('test-session-id' as unknown as ReturnType<typeof useChatStore>);
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

  it('calls approve mutation with session context when approve button clicked', () => {
    render(<ApprovalInlineMessage message={baseMessage} />);
    fireEvent.click(screen.getByRole('button', { name: /approve action/i }));
    expect(mockApproveMutate).toHaveBeenCalledWith(
      { actionId: 'action-xyz', sessionId: 'test-session-id', toolName: 'send_email' },
      expect.any(Object),
    );
  });

  it('calls reject mutation with session context when reject button clicked', () => {
    render(<ApprovalInlineMessage message={baseMessage} />);
    fireEvent.click(screen.getByRole('button', { name: /reject action/i }));
    expect(mockRejectMutate).toHaveBeenCalledWith({
      actionId: 'action-xyz',
      reason: undefined,
      sessionId: 'test-session-id',
      toolName: 'send_email',
    });
  });

  it('shows resolved heading when status is approved', () => {
    const msg = { ...baseMessage, action_status: 'approved' };
    render(<ApprovalInlineMessage message={msg} />);
    expect(screen.getByText(/Approved/)).toBeTruthy();
    expect(screen.queryByRole('button', { name: /approve action/i })).toBeNull();
  });

  it('shows resolved heading when status is rejected', () => {
    const msg = { ...baseMessage, action_status: 'rejected' };
    render(<ApprovalInlineMessage message={msg} />);
    expect(screen.getByText(/Rejected/)).toBeTruthy();
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

  // AC-29: Execution result display
  it('shows execution result after approve resolves (AC-29)', () => {
    vi.mocked(useApproveAction).mockReturnValue({
      mutate: vi.fn((_, callbacks) => {
        const cb = callbacks as { onSuccess?: (r: ActionResult) => void };
        cb?.onSuccess?.({ success: true, message: 'ok', result: { execution_result: 'Task deleted.' } });
      }),
      isPending: false,
    } as ReturnType<typeof useApproveAction>);

    render(<ApprovalInlineMessage message={baseMessage} />);
    act(() => {
      fireEvent.click(screen.getByRole('button', { name: /approve action/i }));
    });
    expect(screen.getByText('Task deleted.')).toBeTruthy();
  });

  it('shows Executed successfully. when approve result has no execution_result (AC-29)', () => {
    vi.mocked(useApproveAction).mockReturnValue({
      mutate: vi.fn((_, callbacks) => {
        const cb = callbacks as { onSuccess?: (r: ActionResult) => void };
        cb?.onSuccess?.({ success: true, message: 'ok' });
      }),
      isPending: false,
    } as ReturnType<typeof useApproveAction>);

    render(<ApprovalInlineMessage message={baseMessage} />);
    act(() => {
      fireEvent.click(screen.getByRole('button', { name: /approve action/i }));
    });
    expect(screen.getByText('Executed successfully.')).toBeTruthy();
  });

  it('shows Running... while approve mutation is pending (AC-29)', () => {
    vi.mocked(useApproveAction).mockReturnValue({
      mutate: vi.fn(),
      isPending: true,
    } as ReturnType<typeof useApproveAction>);

    const msg = { ...baseMessage, action_status: 'approved' };
    render(<ApprovalInlineMessage message={msg} />);
    expect(screen.getByText('Running...')).toBeTruthy();
  });

  // Per-state border colors
  it('shows success border when approved', () => {
    const msg = { ...baseMessage, action_status: 'approved' };
    render(<ApprovalInlineMessage message={msg} />);
    const alertDiv = screen.getByRole('alert');
    expect(alertDiv.className).toContain('border-l-success-indicator');
  });

  it('shows neutral border when rejected', () => {
    const msg = { ...baseMessage, action_status: 'rejected' };
    render(<ApprovalInlineMessage message={msg} />);
    const alertDiv = screen.getByRole('alert');
    expect(alertDiv.className).toContain('border-l-ui-border');
  });

  it('shows warning border when pending', () => {
    render(<ApprovalInlineMessage message={baseMessage} />);
    const alertDiv = screen.getByRole('alert');
    expect(alertDiv.className).toContain('border-l-warning-strong');
  });

  // Args toggle when resolved
  it('shows args toggle when resolved', () => {
    const msg = { ...baseMessage, action_status: 'approved' };
    render(<ApprovalInlineMessage message={msg} />);
    expect(screen.getByText('Show arguments')).toBeTruthy();
  });
});
