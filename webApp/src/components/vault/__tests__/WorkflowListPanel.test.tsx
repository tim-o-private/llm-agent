import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';

// Mock react-router-dom before imports
const mockNavigate = vi.fn();
vi.mock('react-router-dom', () => ({
  useNavigate: () => mockNavigate,
}));

// Mock the hooks
const mockUseWorkflowList = vi.fn();
const mockMutate = vi.fn();
vi.mock('@/api/hooks/useWorkflowEditorHooks', () => ({
  useWorkflowList: () => mockUseWorkflowList(),
  useCreateWorkflow: () => ({
    mutate: mockMutate,
    isPending: false,
  }),
}));

// Mock Spinner
vi.mock('@/components/ui/Spinner', () => ({
  Spinner: () => <div data-testid="spinner">Loading...</div>,
}));

import { WorkflowListPanel } from '../WorkflowListPanel';

const SAMPLE_WORKFLOWS = [
  {
    name: 'morning-briefing',
    filename: 'morning-briefing.flow.md',
    description: 'Compose the morning briefing.',
    trigger_summary: 'cron: 0 6 * * *',
    next_run_at: '2026-04-22T06:00:00Z',
  },
  {
    name: 'draft-reply',
    filename: 'draft-reply.flow.md',
    description: 'Draft a reply to an email.',
    trigger_summary: 'Manual',
    next_run_at: null,
  },
];

describe('WorkflowListPanel', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders workflow entries', () => {
    mockUseWorkflowList.mockReturnValue({
      data: SAMPLE_WORKFLOWS,
      isLoading: false,
      error: null,
    });

    render(
      <WorkflowListPanel currentPath="_workflows/morning-briefing.flow.md" />,
    );

    expect(screen.getByText('morning-briefing')).toBeDefined();
    expect(screen.getByText('draft-reply')).toBeDefined();
    expect(screen.getByText('Compose the morning briefing.')).toBeDefined();
  });

  it('shows empty state with "No workflows" message', () => {
    mockUseWorkflowList.mockReturnValue({
      data: [],
      isLoading: false,
      error: null,
    });

    render(<WorkflowListPanel currentPath="" />);

    expect(
      screen.getByText(/No workflows/i),
    ).toBeDefined();
  });

  it('"+ New workflow" button renders with correct data-testid', () => {
    mockUseWorkflowList.mockReturnValue({
      data: SAMPLE_WORKFLOWS,
      isLoading: false,
      error: null,
    });

    render(
      <WorkflowListPanel currentPath="_workflows/morning-briefing.flow.md" />,
    );

    const btn = screen.getByTestId('new-workflow-btn');
    expect(btn).toBeDefined();
    expect(btn.textContent).toContain('New workflow');
  });

  it('current workflow is highlighted with aria-current="page"', () => {
    mockUseWorkflowList.mockReturnValue({
      data: SAMPLE_WORKFLOWS,
      isLoading: false,
      error: null,
    });

    render(
      <WorkflowListPanel currentPath="_workflows/morning-briefing.flow.md" />,
    );

    const activeButton = screen.getByText('morning-briefing').closest('button');
    expect(activeButton?.getAttribute('aria-current')).toBe('page');

    const inactiveButton = screen.getByText('draft-reply').closest('button');
    expect(inactiveButton?.getAttribute('aria-current')).toBeNull();
  });

  it('clicking a workflow entry navigates via useNavigate', () => {
    mockUseWorkflowList.mockReturnValue({
      data: SAMPLE_WORKFLOWS,
      isLoading: false,
      error: null,
    });

    render(
      <WorkflowListPanel currentPath="_workflows/morning-briefing.flow.md" />,
    );

    const draftReplyBtn = screen.getByText('draft-reply').closest('button')!;
    fireEvent.click(draftReplyBtn);

    expect(mockNavigate).toHaveBeenCalledWith(
      '/vault/_workflows/draft-reply.flow.md',
    );
  });
});
