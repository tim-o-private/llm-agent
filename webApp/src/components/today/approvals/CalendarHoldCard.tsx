import React from 'react';
import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/Input';
import { CardShell } from './CardShell';
import { useCardEdit } from './useCardEdit';
import type { ApprovalCard } from '@/api/types/today';
import { useApproveCard } from '@/api/hooks/useApprovalsHooks';

interface Props {
  card: Extract<ApprovalCard, { card_type: 'calendar_hold' }>;
}

function formatWindow(start: string, end: string): string {
  try {
    const s = new Date(start);
    const e = new Date(end);
    const diffHr = Math.round((e.getTime() - s.getTime()) / 36e5);
    const fmt = (d: Date) => d.toUTCString().replace('GMT', '').slice(0, -1).trim();
    return `${fmt(s)} → ${fmt(e)} (${diffHr}h)`;
  } catch {
    return `${start} → ${end}`;
  }
}

export const CalendarHoldCard: React.FC<Props> = ({ card }) => {
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
            aria-label="Confirm"
          >
            Confirm
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
          <label className="block text-xs text-text-muted">Title</label>
          <Input
            type="text"
            aria-label="Title"
            value={draft.title}
            onChange={(e) => updateDraft({ title: e.target.value })}
          />
          <div className="flex gap-2">
            <div className="flex-1">
              <label className="block text-xs text-text-muted">Start</label>
              <Input
                type="datetime-local"
                aria-label="Start"
                value={draft.start_at.slice(0, 16)}
                onChange={(e) =>
                  updateDraft({ start_at: new Date(e.target.value).toISOString() })
                }
              />
            </div>
            <div className="flex-1">
              <label className="block text-xs text-text-muted">End</label>
              <Input
                type="datetime-local"
                aria-label="End"
                value={draft.end_at.slice(0, 16)}
                onChange={(e) =>
                  updateDraft({ end_at: new Date(e.target.value).toISOString() })
                }
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
