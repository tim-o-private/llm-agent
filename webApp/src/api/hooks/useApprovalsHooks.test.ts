/* eslint-disable no-undef */
import { vi, describe, it, expect, beforeEach } from 'vitest';
import { renderHook, waitFor, act } from '@testing-library/react';
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

vi.mock('@/components/ui/toast', () => ({
  toast: { error: vi.fn(), default: vi.fn(), success: vi.fn() },
}));

import {
  useApprovalsCount,
  useApproveCard,
  useRejectCard,
  useEditCard,
} from './useApprovalsHooks';
import type { ApprovalCard, TodayResponse } from '@/api/types/today';

function createWrapper() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  const Wrapper = ({ children }: { children: React.ReactNode }) =>
    React.createElement(QueryClientProvider, { client: queryClient }, children);
  return { Wrapper, queryClient };
}

function emailCard(id = 'card-1'): ApprovalCard {
  return {
    id,
    card_type: 'email_draft',
    title: 'Draft',
    status: 'pending',
    payload: { to: ['a@b.com'], subject: 'S', body: 'B' },
  };
}

function baseTodayPayload(approvals: ApprovalCard[]): TodayResponse {
  return {
    date: '2026-04-21',
    header: { framing: null },
    your_day: [],
    to_do: [],
    notes: [],
    agent: { running: [], watching: [], recent: [], blocked: [] },
    approvals,
    recent: [],
  };
}

function jsonResponse(body: unknown, status = 200) {
  return {
    ok: status >= 200 && status < 300,
    status,
    json: () => Promise.resolve(body),
    text: () => Promise.resolve(JSON.stringify(body)),
  };
}

describe('useApprovalsCount', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders count from /api/approvals/count', async () => {
    global.fetch = vi.fn().mockResolvedValue(jsonResponse({ count: 4 }));
    const { Wrapper } = createWrapper();
    const { result } = renderHook(() => useApprovalsCount(), { wrapper: Wrapper });

    await waitFor(() => expect(result.current.data).toBe(4));
    expect(global.fetch).toHaveBeenCalledWith(
      expect.stringContaining('/api/approvals/count'),
      expect.any(Object),
    );
  });

  it('falls back to 0 when count missing', async () => {
    global.fetch = vi.fn().mockResolvedValue(jsonResponse({}));
    const { Wrapper } = createWrapper();
    const { result } = renderHook(() => useApprovalsCount(), { wrapper: Wrapper });
    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(result.current.data).toBe(0);
  });
});

describe('useApproveCard', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('removes card from today cache and invalidates queries on success', async () => {
    global.fetch = vi.fn().mockResolvedValue(jsonResponse({ ok: true }));
    const { Wrapper, queryClient } = createWrapper();
    queryClient.setQueryData(['today'], baseTodayPayload([emailCard('c-1'), emailCard('c-2')]));
    queryClient.setQueryData(['approvals'], [emailCard('c-1'), emailCard('c-2')]);
    const invalidateSpy = vi.spyOn(queryClient, 'invalidateQueries');

    const { result } = renderHook(() => useApproveCard(), { wrapper: Wrapper });
    act(() => {
      result.current.mutate({ id: 'c-1' });
    });
    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    const cachedToday = queryClient.getQueryData<TodayResponse>(['today']);
    expect(cachedToday?.approvals.map((c) => c.id)).toEqual(['c-2']);
    const cachedList = queryClient.getQueryData<ApprovalCard[]>(['approvals']);
    expect(cachedList?.map((c) => c.id)).toEqual(['c-2']);

    const invalidatedKeys = invalidateSpy.mock.calls.map(
      (c) => (c[0] as { queryKey: unknown[] }).queryKey[0],
    );
    expect(invalidatedKeys).toEqual(
      expect.arrayContaining(['today', 'approvals']),
    );
  });

  it('surfaces error on 500 and leaves cache untouched', async () => {
    global.fetch = vi.fn().mockResolvedValue(jsonResponse({}, 500));
    const { Wrapper, queryClient } = createWrapper();
    const original = baseTodayPayload([emailCard('c-1')]);
    queryClient.setQueryData(['today'], original);

    const { result } = renderHook(() => useApproveCard(), { wrapper: Wrapper });
    act(() => {
      result.current.mutate({ id: 'c-1' });
    });
    await waitFor(() => expect(result.current.isError).toBe(true));

    const cached = queryClient.getQueryData<TodayResponse>(['today']);
    expect(cached?.approvals).toHaveLength(1);
  });

  it('forwards decision_note in POST body', async () => {
    const fetchMock = vi.fn().mockResolvedValue(jsonResponse({ ok: true }));
    global.fetch = fetchMock;
    const { Wrapper } = createWrapper();
    const { result } = renderHook(() => useApproveCard(), { wrapper: Wrapper });
    act(() => {
      result.current.mutate({ id: 'c-1', decision_note: 'looks good' });
    });
    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    const call = fetchMock.mock.calls[0];
    expect(JSON.parse(call[1].body)).toEqual({ decision_note: 'looks good' });
  });
});

