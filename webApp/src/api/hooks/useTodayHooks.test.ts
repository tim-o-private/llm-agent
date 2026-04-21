/* eslint-disable no-undef */
import { vi, describe, it, expect, beforeEach, afterEach } from 'vitest';
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
  useToday,
  useTodaySource,
  useAppendNote,
  useToggleTodo,
  useRegenerateToday,
  useRegenerationStatus,
} from './useTodayHooks';
import type { TodayResponse, WorkflowRun } from '@/api/types/today';

function createWrapper() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  const Wrapper = ({ children }: { children: React.ReactNode }) =>
    React.createElement(QueryClientProvider, { client: queryClient }, children);
  return { Wrapper, queryClient };
}

function baseTodayPayload(overrides: Partial<TodayResponse> = {}): TodayResponse {
  return {
    date: '2026-04-21',
    header: { framing: 'Light day.' },
    your_day: [],
    to_do: [
      { line_id: 'todo-1', text: 'Ship', checked: false },
      { line_id: 'todo-2', text: 'Review', checked: true },
    ],
    notes: [],
    agent: { running: [], watching: [], recent: [], blocked: [] },
    approvals: [],
    recent: [],
    ...overrides,
  };
}

function jsonResponse(body: unknown, status = 200) {
  return {
    ok: status >= 200 && status < 300,
    status,
    json: () => Promise.resolve(body),
    text: () => Promise.resolve(typeof body === 'string' ? body : JSON.stringify(body)),
  };
}

describe('useToday', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('fetches /api/today on mount (happy path)', async () => {
    const payload = baseTodayPayload();
    global.fetch = vi.fn().mockResolvedValue(jsonResponse(payload));

    const { Wrapper } = createWrapper();
    const { result } = renderHook(() => useToday(), { wrapper: Wrapper });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(result.current.data).toEqual(payload);
    expect(global.fetch).toHaveBeenCalledWith(
      expect.stringContaining('/api/today'),
      expect.objectContaining({
        headers: expect.objectContaining({ Authorization: 'Bearer test-token' }),
      }),
    );
  });

  it('surfaces error on 500', async () => {
    global.fetch = vi.fn().mockResolvedValue(jsonResponse({}, 500));
    const { Wrapper } = createWrapper();
    const { result } = renderHook(() => useToday(), { wrapper: Wrapper });
    await waitFor(() => expect(result.current.isError).toBe(true));
    expect(result.current.error?.message).toMatch(/500/);
  });
});

describe('useTodaySource', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('does not fetch when disabled', async () => {
    global.fetch = vi.fn();
    const { Wrapper } = createWrapper();
    renderHook(() => useTodaySource(false), { wrapper: Wrapper });
    await new Promise((r) => setTimeout(r, 10));
    expect(global.fetch).not.toHaveBeenCalled();
  });

  it('returns raw markdown when response is plain text', async () => {
    global.fetch = vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      text: () => Promise.resolve('# Today\n## Notes\n'),
    });
    const { Wrapper } = createWrapper();
    const { result } = renderHook(() => useTodaySource(true), { wrapper: Wrapper });
    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(result.current.data).toBe('# Today\n## Notes\n');
  });

  it('returns error on 401', async () => {
    global.fetch = vi.fn().mockResolvedValue({ ok: false, status: 401, text: () => Promise.resolve('') });
    const { Wrapper } = createWrapper();
    const { result } = renderHook(() => useTodaySource(true), { wrapper: Wrapper });
    await waitFor(() => expect(result.current.isError).toBe(true));
    expect(result.current.error?.message).toMatch(/401/);
  });
});

