import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { AskChip } from './AskChip';
import { useChatStore } from '@/stores/useChatStore';

// Mock the store — we just need to verify calls
vi.mock('@/stores/useChatStore', () => {
  const setScope = vi.fn();
  const setChatPanelOpen = vi.fn();
  const setPendingPrompt = vi.fn();

  const store = {
    getState: () => ({
      setScope,
      setChatPanelOpen,
      setPendingPrompt,
    }),
  };

  return {
    useChatStore: Object.assign(() => ({}), store),
  };
});

describe('AskChip', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders with default label', () => {
    render(<AskChip scope={{ type: 'today' }} />);
    const button = screen.getByRole('button', { name: 'Ask about this' });
    expect(button).toBeDefined();
    expect(button.textContent).toContain('Ask about this');
  });

  it('renders with custom label', () => {
    render(<AskChip scope={{ type: 'today' }} label="Ask about approvals" />);
    const button = screen.getByRole('button', { name: 'Ask about approvals' });
    expect(button).toBeDefined();
  });

  it('clicking sets scope, opens panel', () => {
    render(<AskChip scope={{ type: 'today' }} />);
    fireEvent.click(screen.getByRole('button'));

    const state = useChatStore.getState();
    expect(state.setScope).toHaveBeenCalledWith({ type: 'today' });
    expect(state.setChatPanelOpen).toHaveBeenCalledWith(true);
  });

  it('clicking with prompt sets pending prompt', () => {
    render(
      <AskChip
        scope={{ type: 'file', path: 'notes/test.md' }}
        prompt="Summarize this file"
      />,
    );
    fireEvent.click(screen.getByRole('button'));

    const state = useChatStore.getState();
    expect(state.setScope).toHaveBeenCalledWith({ type: 'file', path: 'notes/test.md' });
    expect(state.setChatPanelOpen).toHaveBeenCalledWith(true);
    expect(state.setPendingPrompt).toHaveBeenCalledWith('Summarize this file');
  });

  it('clicking without prompt does not set pending prompt', () => {
    render(<AskChip scope={{ type: 'today' }} />);
    fireEvent.click(screen.getByRole('button'));

    const state = useChatStore.getState();
    expect(state.setPendingPrompt).not.toHaveBeenCalled();
  });
});
