import React, { useState } from 'react';
import { Button } from '@/components/ui/Button';
import { useEditCard } from '@/api/hooks/useApprovalsHooks';

export interface UseCardEditResult<P extends object> {
  editing: boolean;
  startEdit: () => void;
  draft: P;
  updateDraft: (patch: Partial<P>) => void;
  editActionRow: React.ReactNode;
}

export function useCardEdit<P extends object>(card: {
  id: string;
  payload: P;
}): UseCardEditResult<P> {
  const [editing, setEditing] = useState(false);
  const [draft, setDraft] = useState<P>(card.payload);
  const edit = useEditCard();

  const startEdit = () => {
    setDraft(card.payload);
    setEditing(true);
  };

  const cancelEdit = () => {
    setDraft(card.payload);
    setEditing(false);
  };

  const save = () => {
    edit.mutate(
      { id: card.id, payload_patch: draft as Record<string, unknown> },
      { onSuccess: () => setEditing(false) },
    );
  };

  const updateDraft = (patch: Partial<P>) => setDraft((d) => ({ ...d, ...patch }));

  const editActionRow = (
    <div className="flex flex-wrap items-center justify-end gap-2">
      <Button variant="solid" size="2" onClick={save} disabled={edit.isPending} aria-label="Save">
        Save
      </Button>
      <Button variant="soft" size="2" onClick={cancelEdit} aria-label="Cancel edit">
        Cancel
      </Button>
    </div>
  );

  return { editing, startEdit, draft, updateDraft, editActionRow };
}