describe('useAppendNote', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('posts note and optimistically appends to cached today', async () => {
    const today = baseTodayPayload({ notes: [] });
    const saved = { created_at: '2026-04-21T09:14:00Z', text: 'hello' };
    global.fetch = vi.fn().mockResolvedValue(jsonResponse(saved));

    const { Wrapper, queryClient } = createWrapper();
    queryClient.setQueryData(['today'], today);

    const { result } = renderHook(() => useAppendNote(), { wrapper: Wrapper });
    act(() => {
      result.current.mutate('hello');
    });
    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    const cached = queryClient.getQueryData<TodayResponse>(['today']);
    expect(cached?.notes).toContainEqual(saved);
  });

  it('surfaces error on 500', async () => {
    global.fetch = vi.fn().mockResolvedValue(jsonResponse({}, 500));
    const { Wrapper } = createWrapper();
    const { result } = renderHook(() => useAppendNote(), { wrapper: Wrapper });
    act(() => {
      result.current.mutate('hi');
    });
    await waitFor(() => expect(result.current.isError).toBe(true));
  });
});

describe('useToggleTodo', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('optimistically updates todo checked state on mutate', async () => {
    global.fetch = vi.fn().mockResolvedValue(jsonResponse({ ok: true }));
    const { Wrapper, queryClient } = createWrapper();
    queryClient.setQueryData(['today'], baseTodayPayload());

    const { result } = renderHook(() => useToggleTodo(), { wrapper: Wrapper });
    act(() => {
      result.current.mutate({ line_id: 'todo-1', checked: true });
    });

    await waitFor(() => {
      const cached = queryClient.getQueryData<TodayResponse>(['today']);
      expect(cached?.to_do.find((t) => t.line_id === 'todo-1')?.checked).toBe(true);
    });
  });

  it('rolls back on error (401)', async () => {
    global.fetch = vi.fn().mockResolvedValue(jsonResponse({}, 401));
    const { Wrapper, queryClient } = createWrapper();
    const original = baseTodayPayload();
    queryClient.setQueryData(['today'], original);

    const { result } = renderHook(() => useToggleTodo(), { wrapper: Wrapper });
    act(() => {
      result.current.mutate({ line_id: 'todo-1', checked: true });
    });
    await waitFor(() => expect(result.current.isError).toBe(true));

    const cached = queryClient.getQueryData<TodayResponse>(['today']);
    expect(cached?.to_do.find((t) => t.line_id === 'todo-1')?.checked).toBe(false);
  });
});

describe('useRegenerateToday', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('accepts 202 as success and returns run_id', async () => {
    global.fetch = vi.fn().mockResolvedValue(jsonResponse({ run_id: 'run-1' }, 202));
    const { Wrapper } = createWrapper();
    const { result } = renderHook(() => useRegenerateToday(), { wrapper: Wrapper });

    act(() => {
      result.current.mutate();
    });
    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(result.current.data).toEqual({ run_id: 'run-1' });
  });

  it('surfaces error on 500', async () => {
    global.fetch = vi.fn().mockResolvedValue(jsonResponse({}, 500));
    const { Wrapper } = createWrapper();
    const { result } = renderHook(() => useRegenerateToday(), { wrapper: Wrapper });
    act(() => {
      result.current.mutate();
    });
    await waitFor(() => expect(result.current.isError).toBe(true));
  });
});

