/* eslint-disable no-undef */
import { vi, describe, it, expect, beforeEach } from 'vitest';
import { renderHook, waitFor } from '@testing-library/react';
import { act } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import React from 'react';

vi.mock('@/lib/supabaseClient', () => ({
  supabase: {
    auth: {
      getSession: vi.fn().mockResolvedValue({
        data: { session: { access_token: 'test-token' } },
      }),
    },
  },
}));

vi.mock('./useChatApiHooks', () => ({
  sendMessageApi: vi.fn().mockResolvedValue('ok'),
  useSendMessageMutation: vi.fn(),
}));

vi.mock('@/components/ui/toast', () => ({
  toast: { error: vi.fn(), success: vi.fn() },
}));

import { sendMessageApi } from './useChatApiHooks';
import { useApproveAction, useRejectAction } from './useActionsHooks';

const mockSendMessageApi = vi.mocked(sendMessageApi);

function createWrapper() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  const Wrapper = ({ children }: { children: React.ReactNode }) =>
    React.createElement(QueryClientProvider, { client: queryClient }, children);
  return Wrapper;
}

describe('useApproveAction', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockSendMessageApi.mockResolvedValue('ok');
    global.fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: () =>
        Promise.resolve({
          success: true,
          message: 'ok',
          result: { execution_result: 'Task done.' },
        }),
    });
  });

  it('sends follow-up chat message after approve (AC-30)', async () => {
    const { result } = renderHook(() => useApproveAction(), { wrapper: createWrapper() });

    act(() => {
      result.current.mutate({ actionId: 'act-1', sessionId: 'session-abc', toolName: 'delete_tasks' });
    });

    await waitFor(() => {
      expect(mockSendMessageApi).toHaveBeenCalledWith({
        message: '[Action approved: delete_tasks. Result: Task done.]',
        userId: null,
        activeChatId: 'session-abc',
      });
    });
  });

  it('uses Executed successfully. when execution_result is absent', async () => {
    global.fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: () => Promise.resolve({ success: true, message: 'ok', result: {} }),
    });

    const { result } = renderHook(() => useApproveAction(), { wrapper: createWrapper() });

    act(() => {
      result.current.mutate({ actionId: 'act-1', sessionId: 'session-abc', toolName: 'delete_tasks' });
    });

    await waitFor(() => {
      expect(mockSendMessageApi).toHaveBeenCalledWith(
        expect.objectContaining({
          message: '[Action approved: delete_tasks. Result: Executed successfully.]',
        }),
      );
    });
  });

  it('mutation variable includes sessionId and toolName (AC-32)', async () => {
    const { result } = renderHook(() => useApproveAction(), { wrapper: createWrapper() });

    act(() => {
      result.current.mutate({ actionId: 'act-1', sessionId: 'sess-xyz', toolName: 'send_email' });
    });

    await waitFor(() => {
      expect(mockSendMessageApi).toHaveBeenCalledWith(
        expect.objectContaining({ activeChatId: 'sess-xyz' }),
      );
    });
  });
});

describe('useRejectAction', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockSendMessageApi.mockResolvedValue('ok');
    global.fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: () => Promise.resolve({ success: false, message: 'rejected' }),
    });
  });

  it('sends follow-up chat message after reject (AC-31)', async () => {
    const { result } = renderHook(() => useRejectAction(), { wrapper: createWrapper() });

    act(() => {
      result.current.mutate({ actionId: 'act-2', sessionId: 'session-abc', toolName: 'send_email' });
    });

    await waitFor(() => {
      expect(mockSendMessageApi).toHaveBeenCalledWith({
        message: '[Action rejected: send_email. Reason: User declined.]',
        userId: null,
        activeChatId: 'session-abc',
      });
    });
  });

  it('includes custom reason in follow-up message', async () => {
    const { result } = renderHook(() => useRejectAction(), { wrapper: createWrapper() });

    act(() => {
      result.current.mutate({
        actionId: 'act-2',
        sessionId: 'session-abc',
        toolName: 'send_email',
        reason: 'Not now',
      });
    });

    await waitFor(() => {
      expect(mockSendMessageApi).toHaveBeenCalledWith({
        message: '[Action rejected: send_email. Reason: Not now]',
        userId: null,
        activeChatId: 'session-abc',
      });
    });
  });

  it('reject mutation variable includes sessionId and toolName (AC-32)', async () => {
    const { result } = renderHook(() => useRejectAction(), { wrapper: createWrapper() });

    act(() => {
      result.current.mutate({ actionId: 'act-2', sessionId: 'my-session', toolName: 'delete_file' });
    });

    await waitFor(() => {
      expect(mockSendMessageApi).toHaveBeenCalledWith(
        expect.objectContaining({ activeChatId: 'my-session' }),
      );
    });
  });
});
