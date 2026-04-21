import React, { useState } from 'react';
import { Button } from '@/components/ui/Button';
import { CardShell } from './CardShell';
import type { ApprovalCard, CalendarHoldPayload } from '@/api/types/today';
import { useApproveCard, useEditCard } from '@/api/hooks/useApprovalsHooks';

interface Props {
  card: Extract<ApprovalCard, { card_type: 'calendar_hold' }>;
}

function formatWindow(start: string, end: string): string {
  try {
    const s = new Date(start);
    const e = new Date(end);
    const diffHr = Math.round((e.getTime() - s.getTime()) / 36e5);
    const fmt = (d: Date) =>
      d.toUTCString().replace('GMT', '').slice(0, -1).trim();
    return `${fmt(s)} → ${fmt(e)} (${diffHr}h)`;
  } catch {
    return `${start} → ${end}`;
  }
}

export const CalendarHoldCard: React.FC<Props> = ({ card }) => {
  const approve = useApproveCard();
  const edit = useEditCard();
  const [editing, setEditing] = useState(false);
  const [title, setTitle] = useState(card.payload.title);
  const [start, setStart] = useState(card.payload.start_at);
  const [end, setEnd] = useState(card.payload.end_at);

  const save = () => {
    const patch: Partial<CalendarHoldPayload> = { title, start_at: start, end_at: end };
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
        onClick={() => setEditing(false)}
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
            aria-label="Confirm"
          >
            Confirm
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
          <label className="block text-xs text-text-muted">Title</label>
          <input
            type="text"
            aria-label="Title"
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            className="w-full rounded-md border border-ui-border bg-ui-element-bg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand-primary"
          />
          <div className="flex gap-2">
            <div className="flex-1">
              <label className="block text-xs text-text-muted">Start</label>
              <input
                type="datetime-local"
                aria-label="Start"
                value={start.slice(0, 16)}
                onChange={(e) => setStart(new Date(e.target.value).toISOString())}
                className="w-full rounded-md border border-ui-border bg-ui-element-bg px-3 py-2 text-sm"
              />
            </div>
            <div className="flex-1">
              <label className="block text-xs text-text-muted">End</label>
              <input
                type="datetime-local"
                aria-label="End"
                value={end.slice(0, 16)}
                onChange={(e) => setEnd(new Date(e.target.value).toISOString())}
                className="w-full rounded-md border border-ui-border bg-ui-element-bg px-3 py-2 text-sm"
              />
            </div>
          </div>
        </div>
      ) : (
        <>
          <div>
            <span className="text-text-muted">Title: </span>
            <span className="font-medium">{card.payload.title}</span>
          </div>
          <div>
            <span className="text-text-muted">When: </span>
            <span className="font-mono text-xs">
              {formatWindow(card.payload.start_at, card.payload.end_at)}
            </span>
          </div>
          {card.payload.source_ref && (
            <div className="text-xs text-text-muted">source: {card.payload.source_ref}</div>
          )}
        </>
      )}
    </CardShell>
  );
};

export default CalendarHoldCard;
