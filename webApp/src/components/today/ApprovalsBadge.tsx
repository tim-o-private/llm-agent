import React from 'react';
import { BellIcon } from '@radix-ui/react-icons';
import { clsx } from 'clsx';
import { Badge } from '@/components/ui/Badge';
import { useApprovalsCount } from '@/api/hooks/useApprovalsHooks';

export interface ApprovalsBadgeProps {
  onJump?: () => void;
}

export const ApprovalsBadge: React.FC<ApprovalsBadgeProps> = ({ onJump }) => {
  const { data: count = 0 } = useApprovalsCount();
  const display = count >= 10 ? '9+' : count > 0 ? String(count) : '';
  const label = count === 0 ? 'No pending approvals' : `${count} pending approvals`;

  return (
    <div aria-live="polite">
      <button
        type="button"
        onClick={onJump}
        aria-label={label}
        className={clsx(
          'inline-flex items-center gap-1.5 rounded-md px-2 py-1 transition-colors',
          'hover:bg-ui-interactive-bg-hover focus:outline-none',
          count === 0 && 'opacity-60',
        )}
      >
        <BellIcon className="h-4 w-4 text-text-secondary" aria-hidden="true" />
        {count > 0 && (
          <Badge variant="soft" color="amber" size="1">
            {display}
          </Badge>
        )}
      </button>
    </div>
  );
};

export default ApprovalsBadge;
