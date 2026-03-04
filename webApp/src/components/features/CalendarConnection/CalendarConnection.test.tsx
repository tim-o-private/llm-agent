import { vi, describe, it, expect, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';

vi.mock('@/api/hooks/useExternalConnectionsHooks', () => ({
  useConnectionStatus: vi.fn(),
  useCalendarConnections: vi.fn(),
  useDisconnectCalendarConnection: vi.fn(),
}));

vi.mock('@/lib/supabaseClient', () => ({
  supabase: {
    auth: {
      getSession: vi.fn().mockResolvedValue({ data: { session: { access_token: 'test' } } }),
    },
  },
}));

import {
  useConnectionStatus,
  useCalendarConnections,
  useDisconnectCalendarConnection,
} from '@/api/hooks/useExternalConnectionsHooks';
import { CalendarConnection } from './CalendarConnection';

const mockDisconnectMutateAsync = vi.fn();

beforeEach(() => {
  vi.clearAllMocks();
  vi.mocked(useConnectionStatus).mockReturnValue({
    data: { connected: false, count: 0, service: 'google_calendar' },
    isLoading: false,
    error: null,
    refetch: vi.fn(),
  } as unknown as ReturnType<typeof useConnectionStatus>);
  vi.mocked(useCalendarConnections).mockReturnValue({
    data: [],
    isLoading: false,
    refetch: vi.fn(),
  } as unknown as ReturnType<typeof useCalendarConnections>);
  vi.mocked(useDisconnectCalendarConnection).mockReturnValue({
    mutateAsync: mockDisconnectMutateAsync,
    isPending: false,
    error: null,
  } as unknown as ReturnType<typeof useDisconnectCalendarConnection>);
});

describe('CalendarConnection', () => {
  it('shows connect button when no accounts connected', () => {
    render(<CalendarConnection />);
    expect(screen.getByRole('button', { name: /Connect Google Calendar/i })).toBeInTheDocument();
  });

  it('shows Not Connected badge when no accounts', () => {
    render(<CalendarConnection />);
    expect(screen.getByText('Not Connected')).toBeInTheDocument();
  });

  it('shows connected accounts list', () => {
    vi.mocked(useConnectionStatus).mockReturnValue({
      data: { connected: true, count: 2, service: 'google_calendar' },
      isLoading: false,
      error: null,
      refetch: vi.fn(),
    } as unknown as ReturnType<typeof useConnectionStatus>);
    vi.mocked(useCalendarConnections).mockReturnValue({
      data: [
        { id: 'conn1', service_name: 'google_calendar', service_user_email: 'work@test.com', is_active: true, created_at: '2026-03-01T00:00:00Z' },
        { id: 'conn2', service_name: 'google_calendar', service_user_email: 'personal@test.com', is_active: true, created_at: '2026-03-02T00:00:00Z' },
      ],
      isLoading: false,
      refetch: vi.fn(),
    } as unknown as ReturnType<typeof useCalendarConnections>);

    render(<CalendarConnection />);
    expect(screen.getByText('work@test.com')).toBeInTheDocument();
    expect(screen.getByText('personal@test.com')).toBeInTheDocument();
    expect(screen.getByText(/2 of 5 connected/i)).toBeInTheDocument();
  });

  it('shows Add Calendar Account button when accounts exist and under limit', () => {
    vi.mocked(useConnectionStatus).mockReturnValue({
      data: { connected: true, count: 1, service: 'google_calendar' },
      isLoading: false,
      error: null,
      refetch: vi.fn(),
    } as unknown as ReturnType<typeof useConnectionStatus>);
    vi.mocked(useCalendarConnections).mockReturnValue({
      data: [
        { id: 'conn1', service_name: 'google_calendar', service_user_email: 'work@test.com', is_active: true, created_at: '2026-03-01T00:00:00Z' },
      ],
      isLoading: false,
      refetch: vi.fn(),
    } as unknown as ReturnType<typeof useCalendarConnections>);

    render(<CalendarConnection />);
    expect(screen.getByRole('button', { name: /Add Calendar Account/i })).toBeInTheDocument();
  });

  it('hides Add button when at max accounts', () => {
    vi.mocked(useConnectionStatus).mockReturnValue({
      data: { connected: true, count: 5, service: 'google_calendar' },
      isLoading: false,
      error: null,
      refetch: vi.fn(),
    } as unknown as ReturnType<typeof useConnectionStatus>);
    vi.mocked(useCalendarConnections).mockReturnValue({
      data: Array.from({ length: 5 }, (_, i) => ({
        id: `conn${i}`, service_name: 'google_calendar', service_user_email: `user${i}@test.com`, is_active: true, created_at: '2026-03-01T00:00:00Z',
      })),
      isLoading: false,
      refetch: vi.fn(),
    } as unknown as ReturnType<typeof useCalendarConnections>);

    render(<CalendarConnection />);
    expect(screen.queryByRole('button', { name: /Add Calendar Account/i })).not.toBeInTheDocument();
  });

  it('shows per-account disconnect buttons', () => {
    vi.mocked(useConnectionStatus).mockReturnValue({
      data: { connected: true, count: 1, service: 'google_calendar' },
      isLoading: false,
      error: null,
      refetch: vi.fn(),
    } as unknown as ReturnType<typeof useConnectionStatus>);
    vi.mocked(useCalendarConnections).mockReturnValue({
      data: [
        { id: 'conn1', service_name: 'google_calendar', service_user_email: 'work@test.com', is_active: true, created_at: '2026-03-01T00:00:00Z' },
      ],
      isLoading: false,
      refetch: vi.fn(),
    } as unknown as ReturnType<typeof useCalendarConnections>);

    render(<CalendarConnection />);
    // The Trash2 icon button exists for disconnect
    const buttons = screen.getAllByRole('button');
    // Should have at least the disconnect button and Add/Refresh buttons
    expect(buttons.length).toBeGreaterThanOrEqual(2);
  });
});
