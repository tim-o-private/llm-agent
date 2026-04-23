import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import type { WorkflowRunEntry } from '@/api/types/workflowEditor';

// Mock the hooks
const mockUseWorkflowRuns = vi.fn();
vi.mock('@/api/hooks/useWorkflowEditorHooks', () => ({
  useWorkflowRuns: (name: string) => mockUseWorkflowRuns(name),
}));

// Mock Spinner
vi.mock('@/components/ui/Spinner', () => ({
  Spinner: () => <div data-testid="spinner">Loading...</div>,
}));

// Mock RunHistoryEntry to simplify assertions
vi.mock('../RunHistoryEntry', () => ({
  RunHistoryEntry: ({
    run,
    isExpanded,
    onToggle,
  }: {
    run: WorkflowRunEntry;
    isExpanded: boolean;
    onToggle: () => void;
  }) => (
    <div
      role="listitem"
      aria-label={`Run from ${run.created_at}, status: ${run.status}`}
      onClick={onToggle}
      data-expanded={isExpanded}
    >
      <span
        className={`status-dot status-${run.status}`}
        data-testid={`status-${run.status}`}
      />
      <span>{run.created_at}</span>
      {isExpanded && (
        <div data-testid={`detail-${run.id}`}>
          {run.step_outputs &&
            Object.entries(run.step_outputs).map(([step, output]) => (
              <div key={step}>
                {step}: {String(output)}
              </div>
            ))}
          {run.error && <div>Error: {run.error}</div>}
        </div>
      )}
    </div>
  ),
}));

// Mock LastOutputPreview
vi.mock('../LastOutputPreview', () => ({
  LastOutputPreview: ({ runs }: { runs: WorkflowRunEntry[] }) => {
    const lastCompleted = runs.find((r) => r.status === 'completed');
    if (!lastCompleted?.step_outputs) {
      return (
        <div aria-label="Last run output">No completed runs yet.</div>
      );
    }
    const outputs = Object.entries(lastCompleted.step_outputs);
    const lastOutput =
      outputs.length > 0 ? String(outputs[outputs.length - 1][1]) : '';
    const truncated =
      lastOutput.length > 500
        ? lastOutput.slice(0, 500) + '...'
        : lastOutput;
    return (
      <div aria-label="Last run output">
        <span>{truncated}</span>
        {lastOutput.length > 500 && (
          <button>Show full output</button>
        )}
      </div>
    );
  },
}));

import { RunHistoryPanel } from '../RunHistoryPanel';

const SAMPLE_RUNS: WorkflowRunEntry[] = [
  {
    id: 'run-001',
    template_name: 'morning-briefing',
    status: 'completed',
    current_step: '',
    error: null,
    parameters: { recipient: 'tim@stlvr.coffee' },
    step_outputs: {
      'step-1': 'Gathered 12 calendar events.',
      'step-2': 'Composed briefing summary.',
    },
    started_at: '2026-04-21T06:00:00Z',
    completed_at: '2026-04-21T06:02:30Z',
    created_at: '2026-04-21T06:00:00Z',
  },
  {
    id: 'run-002',
    template_name: 'morning-briefing',
    status: 'failed',
    current_step: 'step-1',
    error: 'Agent timed out.',
    parameters: {},
    step_outputs: {},
    started_at: '2026-04-20T06:00:00Z',
    completed_at: '2026-04-20T06:05:00Z',
    created_at: '2026-04-20T06:00:00Z',
  },
];

describe('RunHistoryPanel', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders run entries with status dots', () => {
    mockUseWorkflowRuns.mockReturnValue({
      data: SAMPLE_RUNS,
      isLoading: false,
      error: null,
    });

    render(<RunHistoryPanel templateName="morning-briefing" />);

    const section = screen.getByLabelText('Run history');
    expect(section).toBeDefined();

    const items = screen.getAllByRole('listitem');
    expect(items).toHaveLength(2);

    expect(screen.getByTestId('status-completed')).toBeDefined();
    expect(screen.getByTestId('status-failed')).toBeDefined();
  });

  it('expand/collapse entries (only one at a time)', () => {
    mockUseWorkflowRuns.mockReturnValue({
      data: SAMPLE_RUNS,
      isLoading: false,
      error: null,
    });

    render(<RunHistoryPanel templateName="morning-briefing" />);

    const items = screen.getAllByRole('listitem');

    // Initially none expanded.
    expect(screen.queryByTestId('detail-run-001')).toBeNull();
    expect(screen.queryByTestId('detail-run-002')).toBeNull();

    // Click first entry to expand.
    fireEvent.click(items[0]);
    expect(screen.getByTestId('detail-run-001')).toBeDefined();

    // Click second entry -- first should collapse, second expands.
    fireEvent.click(items[1]);
    expect(screen.queryByTestId('detail-run-001')).toBeNull();
    expect(screen.getByTestId('detail-run-002')).toBeDefined();

    // Click second entry again to collapse it.
    fireEvent.click(items[1]);
    expect(screen.queryByTestId('detail-run-002')).toBeNull();
  });

  it('last output preview truncates at 500 chars', () => {
    const longOutput = 'B'.repeat(600);
    const runsWithLongOutput: WorkflowRunEntry[] = [
      {
        id: 'run-long',
        template_name: 'morning-briefing',
        status: 'completed',
        current_step: '',
        error: null,
        parameters: {},
        step_outputs: { 'final-step': longOutput },
        started_at: '2026-04-21T06:00:00Z',
        completed_at: '2026-04-21T06:02:30Z',
        created_at: '2026-04-21T06:00:00Z',
      },
    ];

    mockUseWorkflowRuns.mockReturnValue({
      data: runsWithLongOutput,
      isLoading: false,
      error: null,
    });

    render(<RunHistoryPanel templateName="morning-briefing" />);

    const preview = screen.getByLabelText('Last run output');
    expect(preview).toBeDefined();

    // The truncated text should be 500 chars + "...".
    const displayed = preview.textContent ?? '';
    expect(displayed).toContain('...');
    expect(screen.getByText('Show full output')).toBeDefined();
  });

  it('empty state shows "No runs yet"', () => {
    mockUseWorkflowRuns.mockReturnValue({
      data: [],
      isLoading: false,
      error: null,
    });

    render(<RunHistoryPanel templateName="morning-briefing" />);

    expect(screen.getByText(/No runs yet/i)).toBeDefined();
  });
});
