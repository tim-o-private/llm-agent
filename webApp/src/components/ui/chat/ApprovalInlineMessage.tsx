import React, { useEffect, useState } from 'react';
import { CheckCircle, XCircle, ChevronDown, ChevronUp } from 'lucide-react';
import { useApproveAction, useRejectAction } from '@/api/hooks/useActionsHooks';
import { useMarkNotificationRead } from '@/api/hooks/useNotificationHooks';
import { useChatStore } from '@/stores/useChatStore';
import type { ChatMessage } from '@/stores/useChatStore';

interface ApprovalInlineMessageProps {
  message: ChatMessage; // sender = 'approval'
}

export const ApprovalInlineMessage: React.FC<ApprovalInlineMessageProps> = ({ message }) => {
  const [showAll, setShowAll] = useState(false);
  const [showArgsWhenResolved, setShowArgsWhenResolved] = useState(false);
  const [executionResult, setExecutionResult] = useState<string | null>(null);
  const [executionError, setExecutionError] = useState<string | null>(null);
  const [optimisticStatus, setOptimisticStatus] = useState<string | null>(null);

  const approveAction = useApproveAction();
  const rejectAction = useRejectAction();
  const markRead = useMarkNotificationRead();
  const activeChatId = useChatStore((s) => s.activeChatId);

  // Auto-mark-read on mount (AC-14)
  useEffect(() => {
    if (message.notification_id) {
      markRead.mutate(message.notification_id);
    }
    // Run only on mount
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [message.notification_id]);

  const actionId = message.action_id;
  const toolName = message.action_tool_name ?? 'Unknown tool';
  const toolArgs = message.action_tool_args ?? {};
  const status = optimisticStatus ?? message.action_status ?? 'pending';

  const isPending = status === 'pending';
  const isApproved = status === 'approved';
  const isRejected = status === 'rejected';

  const isMutating = approveAction.isPending || rejectAction.isPending;

  const argEntries = Object.entries(toolArgs);
  const previewArgs = argEntries.slice(0, 3);
  const hasMore = argEntries.length > 3;

  // Border shifts from warning → success on approve, neutral on reject/expire
  const borderColor = isPending
    ? 'border-l-warning-strong'
    : isApproved && executionError
      ? 'border-l-destructive'
      : isApproved
        ? 'border-l-success-indicator'
        : 'border-l-ui-border';

  return (
    <div
      className={`mx-3 my-1 px-3 py-2 border-l-2 ${borderColor} bg-ui-bg-alt rounded-r-md`}
      role="alert"
      aria-label={`Approval request: ${toolName}`}
    >
      <p className="text-sm font-medium text-text-primary mb-1">
        {isPending ? (
          <>
            Approval needed:{' '}
            <span className="font-mono text-xs bg-ui-element-bg px-1 py-0.5 rounded">{toolName}</span>
          </>
        ) : isApproved ? (
          `✓ ${toolName} — Approved`
        ) : isRejected ? (
          `✗ ${toolName} — Rejected`
        ) : (
          `${toolName} — Expired`
        )}
      </p>

      {/* Args always visible when pending; toggled when resolved */}
      {argEntries.length > 0 && isPending && (
        <div className="mb-2">
          <pre className="text-xs text-text-secondary font-mono whitespace-pre-wrap bg-ui-element-bg px-2 py-1 rounded">
            {(showAll ? argEntries : previewArgs)
              .map(([k, v]) => `${k}: ${JSON.stringify(v)}`)
              .join('\n')}
          </pre>
          {hasMore && (
            <button
              onClick={() => setShowAll(!showAll)}
              className="mt-1 inline-flex items-center gap-0.5 text-xs text-text-secondary hover:text-text-primary transition-colors"
            >
              {showAll ? (
                <>
                  <ChevronUp className="h-3 w-3" /> Show less
                </>
              ) : (
                <>
                  <ChevronDown className="h-3 w-3" /> Show {argEntries.length - 3} more
                </>
              )}
            </button>
          )}
        </div>
      )}

      {argEntries.length > 0 && !isPending && (
        <div className="mb-2">
          <button
            onClick={() => setShowArgsWhenResolved(!showArgsWhenResolved)}
            className="inline-flex items-center gap-0.5 text-xs text-text-secondary hover:text-text-primary transition-colors"
          >
            {showArgsWhenResolved ? (
              <>
                <ChevronUp className="h-3 w-3" /> Hide arguments
              </>
            ) : (
              <>
                <ChevronDown className="h-3 w-3" /> Show arguments
              </>
            )}
          </button>
          {showArgsWhenResolved && (
            <pre className="mt-1 text-xs text-text-secondary font-mono whitespace-pre-wrap bg-ui-element-bg px-2 py-1 rounded">
              {argEntries.map(([k, v]) => `${k}: ${JSON.stringify(v)}`).join('\n')}
            </pre>
          )}
        </div>
      )}

      {isPending && actionId && (
        <div className="flex gap-2 mt-2">
          <button
            onClick={() => {
              setOptimisticStatus('approved');
              approveAction.mutate(
                { actionId, sessionId: activeChatId ?? '', toolName },
                {
                  onSuccess: (result) => {
                    const execResult = result.result?.execution_result as string | undefined;
                    if (result.success) {
                      setExecutionResult(execResult ?? 'Executed successfully.');
                    } else {
                      setExecutionError(result.error ?? 'Execution failed');
                    }
                  },
                  onError: () => {
                    setOptimisticStatus(null);
                    setExecutionError('Failed to approve action');
                  },
                },
              );
            }}
            disabled={isMutating}
            className="inline-flex items-center gap-1 px-3 py-1 rounded text-xs font-medium bg-success-subtle text-success-strong hover:bg-success-subtle/80 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
            aria-label="Approve action"
          >
            <CheckCircle className="h-3 w-3" />
            Approve
          </button>
          <button
            onClick={() => {
              setOptimisticStatus('rejected');
              rejectAction.mutate({ actionId, reason: undefined, sessionId: activeChatId ?? '', toolName });
            }}
            disabled={isMutating}
            className="inline-flex items-center gap-1 px-3 py-1 rounded text-xs font-medium bg-destructive-subtle text-destructive hover:bg-destructive-subtle/80 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
            aria-label="Reject action"
          >
            <XCircle className="h-3 w-3" />
            Reject
          </button>
        </div>
      )}

      {isApproved && approveAction.isPending && (
        <p className="text-xs text-text-secondary mt-1">Running...</p>
      )}
      {isApproved && executionResult && (
        <p className="text-xs text-success-strong mt-1">{executionResult}</p>
      )}
      {isApproved && executionError && (
        <p className="text-xs text-destructive mt-1">Failed: {executionError}</p>
      )}
    </div>
  );
};
