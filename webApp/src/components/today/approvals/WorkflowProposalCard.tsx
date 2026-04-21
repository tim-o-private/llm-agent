import React, { useState } from 'react';
import { Button } from '@/components/ui/Button';
import { CardShell } from './CardShell';
import type { ApprovalCard, WorkflowProposalPayload } from '@/api/types/today';
import { useApproveCard, useEditCard } from '@/api/hooks/useApprovalsHooks';

interface Props {
  card: Extract<ApprovalCard, { card_type: 'workflow_proposal' }>;
}

export const WorkflowProposalCard: React.FC<Props> = ({ card }) => {
  const approve = useApproveCard();
  const edit = useEditCard();
  const [editing, setEditing] = useState(false);
  const [expanded, setExpanded] = useState(false);
  const [filename, setFilename] = useState(card.payload.filename);
  const [body, setBody] = useState(card.payload.body);

  const save = () => {
    const patch: Partial<WorkflowProposalPayload> = { filename, body };
    edit.mutate(
      { id: card.id, payload_patch: patch },
      { onSuccess: () => setEditing(false) },
    );
  };

  const editActionRow = (
    <div className="flex flex-wrap items-center justify-end gap-2">
      <Button variant="solid" size="2" onClick={save} disabled={edit.isPending} aria-label="Save">
        Save
      </Button>
      <Button variant="soft" size="2" onClick={() => setEditing(false)} aria-label="Cancel edit">
        Cancel
      </Button>
    </div>
  );

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
          <Button variant="soft" size="2" onClick={() => setEditing(true)} aria-label="Edit">
            Edit
          </Button>
        </>
      }
      actionRowOverride={editing ? editActionRow : undefined}
    >
      {editing ? (
        <div className="space-y-2">
          <label className="block text-xs text-text-muted">Filename</label>
          <input
            type="text"
            aria-label="Filename"
            value={filename}
            onChange={(e) => setFilename(e.target.value)}
            className="w-full rounded-md border border-ui-border bg-ui-element-bg px-3 py-2 text-sm font-mono focus:outline-none focus:ring-2 focus:ring-brand-primary"
          />
          <label className="block text-xs text-text-muted mt-2">Body</label>
          <textarea
            aria-label="Body"
            rows={12}
            value={body}
            onChange={(e) => setBody(e.target.value)}
            className="w-full rounded-md border border-ui-border bg-ui-element-bg px-3 py-2 text-sm font-mono focus:outline-none focus:ring-2 focus:ring-brand-primary"
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
