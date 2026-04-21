import React, { useState } from 'react';
import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/Input';
import { Textarea } from '@/components/ui/Textarea';
import { CardShell } from './CardShell';
import { useCardEdit } from './useCardEdit';
import type { ApprovalCard } from '@/api/types/today';
import { useApproveCard } from '@/api/hooks/useApprovalsHooks';

interface Props {
  card: Extract<ApprovalCard, { card_type: 'workflow_proposal' }>;
}

export const WorkflowProposalCard: React.FC<Props> = ({ card }) => {
  const approve = useApproveCard();
  const [expanded, setExpanded] = useState(false);
  const { editing, startEdit, draft, updateDraft, editActionRow } = useCardEdit(card);

  return (
    <CardShell
      card={card}
      editing={editing}
      actions={
        <>
          <Button
            variant="solid"
            size="2"
            onClick={() => approve.mutate({ id: card.id })}
            disabled={approve.isPending}
            aria-label="Accept"
          >
            Accept
          </Button>
          <Button variant="soft" size="2" onClick={startEdit} aria-label="Edit">
            Edit
          </Button>
        </>
      }
      actionRowOverride={editing ? editActionRow : undefined}
    >
      {editing ? (
        <div className="space-y-2">
          <label className="block text-xs text-text-muted">Filename</label>
          <Input
            type="text"
            aria-label="Filename"
            value={draft.filename}
            onChange={(e) => updateDraft({ filename: e.target.value })}
            className="font-mono"
          />
          <label className="block text-xs text-text-muted mt-2">Body</label>
          <Textarea
            aria-label="Body"
            rows={12}
            value={draft.body}
            onChange={(e) => updateDraft({ body: e.target.value })}
            className="font-mono"
          />
        </div>
      ) : (
        <>
          <div>
            <span className="text-text-muted">Filename: </span>
            <span className="font-mono text-sm">{card.payload.filename}</span>
          </div>
          <div>
            <span className="text-text-muted">Pattern: </span>
            <span>{card.payload.pattern_observed}</span>
          </div>
          <div>
            <button
              type="button"
              onClick={() => setExpanded((x) => !x)}
              className="text-xs text-brand-primary hover:underline"
            >
              {expanded ? '▾ Hide preview' : '▸ Preview'}
            </button>
            {expanded && (
              <pre className="mt-2 overflow-auto rounded-md bg-ui-bg p-3 text-xs font-mono text-text-primary">
                {card.payload.body}
              </pre>
            )}
          </div>
        </>
      )}
    </CardShell>
  );
};

export default WorkflowProposalCard;