describe('useRegenerationStatus', () => {
  beforeEach(() => {
    vi.useFakeTimers();
    vi.clearAllMocks();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  function runsResponse(runs: WorkflowRun[]) {
    return jsonResponse({ runs });
  }

  it('polls /api/workflows/runs at 30s interval', async () => {
    const fetchMock = vi.fn().mockResolvedValue(runsResponse([]));
    global.fetch = fetchMock;

    const { Wrapper } = createWrapper();
    renderHook(() => useRegenerationStatus(), { wrapper: Wrapper });

    await vi.waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(1));
    expect(fetchMock).toHaveBeenCalledWith(
      expect.stringContaining('/api/workflows/runs?template_name=regenerate-today&limit=1'),
      expect.any(Object),
    );

    await act(async () => {
      await vi.advanceTimersByTimeAsync(30_000);
    });
    expect(fetchMock.mock.calls.length).toBeGreaterThanOrEqual(2);
  });

  it('invalidates today query when a newer completed run appears', async () => {
    const firstRun: WorkflowRun = {
      run_id: 'run-1',
      template_name: 'regenerate-today',
      status: 'completed',
      completed_at: '2026-04-21T09:00:00Z',
    };
    const secondRun: WorkflowRun = {
      ...firstRun,
      run_id: 'run-2',
      completed_at: '2026-04-21T09:30:00Z',
    };

    let call = 0;
    global.fetch = vi.fn().mockImplementation(() => {
      call += 1;
      return Promise.resolve(runsResponse(call === 1 ? [firstRun] : [secondRun]));
    });

    const { Wrapper, queryClient } = createWrapper();
    const invalidateSpy = vi.spyOn(queryClient, 'invalidateQueries');

    renderHook(() => useRegenerationStatus(), { wrapper: Wrapper });

    // First observation seeds the ref — must NOT invalidate.
    await vi.waitFor(() =>
      expect(
        (global.fetch as ReturnType<typeof vi.fn>).mock.calls.length,
      ).toBeGreaterThanOrEqual(1),
    );
    await act(async () => {
      await vi.advanceTimersByTimeAsync(0);
    });
    const todayInvalidationsAfterFirst = invalidateSpy.mock.calls.filter(
      (c) => Array.isArray((c[0] as { queryKey?: unknown[] })?.queryKey) &&
             ((c[0] as { queryKey: unknown[] }).queryKey[0] === 'today') &&
             ((c[0] as { queryKey: unknown[] }).queryKey.length === 1),
    ).length;
    expect(todayInvalidationsAfterFirst).toBe(0);

    // Second poll returns a newer completed run → invalidate once.
    await act(async () => {
      await vi.advanceTimersByTimeAsync(30_000);
    });
    await vi.waitFor(() => {
      const invalidations = invalidateSpy.mock.calls.filter(
        (c) =>
          Array.isArray((c[0] as { queryKey?: unknown[] })?.queryKey) &&
          ((c[0] as { queryKey: unknown[] }).queryKey[0] === 'today') &&
          ((c[0] as { queryKey: unknown[] }).queryKey.length === 1),
      );
      expect(invalidations.length).toBeGreaterThanOrEqual(1);
    });
  });

  it('does not re-invalidate on repeated observation of the same run', async () => {
    const run: WorkflowRun = {
      run_id: 'run-1',
      template_name: 'regenerate-today',
      status: 'completed',
      completed_at: '2026-04-21T09:00:00Z',
    };
    global.fetch = vi.fn().mockResolvedValue(runsResponse([run]));

    const { Wrapper, queryClient } = createWrapper();
    const invalidateSpy = vi.spyOn(queryClient, 'invalidateQueries');

    renderHook(() => useRegenerationStatus(), { wrapper: Wrapper });

    // Seed + two more polls, all same run.
    await vi.waitFor(() =>
      expect(
        (global.fetch as ReturnType<typeof vi.fn>).mock.calls.length,
      ).toBeGreaterThanOrEqual(1),
    );
    await act(async () => {
      await vi.advanceTimersByTimeAsync(30_000);
    });
    await act(async () => {
      await vi.advanceTimersByTimeAsync(30_000);
    });

    const todayInvalidations = invalidateSpy.mock.calls.filter(
      (c) =>
        Array.isArray((c[0] as { queryKey?: unknown[] })?.queryKey) &&
        ((c[0] as { queryKey: unknown[] }).queryKey[0] === 'today') &&
        ((c[0] as { queryKey: unknown[] }).queryKey.length === 1),
    ).length;
    expect(todayInvalidations).toBe(0);
  });

  it('stops polling after unmount', async () => {
    const fetchMock = vi.fn().mockResolvedValue(runsResponse([]));
    global.fetch = fetchMock;

    const { Wrapper } = createWrapper();
    const { unmount } = renderHook(() => useRegenerationStatus(), { wrapper: Wrapper });

    await vi.waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(1));
    unmount();

    const callsAtUnmount = fetchMock.mock.calls.length;
    await act(async () => {
      await vi.advanceTimersByTimeAsync(60_000);
    });
    expect(fetchMock.mock.calls.length).toBe(callsAtUnmount);
  });
});
