import React from 'react';
import { ActivityLogIcon } from '@radix-ui/react-icons';
import { clsx } from 'clsx';
import { Badge } from '@/components/ui/Badge';
import { ApprovalsBadge } from '@/components/today/ApprovalsBadge';
import { useActivityCount } from '@/api/hooks/useActivityHooks';
import { useActivityStore } from '@/stores/useActivityStore';

interface AmbientIndicatorProps {
  /** Callback when the approvals badge is clicked (scrolls to approvals section). */
  onJumpToApprovals?: () => void;
}

/**
 * SPEC-050 AC-09: Combined topbar indicator showing both pending approvals
 * and new activity entries. Replaces the standalone ApprovalsBadge in TopBar.
 */
export const AmbientIndicator: React.FC<AmbientIndicatorProps> = ({
  onJumpToApprovals,
}) => {
  const { data: activityCount = { total: 0, since_last_viewed: 0 } } =
    useActivityCount();
  const openPanel = useActivityStore((s) => s.open);

  const count = activityCount.since_last_viewed;
  const display = count >= 10 ? '9+' : count > 0 ? String(count) : '';
  const label =
    count === 0 ? 'No new agent actions' : `${count} new agent actions`;

  return (
    <div className="flex items-center gap-1">
      {/* Approvals badge — existing component, unchanged behavior */}
      <ApprovalsBadge onJump={onJumpToApprovals} />

      {/* Activity badge */}
      <div aria-live="polite">
        <button
          type="button"
          onClick={openPanel}
          aria-label={label}
          className={clsx(
            'inline-flex items-center gap-1.5 rounded-md px-2 py-1 transition-colors',
            'hover:bg-ui-interactive-bg-hover focus:outline-none',
            count === 0 && 'opacity-60',
          )}
        >
          <ActivityLogIcon
            className="h-4 w-4 text-text-secondary"
            aria-hidden="true"
          />
          {count > 0 && (
            <Badge variant="soft" color="blue" size="1">
              {display}
            </Badge>
          )}
        </button>
      </div>
    </div>
  );
};

export default AmbientIndicator;
