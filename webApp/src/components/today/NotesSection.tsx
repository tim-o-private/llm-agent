import React, { useState } from 'react';
import { Button } from '@/components/ui/Button';
import { useAppendNote } from '@/api/hooks/useTodayHooks';
import type { NoteItem } from '@/api/types/today';

const HEADING_ID = 'today-notes-heading';

function formatTimestamp(iso: string): string {
  try {
    const d = new Date(iso);
    return d.toISOString().slice(0, 16).replace('T', ' ');
  } catch {
    return iso;
  }
}

export const NotesSection: React.FC<{ notes: NoteItem[] }> = ({ notes }) => {
  const [value, setValue] = useState('');
  const append = useAppendNote();

  const submit = () => {
    const text = value.trim();
    if (!text) return;
    const prev = value;
    setValue('');
    append.mutate(text, {
      onError: () => setValue(prev),
    });
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if ((e.metaKey || e.ctrlKey) && e.key === 'Enter') {
      e.preventDefault();
      submit();
    }
  };

  return (
    <section aria-labelledby={HEADING_ID} className="py-6">
      <h2 id={HEADING_ID} className="text-lg font-medium text-text-secondary tracking-tight mb-3">
        Notes
      </h2>

      <div className="space-y-1">
        <textarea
          aria-label="Capture a note"
          aria-multiline="true"
          rows={3}
          value={value}
          disabled={append.isPending}
          onChange={(e) => setValue(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="Capture a note"
          className="w-full rounded-md border border-ui-border bg-ui-element-bg px-3 py-2 text-sm text-text-primary focus:outline-none focus:ring-2 focus:ring-brand-primary resize-y"
        />
        <div className="flex items-center justify-between">
          <span className="text-xs text-text-muted">Cmd+Enter to save</span>
          <Button
            variant="soft"
            size="2"
            onClick={submit}
            disabled={append.isPending || !value.trim()}
            aria-label="Save note"
          >
            {append.isPending ? 'Saving…' : 'Save'}
          </Button>
        </div>
      </div>

      {notes.length === 0 ? (
        <p className="mt-4 text-sm text-text-muted italic">
          No notes yet — capture one above.
        </p>
      ) : (
        <ul aria-label="Captured notes" className="mt-4 space-y-3">
          {notes.map((n, i) => (
            <li key={`${n.created_at}-${i}`} className="text-sm">
              <div className="text-xs text-text-muted font-mono">
                {formatTimestamp(n.created_at)}
              </div>
              <div className="text-text-primary whitespace-pre-wrap">{n.text}</div>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
};

export default NotesSection;
