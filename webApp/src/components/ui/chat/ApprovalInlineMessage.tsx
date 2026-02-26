import React, { useEffect, useState } from 'react';
import { CheckCircle, XCircle, ChevronDown, ChevronUp } from 'lucide-react';
import { useApproveAction, useRejectAction } from '@/api/hooks/useActionsHooks';
import { useMarkNotificationRead } from '@/api/hooks/useNotificationHooks';
import type { ChatMessage } from '@/stores/useChatStore';

interface ApprovalInlineMessageProps {
  message: ChatMessage; // sender = 'approval'
}

export const ApprovalInlineMessage: React.FC<ApprovalInlineMessageProps> = ({ message }) => {
  const [showAll, setShowAll] = useState(false);
  const approveAction = useApproveAction();
  const rejectAction = useRejectAction();
  const markRead = useMarkNotificationRead();

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
  const status = message.action_status ?? 'pending';

  const isPending = status === 'pending';
  const isApproved = status === 'approved';
  const isRejected = status === 'rejected';
  const isExpired = status === 'expired';

  const isMutating = approveAction.isPending || rejectAction.isPending;

  const argEntries = Object.entries(toolArgs);
  const previewArgs = argEntries.slice(0, 3);
  const hasMore = argEntries.length > 3;

  return (
    <div
      className="mx-3 my-1 px-3 py-2 border-l-2 border-l-warning-strong bg-ui-bg-alt rounded-r-md"
      role="alert"
      aria-label={`Approval request: ${toolName}`}
    >
      <p className="text-sm font-medium text-text-primary mb-1">
        Approval needed: <span className="font-mono text-xs bg-ui-element-bg px-1 py-0.5 rounded">{toolName}</span>
      </p>

      {argEntries.length > 0 && (
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

      {isPending && actionId && (
        <div className="flex gap-2 mt-2">
          <button
            onClick={() => approveAction.mutate(actionId)}
            disabled={isMutating}
            className="inline-flex items-center gap-1 px-3 py-1 rounded text-xs font-medium bg-success-subtle text-success-strong hover:bg-success-subtle/80 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
            aria-label="Approve action"
          >
            <CheckCircle className="h-3 w-3" />
            Approve
          </button>
          <button
            onClick={() => rejectAction.mutate({ actionId })}
            disabled={isMutating}
            className="inline-flex items-center gap-1 px-3 py-1 rounded text-xs font-medium bg-destructive-subtle text-destructive hover:bg-destructive-subtle/80 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
            aria-label="Reject action"
          >
            <XCircle className="h-3 w-3" />
            Reject
          </button>
        </div>
      )}

      {isApproved && (
        <p className="text-xs font-medium text-success-strong mt-1">Approved ✓</p>
      )}
      {isRejected && (
        <p className="text-xs font-medium text-destructive mt-1">Rejected</p>
      )}
      {isExpired && (
        <p className="text-xs font-medium text-text-secondary mt-1">Expired</p>
      )}
    </div>
  );
};
