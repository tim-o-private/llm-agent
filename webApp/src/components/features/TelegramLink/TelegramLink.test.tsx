import { vi, describe, it, expect, beforeEach } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';

vi.mock('@/api/hooks/useTelegramHooks', () => ({
  useTelegramStatus: vi.fn(),
  useGenerateLinkToken: vi.fn(),
  useUnlinkTelegram: vi.fn(),
}));

import { useTelegramStatus, useGenerateLinkToken, useUnlinkTelegram } from '@/api/hooks/useTelegramHooks';
import { TelegramLink } from './TelegramLink';

const mockMutate = vi.fn();
const mockUnlinkMutate = vi.fn();

beforeEach(() => {
  vi.clearAllMocks();
  vi.mocked(useTelegramStatus).mockReturnValue({
    data: { linked: false, linked_at: null },
    isLoading: false,
  } as any);
  vi.mocked(useGenerateLinkToken).mockReturnValue({
    data: undefined,
    mutate: mockMutate,
    isPending: false,
    error: null,
  } as any);
  vi.mocked(useUnlinkTelegram).mockReturnValue({
    mutate: mockUnlinkMutate,
    isPending: false,
  } as any);
});

describe('TelegramLink', () => {
  it('shows connect button when not linked', () => {
    render(<TelegramLink />);
    expect(screen.getByRole('button', { name: 'Connect Telegram' })).toBeInTheDocument();
  });

  it('shows connected badge when linked', () => {
    vi.mocked(useTelegramStatus).mockReturnValue({
      data: { linked: true, linked_at: '2026-02-17T00:00:00Z' },
      isLoading: false,
    } as any);

    render(<TelegramLink />);
    expect(screen.getByText('Connected')).toBeInTheDocument();
  });

  it('shows loading state', () => {
    vi.mocked(useTelegramStatus).mockReturnValue({
      data: undefined,
      isLoading: true,
    } as any);

    render(<TelegramLink />);
    expect(screen.getByText('Checking status...')).toBeInTheDocument();
  });

  it('shows token after generating', () => {
    vi.mocked(useGenerateLinkToken).mockReturnValue({
      data: { token: 'test-token', bot_username: 'test_bot' },
      mutate: mockMutate,
      isPending: false,
      error: null,
    } as any);

    render(<TelegramLink />);
    expect(screen.getByText(/\/start test-token/)).toBeInTheDocument();
    expect(screen.getByText('@test_bot')).toBeInTheDocument();
  });

  it('calls mutate when connect button clicked', () => {
    render(<TelegramLink />);
    fireEvent.click(screen.getByRole('button', { name: 'Connect Telegram' }));
    expect(mockMutate).toHaveBeenCalledOnce();
  });

  it('shows disconnect button when linked', () => {
    vi.mocked(useTelegramStatus).mockReturnValue({
      data: { linked: true, linked_at: '2026-02-17T00:00:00Z' },
      isLoading: false,
    } as any);

    render(<TelegramLink />);
    expect(screen.getByRole('button', { name: 'Disconnect' })).toBeInTheDocument();
  });

  it('shows unlink confirmation dialog', () => {
    vi.mocked(useTelegramStatus).mockReturnValue({
      data: { linked: true, linked_at: '2026-02-17T00:00:00Z' },
      isLoading: false,
    } as any);

    render(<TelegramLink />);
    fireEvent.click(screen.getByRole('button', { name: 'Disconnect' }));
    expect(screen.getByRole('button', { name: 'Yes, disconnect' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Cancel' })).toBeInTheDocument();
  });

  it('hides confirmation on cancel', () => {
    vi.mocked(useTelegramStatus).mockReturnValue({
      data: { linked: true, linked_at: '2026-02-17T00:00:00Z' },
      isLoading: false,
    } as any);

    render(<TelegramLink />);
    fireEvent.click(screen.getByRole('button', { name: 'Disconnect' }));
    expect(screen.getByRole('button', { name: 'Yes, disconnect' })).toBeInTheDocument();

    fireEvent.click(screen.getByRole('button', { name: 'Cancel' }));
    expect(screen.queryByRole('button', { name: 'Yes, disconnect' })).not.toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Disconnect' })).toBeInTheDocument();
  });

  it('shows generating state on button', () => {
    vi.mocked(useGenerateLinkToken).mockReturnValue({
      data: undefined,
      mutate: mockMutate,
      isPending: true,
      error: null,
    } as any);

    render(<TelegramLink />);
    expect(screen.getByRole('button', { name: 'Generating...' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Generating...' })).toBeDisabled();
  });

  it('shows error message when token generation fails', () => {
    vi.mocked(useGenerateLinkToken).mockReturnValue({
      data: undefined,
      mutate: mockMutate,
      isPending: false,
      error: new Error('Network error'),
    } as any);

    render(<TelegramLink />);
    expect(screen.getByText('Network error')).toBeInTheDocument();
  });

  it('shows linked date when available', () => {
    vi.mocked(useTelegramStatus).mockReturnValue({
      data: { linked: true, linked_at: '2026-02-17T12:00:00Z' },
      isLoading: false,
    } as any);

    render(<TelegramLink />);
    const dateElements = screen.getAllByText(/Connected/);
    // One is the badge, the other is the "Connected <date>" paragraph
    const dateElement = dateElements.find((el) => /\d+\/\d+\/\d+/.test(el.textContent ?? ''));
    expect(dateElement).toBeDefined();
  });
});
