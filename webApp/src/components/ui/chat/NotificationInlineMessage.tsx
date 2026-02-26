import React, { useEffect } from 'react';
import { ThumbsUp, ThumbsDown } from 'lucide-react';
import { useMarkNotificationRead, useSubmitNotificationFeedback } from '@/api/hooks/useNotificationHooks';
import type { ChatMessage } from '@/stores/useChatStore';

const categoryBorderClass: Record<string, string> = {
  heartbeat: 'border-l-brand-primary',
  approval_needed: 'border-l-warning-strong',
  agent_result: 'border-l-bg-info-indicator',
  error: 'border-l-destructive',
  info: 'border-l-ui-border',
};

function formatRelativeTime(timestamp: Date): string {
  const diffMs = Date.now() - timestamp.getTime();
  const diffMin = Math.floor(diffMs / 60000);
  if (diffMin < 1) return 'just now';
  if (diffMin < 60) return `${diffMin} min ago`;
  const diffHr = Math.floor(diffMin / 60);
  if (diffHr < 24) return `${diffHr}h ago`;
  return timestamp.toLocaleDateString(undefined, { month: 'short', day: 'numeric' });
}

interface NotificationInlineMessageProps {
  message: ChatMessage; // sender = 'notification'
}

export const NotificationInlineMessage: React.FC<NotificationInlineMessageProps> = ({ message }) => {
  const markRead = useMarkNotificationRead();
  const submitFeedback = useSubmitNotificationFeedback();

  const borderClass =
    categoryBorderClass[message.notification_category ?? 'info'] ?? categoryBorderClass.info;

  // Auto-mark-read on mount (AC-14)
  useEffect(() => {
    if (message.notification_id) {
      markRead.mutate(message.notification_id);
    }
    // Run only on mount; markRead is stable
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [message.notification_id]);

  const feedback = message.notification_feedback;

  const thumbsUpClass =
    feedback === 'useful'
      ? 'text-brand-primary'
      : feedback === 'not_useful'
        ? 'opacity-30 text-text-secondary'
        : 'text-text-secondary';

  const thumbsDownClass =
    feedback === 'not_useful'
      ? 'text-brand-primary'
      : feedback === 'useful'
        ? 'opacity-30 text-text-secondary'
        : 'text-text-secondary';

  return (
    <div
      className={`mx-3 my-1 px-3 py-2 border-l-2 ${borderClass} bg-ui-bg-alt rounded-r-md`}
      role="status"
      aria-label={`Notification: ${message.notification_title ?? message.text}`}
    >
      <div className="flex items-start justify-between gap-2">
        <div className="min-w-0 flex-1">
          {message.notification_title && (
            <p className="text-sm font-medium text-text-primary">{message.notification_title}</p>
          )}
          <p className="text-xs text-text-secondary mt-0.5">{message.text}</p>
          <p className="text-xs text-text-secondary mt-1">{formatRelativeTime(message.timestamp)}</p>
          <div className="flex items-center gap-1 mt-1">
            <button
              onClick={() => {
                if (message.notification_id) {
                  submitFeedback.mutate({ notificationId: message.notification_id, feedback: 'useful' });
                }
              }}
              disabled={submitFeedback.isPending || !message.notification_id}
              className={`p-1 rounded hover:bg-ui-interactive-bg transition-colors disabled:cursor-not-allowed ${thumbsUpClass}`}
              aria-label="Mark as helpful"
              title="Helpful"
            >
              <ThumbsUp className="h-3 w-3" />
            </button>
            <button
              onClick={() => {
                if (message.notification_id) {
                  submitFeedback.mutate({ notificationId: message.notification_id, feedback: 'not_useful' });
                }
              }}
              disabled={submitFeedback.isPending || !message.notification_id}
              className={`p-1 rounded hover:bg-ui-interactive-bg transition-colors disabled:cursor-not-allowed ${thumbsDownClass}`}
              aria-label="Mark as not helpful"
              title="Not helpful"
            >
              <ThumbsDown className="h-3 w-3" />
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};
