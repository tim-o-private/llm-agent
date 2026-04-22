import React from 'react';
import type { RecentEntry } from '@/api/types/today';

const HEADING_ID = 'today-recent-heading';

function relativeTime(iso: string): string {
  try {
    const then = new Date(iso).getTime();
    const diff = Date.now() - then;
    if (Number.isNaN(diff)) return iso;
    const mins = Math.round(diff / 60_000);
    if (mins < 1) return 'just now';
    if (mins < 60) return `${mins} min ago`;
    const hrs = Math.round(mins / 60);
    if (hrs < 24) return `${hrs} hr ago`;
    const days = Math.round(hrs / 24);
    if (days < 7) return `${days} day${days === 1 ? '' : 's'} ago`;
    return new Date(iso).toISOString().slice(0, 10);
  } catch {
    return iso;
  }
}

export const RecentSection: React.FC<{ items: RecentEntry[] }> = ({ items }) => (
  <section aria-labelledby={HEADING_ID} className="py-6">
    <h2 id={HEADING_ID} className="text-lg font-medium text-text-secondary tracking-tight mb-3">
      Recent
    </h2>
    {items.length === 0 ? (
      <p className="text-sm text-text-muted italic">No recent activity.</p>
    ) : (
      <ul aria-label="Recently touched files" className="space-y-1">
        {items.slice(0, 10).map((item) => (
          <li key={item.path} className="flex items-center justify-between gap-3">
            <a
              href={`#/vault/${item.path}`}
              className="font-mono text-sm text-brand-primary hover:underline truncate"
            >
              {item.path}
            </a>
            <time
              dateTime={item.updated_at}
              className="font-mono text-xs text-text-muted whitespace-nowrap"
            >
              {relativeTime(item.updated_at)}
            </time>
          </li>
        ))}
      </ul>
    )}
  </section>
);

export default RecentSection;
