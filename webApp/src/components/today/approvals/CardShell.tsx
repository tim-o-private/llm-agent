import React, { useState } from 'react';
import { clsx } from 'clsx';
import { Badge } from '@/components/ui/Badge';
import { Button } from '@/components/ui/Button';
import { APPROVAL_TYPE_LABEL, type ApprovalCard, type ApprovalCardType } from '@/api/types/today';
import { useRejectCard } from '@/api/hooks/useApprovalsHooks';

type AccentColor = 'blue' | 'violet' | 'amber' | 'red';

const ACCENT: Record<ApprovalCardType, AccentColor> = {
  email_draft: 'blue',
  calendar_hold: 'violet',
  outreach: 'blue',
  workflow_proposal: 'amber',
  config_change: 'amber',
  file_operation: 'red',
};

const BORDER_CLASS: Record<AccentColor, string> = {
  blue: 'border-l-blue-500',
  violet: 'border-l-violet-500',
  amber: 'border-l-amber-500',
  red: 'border-l-red-500',
};

interface CardShellProps {
  card: ApprovalCard;
  children: React.ReactNode;
  /** Primary-action button(s); secondary action like Edit lives alongside. */
  actions: React.ReactNode;
  /** When editing, the caller swaps `children` and passes an edit-mode action row. */
  editing?: boolean;
  /** Override the entire action row (used by approval-card Edit screens). */
  actionRowOverride?: React.ReactNode;
}

export const CardShell: React.FC<CardShellProps> = ({
  card,
  children,
  actions,
  editing,
  actionRowOverride,
}) => {
  const [rejecting, setRejecting] = useState(false);
  const [reason, setReason] = useState('');
  const reject = useRejectCard();

  const typeLabel = APPROVAL_TYPE_LABEL[card.card_type];
  const accent = ACCENT[card.card_type];
  const regionLabel = `${typeLabel} approval: ${card.title}`;

  const confirmReject = () => {
    reject.mutate({ id: card.id, reason: reason || undefined });
  };

  const actionRow = actionRowOverride ? (
    actionRowOverride
  ) : rejecting ? (
    <div className="flex flex-wrap items-center gap-2">
      <input
        type="text"
        aria-label="Optional reason for rejection"
        placeholder="Optional reason for rejection"
        value={reason}
        onChange={(e) => setReason(e.target.value)}
        className="flex-1 min-w-[12rem] rounded-md border border-ui-border bg-ui-element-bg px-2 py-1 text-sm focus:outline-none focus:ring-2 focus:ring-brand-primary"
      />
      <Button
        variant="soft"
        color="gray"
        size="2"
        onClick={confirmReject}
        disabled={reject.isPending}
        aria-label="Confirm reject"
      >
        Confirm reject
      </Button>
      <Button
        variant="ghost"
        size="2"
        onClick={() => {
          setRejecting(false);
          setReason('');
        }}
        aria-label="Cancel reject"
      >
        Cancel
      </Button>
    </div>
  ) : (
    <div className="flex flex-wrap items-center justify-end gap-2">
      {actions}
      {!editing && (
        <Button
          variant="soft"
          color="gray"
          size="2"
          onClick={() => setRejecting(true)}
          aria-label="Reject"
        >
          Reject
        </Button>
      )}
    </div>
  );

  return (
    <div
      role="region"
      aria-label={regionLabel}
      className={clsx(
        'border-l-4 rounded-md bg-ui-element-bg shadow-sm p-5',
        BORDER_CLASS[accent],
      )}
    >
      <div className="flex items-center gap-2 mb-1">
        <Badge variant="soft" color={accent}>
          {typeLabel}
        </Badge>
      </div>
      <h3 className="text-base font-medium text-text-primary mb-3">{card.title}</h3>
      <div className="mb-4 text-sm text-text-primary space-y-2">{children}</div>
      {actionRow}
    </div>
  );
};

export default CardShell;
