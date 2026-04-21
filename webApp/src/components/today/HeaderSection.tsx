import React from 'react';
import { ReloadIcon } from '@radix-ui/react-icons';
import { Button } from '@/components/ui/Button';
import { Spinner } from '@/components/ui/Spinner';
import { useRegenerateToday } from '@/api/hooks/useTodayHooks';

interface HeaderSectionProps {
  date: string;
  framing: string | null;
  regenerating?: boolean;
}

function formatLocaleDate(iso: string): string {
  try {
    const [y, m, d] = iso.split('-').map(Number);
    if (!y || !m || !d) return iso;
    const dt = new Date(Date.UTC(y, m - 1, d));
    return dt.toLocaleDateString(undefined, {
      weekday: 'long',
      year: 'numeric',
      month: 'long',
      day: 'numeric',
      timeZone: 'UTC',
    });
  } catch {
    return iso;
  }
}

export const HeaderSection: React.FC<HeaderSectionProps> = ({ date, framing, regenerating }) => {
  const regenerate = useRegenerateToday();
  const busy = regenerate.isPending || !!regenerating;

  return (
    <header className="py-6">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <h1 className="text-2xl font-semibold text-text-primary tracking-tight">
          {formatLocaleDate(date)}
        </h1>
        <Button
          variant="soft"
          size="2"
          onClick={() => regenerate.mutate()}
          disabled={busy}
          aria-label="Regenerate Today"
          aria-busy={busy || undefined}
          className="flex items-center gap-1.5"
        >
          {busy ? <Spinner size={14} /> : <ReloadIcon className="h-4 w-4" aria-hidden="true" />}
          <span>{busy ? 'Regenerating…' : 'Regenerate Today'}</span>
        </Button>
      </div>
      {framing ? (
        <p className="mt-2 text-base text-text-secondary">{framing}</p>
      ) : (
        <p className="mt-2 text-sm text-text-muted italic">
          No framing yet — run today&apos;s briefing.
        </p>
      )}
    </header>
  );
};

export default HeaderSection;
