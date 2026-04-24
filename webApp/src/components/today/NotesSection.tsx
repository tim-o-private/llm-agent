import React, { useState, useCallback } from 'react';
import { Button } from '@/components/ui/Button';
import { Textarea } from '@/components/ui/Textarea';
import { useAppendNote } from '@/api/hooks/useTodayHooks';
import { useCreateCapture } from '@/api/hooks/useCaptureHooks';
import { CaptureConfirmation } from '@/components/capture/CaptureConfirmation';
import type { NoteItem } from '@/api/types/today';
import type { CaptureResponse } from '@/api/types/capture';

const HEADING_ID = 'today-notes-heading';

/** localStorage key for the capture routing toggle. */
const CAPTURE_ROUTING_KEY = 'capture_routing_enabled';

function formatTimestamp(iso: string): string {
  try {
    const d = new Date(iso);
    return d.toISOString().slice(0, 16).replace('T', ' ');
  } catch {
    return iso;
  }
}

function useCaptureRoutingEnabled(): [boolean, (v: boolean) => void] {
  const [enabled, setEnabled] = useState(() => {
    try {
      return localStorage.getItem(CAPTURE_ROUTING_KEY) === 'true';
    } catch {
      return false;
    }
  });
  const toggle = useCallback((v: boolean) => {
    setEnabled(v);
    try {
      localStorage.setItem(CAPTURE_ROUTING_KEY, String(v));
    } catch {
      // localStorage unavailable
    }
  }, []);
  return [enabled, toggle];
}

export const NotesSection: React.FC<{ notes: NoteItem[] }> = ({ notes }) => {
  const [value, setValue] = useState('');
  const [captureRoutingEnabled, setCaptureRoutingEnabled] = useCaptureRoutingEnabled();
  const [lastCapture, setLastCapture] = useState<CaptureResponse | null>(null);

  const append = useAppendNote();
  const createCapture = useCreateCapture();

  const isPending = append.isPending || createCapture.isPending;

  const submit = () => {
    const text = value.trim();
    if (!text) return;
    const prev = value;
    setValue('');

    if (captureRoutingEnabled) {
      createCapture.mutate(
        { text, source: 'today' },
        {
          onSuccess: (capture) => {
            setLastCapture(capture);
          },
          onError: () => setValue(prev),
        },
      );
    } else {
      append.mutate(text, {
        onError: () => setValue(prev),
      });
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if ((e.metaKey || e.ctrlKey) && e.key === 'Enter') {
      e.preventDefault();
      submit();
    }
  };

  return (
    <section aria-labelledby={HEADING_ID} className="py-6">
      <div className="flex items-center justify-between mb-3">
        <h2 id={HEADING_ID} className="text-lg font-medium text-text-secondary tracking-tight">
          Notes
        </h2>
        <label className="flex items-center gap-1.5 text-xs text-text-muted cursor-pointer select-none">
          <input
            type="checkbox"
            checked={captureRoutingEnabled}
            onChange={(e) => setCaptureRoutingEnabled(e.target.checked)}
            className="accent-accent-bg"
            aria-label="Enable smart routing"
          />
          Smart routing
        </label>
      </div>

      <div className="space-y-1">
        <Textarea
          aria-label="Capture a note"
          aria-multiline="true"
          rows={3}
          value={value}
          disabled={isPending}
          onChange={(e) => setValue(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="Capture a note"
          resize="vertical"
        />
        <div className="flex items-center justify-between">
          <span className="text-xs text-text-muted">Cmd+Enter to save</span>
          <Button
            variant="soft"
            size="2"
            onClick={submit}
            disabled={isPending || !value.trim()}
            aria-label="Save note"
          >
            {isPending ? 'Saving…' : 'Save'}
          </Button>
        </div>
      </div>

      {lastCapture && lastCapture.status === 'placed' && (
        <CaptureConfirmation
          capture={lastCapture}
          onDismiss={() => setLastCapture(null)}
        />
      )}

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
