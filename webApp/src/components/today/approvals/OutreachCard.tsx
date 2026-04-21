import React, { useState } from 'react';
import { Badge } from '@/components/ui/Badge';
import { Button } from '@/components/ui/Button';
import { CardShell } from './CardShell';
import type { ApprovalCard, OutreachPayload } from '@/api/types/today';
import { useApproveCard, useEditCard } from '@/api/hooks/useApprovalsHooks';

interface Props {
  card: Extract<ApprovalCard, { card_type: 'outreach' }>;
}

export const OutreachCard: React.FC<Props> = ({ card }) => {
  const approve = useApproveCard();
  const edit = useEditCard();
  const [editing, setEditing] = useState(false);
  const [message, setMessage] = useState(card.payload.message);

  const save = () => {
    const patch: Partial<OutreachPayload> = { message };
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
            aria-label="Send"
          >
            Send
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
          <label className="block text-xs text-text-muted">Message</label>
          <textarea
            aria-label="Message"
            rows={5}
            value={message}
            onChange={(e) => setMessage(e.target.value)}
            className="w-full rounded-md border border-ui-border bg-ui-element-bg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand-primary"
          />
        </div>
      ) : (
        <>
          <div className="flex items-center gap-2">
            <span className="text-text-muted">To:</span>
            <span className="font-medium">{card.payload.recipient}</span>
            <Badge variant="outline" size="1">
              {card.payload.channel}
            </Badge>
          </div>
          <div className="border-t border-ui-border pt-2 whitespace-pre-wrap">
            {card.payload.message}
          </div>
        </>
      )}
    </CardShell>
  );
};

export default OutreachCard;
