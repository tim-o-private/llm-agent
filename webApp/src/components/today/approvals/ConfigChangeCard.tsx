import React, { useState } from 'react';
import { Button } from '@/components/ui/Button';
import { CardShell } from './CardShell';
import type { ApprovalCard } from '@/api/types/today';
import { useApproveCard } from '@/api/hooks/useApprovalsHooks';

interface Props {
  card: Extract<ApprovalCard, { card_type: 'config_change' }>;
}

const DiffBlock: React.FC<{ diff: string }> = ({ diff }) => (
  <pre className="overflow-auto rounded-md bg-ui-bg p-3 text-xs font-mono leading-relaxed">
    {diff.split('\n').map((line, i) => {
      const cls = line.startsWith('+')
        ? 'text-green-600 dark:text-green-400'
        : line.startsWith('-')
          ? 'text-red-600 dark:text-red-400'
          : 'text-text-muted';
      return (
        <div key={i} className={cls}>
          {line || '\u00A0'}
        </div>
      );
    })}
  </pre>
);

export const ConfigChangeCard: React.FC<Props> = ({ card }) => {
  const approve = useApproveCard();
  const [expanded, setExpanded] = useState(false);

  return (
    <CardShell
      card={card}
      actions={
        <Button
          variant="solid"
          size="2"
          onClick={() => approve.mutate({ id: card.id })}
          disabled={approve.isPending}
          aria-label="Approve"
        >
          Approve
        </Button>
      }
    >
      <div>
        <span className="text-text-muted">File: </span>
        <span className="font-mono text-sm">{card.payload.file_path}</span>
      </div>
      <div>
        <span className="text-text-muted">Summary: </span>
        <span>{card.payload.summary}</span>
      </div>
      <div>
        <button
          type="button"
          onClick={() => setExpanded((x) => !x)}
          className="text-xs text-brand-primary hover:underline"
        >
          {expanded ? '▾ Hide diff' : '▸ Diff'}
        </button>
        {expanded && (
          <div className="mt-2">
            <DiffBlock diff={card.payload.diff} />
          </div>
        )}
      </div>
    </CardShell>
  );
};

export default ConfigChangeCard;
