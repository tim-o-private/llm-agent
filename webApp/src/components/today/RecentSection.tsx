import React from 'react';
import type { RecentEntry } from '@/api/types/today';
import { relativeTime } from '@/lib/formatRelativeTime';

const HEADING_ID = 'today-recent-heading';

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
