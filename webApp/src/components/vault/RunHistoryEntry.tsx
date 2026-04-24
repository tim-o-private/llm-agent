/**
 * SPEC-048 AC-18/AC-19: Single run history entry.
 *
 * Shows timestamp (relative), status dot, duration, current step for running.
 * Clicking expands inline: step_outputs, error, parameters.
 */

import React from 'react';
import { ChevronDownIcon, ChevronRightIcon } from '@radix-ui/react-icons';
import type { WorkflowRunEntry } from '@/api/types/workflowEditor';
import { relativeTime } from '@/lib/formatRelativeTime';

interface RunHistoryEntryProps {
  run: WorkflowRunEntry;
  isExpanded: boolean;
  onToggle: () => void;
}

const STATUS_COLORS: Record<WorkflowRunEntry['status'], string> = {
  completed: 'bg-green-500',
  failed: 'bg-red-500',
  running: 'bg-amber-500',
  pending: 'bg-gray-400',
  cancelled: 'bg-gray-400',
  waiting_for_approval: 'bg-blue-500',
};

const STATUS_LABELS: Record<WorkflowRunEntry['status'], string> = {
  completed: 'completed',
  failed: 'failed',
  running: 'running',
  pending: 'pending',
  cancelled: 'cancelled',
  waiting_for_approval: 'waiting for approval',
};

function formatDuration(
  startedAt: string | null,
  completedAt: string | null,
  status: WorkflowRunEntry['status'],
): string {
  if (status === 'running' || status === 'pending') return 'running';
  if (!startedAt || !completedAt) return '--';

  const start = new Date(startedAt).getTime();
  const end = new Date(completedAt).getTime();
  const diffSec = Math.round((end - start) / 1000);

  if (diffSec < 60) return `${diffSec}s`;
  const min = Math.floor(diffSec / 60);
  const sec = diffSec % 60;
  return `${min}m ${sec}s`;
}

export const RunHistoryEntry: React.FC<RunHistoryEntryProps> = ({
  run,
  isExpanded,
  onToggle,
}) => {
  const Chevron = isExpanded ? ChevronDownIcon : ChevronRightIcon;

  return (
    <div
      role="listitem"
      aria-label={`Run from ${run.created_at}, status: ${STATUS_LABELS[run.status]}`}
    >
      <button
        onClick={onToggle}
        className="w-full text-left px-3 py-2 hover:bg-ui-interactive-bg-hover transition-colors focus-visible:outline-2 focus-visible:outline-offset-[-2px] focus-visible:outline-brand-primary"
      >
        <div className="flex items-center gap-2">
          <Chevron className="h-3 w-3 text-text-muted flex-shrink-0" />
          <span
            className={`h-2 w-2 rounded-full flex-shrink-0 ${STATUS_COLORS[run.status]}`}
            aria-hidden="true"
          />
          <span
            className="text-xs text-text-primary truncate flex-1"
            title={run.created_at}
          >
            {relativeTime(run.created_at)}
          </span>
          <span className="text-xs font-mono text-text-muted flex-shrink-0">
            {formatDuration(run.started_at, run.completed_at, run.status)}
          </span>
        </div>
        {run.status === 'running' && run.current_step && (
          <div className="ml-7 mt-0.5 text-xs text-amber-500 truncate">
            {run.current_step}
          </div>
        )}
      </button>

      {/* Expanded detail */}
      {isExpanded && (
        <div
          aria-label={`Run details for ${run.id}`}
          className="px-3 pb-3 ml-4 border-l-2 border-ui-border"
        >
          {/* Error */}
          {run.error && (
            <div className="mt-2 p-2 bg-red-500/10 border border-red-500/20 rounded text-xs text-red-400">
              <strong className="font-medium">Error:</strong> {run.error}
            </div>
          )}

          {/* Parameters */}
          {run.parameters && Object.keys(run.parameters).length > 0 && (
            <div className="mt-2">
              <h4 className="text-xs font-medium text-text-muted mb-1">
                Parameters
              </h4>
              <div className="space-y-0.5">
                {Object.entries(run.parameters).map(([key, value]) => (
                  <div
                    key={key}
                    className="text-xs font-mono text-text-secondary"
                  >
                    <span className="text-text-muted">{key}:</span>{' '}
                    {String(value)}
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Step outputs */}
          {run.step_outputs && Object.keys(run.step_outputs).length > 0 && (
            <div className="mt-2">
              <h4 className="text-xs font-medium text-text-muted mb-1">
                Step outputs
              </h4>
              <div className="space-y-1.5">
                {Object.entries(run.step_outputs).map(([step, output]) => (
                  <div key={step}>
                    <div className="text-xs font-medium text-text-secondary">
                      {step}
                    </div>
                    <pre className="text-xs text-text-muted mt-0.5 whitespace-pre-wrap break-words max-h-32 overflow-y-auto bg-ui-element-bg/50 rounded p-1.5">
                      {String(output).slice(0, 2000)}
                      {String(output).length > 2000 && '...'}
                    </pre>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
};
