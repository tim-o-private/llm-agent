/**
 * ExecutionStatus — renders execution outcome on approved approval cards.
 *
 * Three states:
 * - Success: green check + summary text
 * - Failure: amber warning + error message + retry button
 * - No executor: neutral chip "Approved as record only"
 *
 * SPEC-052 AC-14, AC-15
 */

import React from 'react';
import { clsx } from 'clsx';
import { Button } from '@/components/ui/Button';
import { useRetryCard } from '@/api/hooks/useApprovalsHooks';
import type { ApprovalCard } from '@/api/types/today';

interface ExecutionStatusProps {
  card: ApprovalCard;
}

export const ExecutionStatus: React.FC<ExecutionStatusProps> = ({ card }) => {
  const retry = useRetryCard();

  // Only show for approved cards with execution data
  if (card.status !== 'approved') return null;
  if (!card.executed_at) return null;

  const hasError = !!card.execution_error;

  // Success state
  if (!hasError && card.execution_result) {
    const summary = describeResult(card);
    return (
      <div
        className={clsx(
          'flex items-center gap-2 mt-3 px-3 py-2 rounded-md',
          'bg-green-50 dark:bg-green-950/30 text-green-700 dark:text-green-400',
          'text-sm',
        )}
        role="status"
        aria-label="Execution succeeded"
      >
        <CheckIcon />
        <span>{summary}</span>
      </div>
    );
  }

  // Failure state
  if (hasError) {
    return (
      <div
        className={clsx(
          'mt-3 px-3 py-2 rounded-md',
          'bg-amber-50 dark:bg-amber-950/30 text-amber-700 dark:text-amber-400',
          'text-sm',
        )}
        role="alert"
        aria-label="Execution failed"
      >
        <div className="flex items-center gap-2">
          <WarningIcon />
          <span className="flex-1">{card.execution_error}</span>
        </div>
        <div className="mt-2">
          <Button
            variant="soft"
            color="amber"
            size="1"
            onClick={() => retry.mutate({ id: card.id })}
            disabled={retry.isPending}
            aria-label="Retry execution"
          >
            {retry.isPending ? 'Retrying...' : 'Retry'}
          </Button>
        </div>
      </div>
    );
  }

  // No executor registered
  return (
    <div
      className={clsx(
        'flex items-center gap-2 mt-3 px-3 py-2 rounded-md',
        'bg-gray-100 dark:bg-gray-800 text-gray-500 dark:text-gray-400',
        'text-sm',
      )}
      role="status"
      aria-label="No executor"
    >
      <span>No executor — approved as record only</span>
    </div>
  );
};

function describeResult(card: ApprovalCard): string {
  const result = card.execution_result;
  if (!result) return 'Executed successfully';

  switch (card.card_type) {
    case 'email_draft':
      return `Sent to ${result.to || 'recipient'}`;
    case 'calendar_hold':
      return `Event created${result.html_link ? '' : ''}`;
    case 'outreach':
      return `${result.channel === 'other' ? 'Approved (manual follow-up)' : `Sent via ${result.channel}`}`;
    case 'workflow_proposal':
      return `Written to ${result.path || 'vault'}`;
    case 'config_change':
      return `Applied to ${result.path || 'file'}`;
    case 'file_operation':
      return `${result.operation || 'Operation'} completed`;
    default:
      return 'Executed successfully';
  }
}

function CheckIcon() {
  return (
    <svg
      className="w-4 h-4 flex-shrink-0"
      fill="none"
      stroke="currentColor"
      viewBox="0 0 24 24"
      aria-hidden="true"
    >
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        strokeWidth={2}
        d="M5 13l4 4L19 7"
      />
    </svg>
  );
}

function WarningIcon() {
  return (
    <svg
      className="w-4 h-4 flex-shrink-0"
      fill="none"
      stroke="currentColor"
      viewBox="0 0 24 24"
      aria-hidden="true"
    >
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        strokeWidth={2}
        d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4.5c-.77-.833-2.694-.833-3.464 0L3.34 16.5c-.77.833.192 2.5 1.732 2.5z"
      />
    </svg>
  );
}

export default ExecutionStatus;