describe('useRejectCard', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('removes card on success and forwards reason', async () => {
    const fetchMock = vi.fn().mockResolvedValue(jsonResponse({ ok: true }));
    global.fetch = fetchMock;
    const { Wrapper, queryClient } = createWrapper();
    queryClient.setQueryData(['today'], baseTodayPayload([emailCard('c-1')]));

    const { result } = renderHook(() => useRejectCard(), { wrapper: Wrapper });
    act(() => {
      result.current.mutate({ id: 'c-1', reason: 'Not now' });
    });
    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(JSON.parse(fetchMock.mock.calls[0][1].body)).toEqual({ reason: 'Not now' });
    const cached = queryClient.getQueryData<TodayResponse>(['today']);
    expect(cached?.approvals).toEqual([]);
  });

  it('surfaces error on 500', async () => {
    global.fetch = vi.fn().mockResolvedValue(jsonResponse({}, 500));
    const { Wrapper } = createWrapper();
    const { result } = renderHook(() => useRejectCard(), { wrapper: Wrapper });
    act(() => {
      result.current.mutate({ id: 'c-1' });
    });
    await waitFor(() => expect(result.current.isError).toBe(true));
  });
});

describe('useEditCard', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('patches cached payload and invalidates on success (card stays pending)', async () => {
    global.fetch = vi.fn().mockResolvedValue(jsonResponse({ ok: true }));
    const { Wrapper, queryClient } = createWrapper();
    queryClient.setQueryData(['today'], baseTodayPayload([emailCard('c-1')]));
    const invalidateSpy = vi.spyOn(queryClient, 'invalidateQueries');

    const { result } = renderHook(() => useEditCard(), { wrapper: Wrapper });
    act(() => {
      result.current.mutate({ id: 'c-1', payload_patch: { subject: 'Updated' } });
    });
    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    const cached = queryClient.getQueryData<TodayResponse>(['today']);
    const card = cached?.approvals.find((c) => c.id === 'c-1');
    expect(card?.status).toBe('pending');
    expect((card?.payload as { subject: string }).subject).toBe('Updated');

    const invalidatedKeys = invalidateSpy.mock.calls.map(
      (c) => (c[0] as { queryKey: unknown[] }).queryKey[0],
    );
    expect(invalidatedKeys).toEqual(expect.arrayContaining(['today', 'approvals']));
  });

  it('surfaces error on 401', async () => {
    global.fetch = vi.fn().mockResolvedValue(jsonResponse({}, 401));
    const { Wrapper } = createWrapper();
    const { result } = renderHook(() => useEditCard(), { wrapper: Wrapper });
    act(() => {
      result.current.mutate({ id: 'c-1', payload_patch: { subject: 'x' } });
    });
    await waitFor(() => expect(result.current.isError).toBe(true));
  });
});
