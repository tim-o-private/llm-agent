import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { ScopeIndicator } from './ScopeIndicator';

describe('ScopeIndicator', () => {
  it('renders nothing for global scope', () => {
    const { container } = render(<ScopeIndicator scope={{ type: 'global' }} />);
    expect(container.innerHTML).toBe('');
  });

  it('renders "Today" for today scope', () => {
    render(<ScopeIndicator scope={{ type: 'today' }} />);
    const el = screen.getByText('Today');
    expect(el).toBeDefined();
    expect(el.getAttribute('aria-label')).toBe('Chat scope: Today');
  });

  it('renders folder name for folder scope', () => {
    render(<ScopeIndicator scope={{ type: 'folder', path: 'projects/web/' }} />);
    const el = screen.getByText('Folder: web');
    expect(el).toBeDefined();
    expect(el.getAttribute('aria-label')).toBe('Chat scope: Folder: web');
  });

  it('renders file name for file scope', () => {
    render(<ScopeIndicator scope={{ type: 'file', path: 'notes/standup.md' }} />);
    const el = screen.getByText('File: standup.md');
    expect(el).toBeDefined();
    expect(el.getAttribute('aria-label')).toBe('Chat scope: File: standup.md');
  });

  it('renders workflow name for workflow scope', () => {
    render(
      <ScopeIndicator scope={{ type: 'workflow', path: '_workflows/digest.flow.md' }} />,
    );
    const el = screen.getByText('Workflow: digest');
    expect(el).toBeDefined();
    expect(el.getAttribute('aria-label')).toBe('Chat scope: Workflow: digest');
  });

  it('handles nested folder paths', () => {
    render(<ScopeIndicator scope={{ type: 'folder', path: 'a/b/c/' }} />);
    expect(screen.getByText('Folder: c')).toBeDefined();
  });
});
