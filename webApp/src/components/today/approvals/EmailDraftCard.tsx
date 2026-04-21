import React from 'react';
import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/Input';
import { Textarea } from '@/components/ui/Textarea';
import { CardShell } from './CardShell';
import { useCardEdit } from './useCardEdit';
import type { ApprovalCard } from '@/api/types/today';
import { useApproveCard } from '@/api/hooks/useApprovalsHooks';

interface Props {
  card: Extract<ApprovalCard, { card_type: 'email_draft' }>;
}

export const EmailDraftCard: React.FC<Props> = ({ card }) => {
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
          <label className="block text-xs text-text-muted">Subject</label>
          <Input
            type="text"
            aria-label="Subject"
            value={draft.subject}
            onChange={(e) => updateDraft({ subject: e.target.value })}
          />
          <label className="block text-xs text-text-muted mt-2">Body</label>
          <Textarea
            aria-label="Body"
            rows={8}
            value={draft.body}
            onChange={(e) => updateDraft({ body: e.target.value })}
          />
        </div>
      ) : (
        <>
          <div>
            <span className="text-text-muted">To: </span>
            <span className="font-mono">{card.payload.to.join(', ')}</span>
          </div>
          <div>
            <span className="text-text-muted">Subject: </span>
            <span className="font-medium">{card.payload.subject}</span>
          </div>
          <div className="border-t border-ui-border pt-2 whitespace-pre-wrap">
            {card.payload.body}
          </div>
        </>
      )}
    </CardShell>
  );
};

export default EmailDraftCard;
