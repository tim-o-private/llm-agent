import React, { useState, useRef, useEffect } from 'react';
import { Bell, Check, CheckCheck, ThumbsUp, ThumbsDown } from 'lucide-react';
import {
  useUnreadCount,
  useNotifications,
  useMarkNotificationRead,
  useMarkAllRead,
  useSubmitNotificationFeedback,
  type Notification,
} from '@/api/hooks/useNotificationHooks';

const categoryStyles: Record<string, string> = {
  heartbeat: 'border-l-brand-primary',
  approval_needed: 'border-l-warning-strong',
  agent_result: 'border-l-bg-info-indicator',
  error: 'border-l-destructive',
  info: 'border-l-ui-border',
};

const NotificationItem: React.FC<{
  notification: Notification;
  onMarkRead: (id: string) => void;
  onSubmitFeedback: (id: string, feedback: 'useful' | 'not_useful') => void;
  feedbackPending?: boolean;
}> = ({ notification, onMarkRead, onSubmitFeedback, feedbackPending }) => {
  const borderClass = categoryStyles[notification.category] || categoryStyles.info;

  const thumbsUpClass =
    notification.feedback === 'useful'
      ? 'text-brand-primary'
      : notification.feedback === 'not_useful'
        ? 'opacity-30 text-text-secondary'
        : 'text-text-secondary';

  const thumbsDownClass =
    notification.feedback === 'not_useful'
      ? 'text-brand-primary'
      : notification.feedback === 'useful'
        ? 'opacity-30 text-text-secondary'
        : 'text-text-secondary';

  return (
    <div className={`px-3 py-2 border-l-2 ${borderClass} ${notification.read ? 'opacity-60' : 'bg-ui-bg-alt'}`}>
      <div className="flex items-start justify-between gap-2">
        <div className="min-w-0 flex-1">
          <p className="text-sm font-medium text-text-primary truncate">{notification.title}</p>
          <p className="text-xs text-text-secondary mt-0.5 line-clamp-2">{notification.body}</p>
          <p className="text-xs text-text-secondary mt-1">
            {new Date(notification.created_at).toLocaleString(undefined, {
              month: 'short',
              day: 'numeric',
              hour: 'numeric',
              minute: '2-digit',
            })}
          </p>
          <div className="flex items-center gap-1 mt-1">
            <button
              onClick={(e) => {
                e.stopPropagation();
                onSubmitFeedback(notification.id, 'useful');
              }}
              disabled={feedbackPending}
              className={`p-1 rounded hover:bg-ui-interactive-bg transition-colors disabled:cursor-not-allowed ${thumbsUpClass}`}
              aria-label="Mark as helpful"
              title="Helpful"
            >
              <ThumbsUp className="h-3 w-3" />
            </button>
            <button
              onClick={(e) => {
                e.stopPropagation();
                onSubmitFeedback(notification.id, 'not_useful');
              }}
              disabled={feedbackPending}
              className={`p-1 rounded hover:bg-ui-interactive-bg transition-colors disabled:cursor-not-allowed ${thumbsDownClass}`}
              aria-label="Mark as not helpful"
              title="Not helpful"
            >
              <ThumbsDown className="h-3 w-3" />
            </button>
          </div>
        </div>
        {!notification.read && (
          <button
            onClick={(e) => {
              e.stopPropagation();
              onMarkRead(notification.id);
            }}
            className="flex-shrink-0 p-1 rounded hover:bg-ui-interactive-bg transition-colors"
            title="Mark as read"
          >
            <Check className="h-3 w-3 text-text-secondary" />
          </button>
        )}
      </div>
    </div>
  );
};

export const NotificationBadge: React.FC = () => {
  const [isOpen, setIsOpen] = useState(false);
  const dropdownRef = useRef<HTMLDivElement>(null);

  const { data: countData } = useUnreadCount();
  const { data: notifications } = useNotifications(false, 20);
  const markRead = useMarkNotificationRead();
  const markAllRead = useMarkAllRead();
  const submitFeedback = useSubmitNotificationFeedback();

  const unreadCount = countData?.count || 0;

  // Close dropdown on outside click
  useEffect(() => {
    if (!isOpen) return;
    const handleClickOutside = (event: Event) => {
      const target = event.target as HTMLElement;
      if (dropdownRef.current && !dropdownRef.current.contains(target)) {
        setIsOpen(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, [isOpen]);

  return (
    <div className="relative" ref={dropdownRef}>
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="relative inline-flex items-center p-1.5 rounded-md hover:bg-ui-interactive-bg transition-colors"
        title={unreadCount > 0 ? `${unreadCount} unread notifications` : 'Notifications'}
      >
        <Bell className="h-4 w-4 text-text-secondary" />
        {unreadCount > 0 && (
          <span className="absolute -top-0.5 -right-0.5 flex h-4 w-4 items-center justify-center rounded-full bg-brand-primary text-[10px] font-medium text-white">
            {unreadCount > 9 ? '9+' : unreadCount}
          </span>
        )}
      </button>

      {isOpen && (
        <div className="absolute right-0 top-full mt-2 w-80 rounded-lg border border-ui-border bg-ui-element-bg shadow-lg z-50">
          {/* Header */}
          <div className="flex items-center justify-between px-3 py-2 border-b border-ui-border">
            <span className="text-sm font-medium text-text-primary">Notifications</span>
            {unreadCount > 0 && (
              <button
                onClick={() => markAllRead.mutate()}
                className="inline-flex items-center text-xs text-text-secondary hover:text-text-primary transition-colors"
              >
                <CheckCheck className="h-3 w-3 mr-1" />
                Mark all read
              </button>
            )}
          </div>

          {/* Notification list */}
          <div className="max-h-80 overflow-y-auto divide-y divide-ui-border">
            {notifications && notifications.length > 0 ? (
              notifications.map((n) => (
                <NotificationItem
                  key={n.id}
                  notification={n}
                  onMarkRead={(id) => markRead.mutate(id)}
                  onSubmitFeedback={(id, feedback) => submitFeedback.mutate({ notificationId: id, feedback })}
                  feedbackPending={submitFeedback.isPending}
                />
              ))
            ) : (
              <div className="px-3 py-6 text-center text-sm text-text-secondary">No notifications</div>
            )}
          </div>
        </div>
      )}
    </div>
  );
};
