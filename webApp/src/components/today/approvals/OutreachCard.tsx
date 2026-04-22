import React from 'react';
import { Badge } from '@/components/ui/Badge';
import { Button } from '@/components/ui/Button';
import { Textarea } from '@/components/ui/Textarea';
import { CardShell } from './CardShell';
import { useCardEdit } from './useCardEdit';
import type { ApprovalCard } from '@/api/types/today';
import { useApproveCard } from '@/api/hooks/useApprovalsHooks';

interface Props {
  card: Extract<ApprovalCard, { card_type: 'outreach' }>;
}

export const OutreachCard: React.FC<Props> = ({ card }) => {
  const approve = useApproveCard();
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
            aria-label="Send"
          >
            Send
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
          <label className="block text-xs text-text-muted">Message</label>
          <Textarea
            aria-label="Message"
            rows={5}
            value={draft.message}
            onChange={(e) => updateDraft({ message: e.target.value })}
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
