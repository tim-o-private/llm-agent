import React, { useState } from 'react';
import { Button } from '@/components/ui/Button';
import { CardShell } from './CardShell';
import type { ApprovalCard, EmailDraftPayload } from '@/api/types/today';
import { useApproveCard, useEditCard } from '@/api/hooks/useApprovalsHooks';

interface Props {
  card: Extract<ApprovalCard, { card_type: 'email_draft' }>;
}

export const EmailDraftCard: React.FC<Props> = ({ card }) => {
  const approve = useApproveCard();
  const edit = useEditCard();
  const [editing, setEditing] = useState(false);
  const [subject, setSubject] = useState(card.payload.subject);
  const [body, setBody] = useState(card.payload.body);

  const save = () => {
    const patch: Partial<EmailDraftPayload> = { subject, body };
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
      <Button
        variant="soft"
        size="2"
        onClick={() => {
          setEditing(false);
          setSubject(card.payload.subject);
          setBody(card.payload.body);
        }}
        aria-label="Cancel edit"
      >
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
          <label className="block text-xs text-text-muted">Subject</label>
          <input
            type="text"
            aria-label="Subject"
            value={subject}
            onChange={(e) => setSubject(e.target.value)}
            className="w-full rounded-md border border-ui-border bg-ui-element-bg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand-primary"
          />
          <label className="block text-xs text-text-muted mt-2">Body</label>
          <textarea
            aria-label="Body"
            rows={8}
            value={body}
            onChange={(e) => setBody(e.target.value)}
            className="w-full rounded-md border border-ui-border bg-ui-element-bg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand-primary"
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
