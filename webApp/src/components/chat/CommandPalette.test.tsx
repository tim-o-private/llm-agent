import { describe, it, expect, vi, beforeEach, beforeAll } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { CommandPalette } from './CommandPalette';

// cmdk uses ResizeObserver internally
beforeAll(() => {
  if (typeof globalThis.ResizeObserver === 'undefined') {
    globalThis.ResizeObserver = class ResizeObserver {
      observe() {}
      unobserve() {}
      disconnect() {}
    };
  }
});

// Mock useChatScope
vi.mock('@/hooks/useChatScope', () => ({
  useChatScope: () => ({ type: 'today' as const }),
}));

// Mock useChatStore
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

function renderPalette() {
  return render(
    <MemoryRouter>
      <CommandPalette />
    </MemoryRouter>,
  );
}

describe('CommandPalette', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('does not render when closed', () => {
    renderPalette();
    expect(screen.queryByRole('dialog')).toBeNull();
  });

  it('opens on Cmd+K', () => {
    renderPalette();
    fireEvent.keyDown(document, { key: 'k', metaKey: true });
    expect(screen.getByRole('dialog', { name: 'Command palette' })).toBeDefined();
  });

  it('opens on Ctrl+K', () => {
    renderPalette();
    fireEvent.keyDown(document, { key: 'k', ctrlKey: true });
    expect(screen.getByRole('dialog', { name: 'Command palette' })).toBeDefined();
  });

  it('closes on Escape', () => {
    renderPalette();
    // Open
    fireEvent.keyDown(document, { key: 'k', metaKey: true });
    expect(screen.getByRole('dialog')).toBeDefined();
    // Close
    fireEvent.keyDown(document, { key: 'Escape' });
    expect(screen.queryByRole('dialog')).toBeNull();
  });

  it('renders the input with correct placeholder', () => {
    renderPalette();
    fireEvent.keyDown(document, { key: 'k', metaKey: true });
    const input = screen.getByPlaceholderText('Ask Clarity anything...');
    expect(input).toBeDefined();
  });

  it('renders the "Chat about" action', () => {
    renderPalette();
    fireEvent.keyDown(document, { key: 'k', metaKey: true });
    expect(screen.getByText('Chat about Today')).toBeDefined();
  });
});
