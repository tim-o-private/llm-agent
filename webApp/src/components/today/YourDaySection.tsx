import React from 'react';
import { Link } from '@radix-ui/themes';
import type { WikilinkItem } from '@/api/types/today';

const HEADING_ID = 'today-your-day-heading';

export const YourDaySection: React.FC<{ items: WikilinkItem[] }> = ({ items }) => (
  <section aria-labelledby={HEADING_ID} className="py-6">
    <h2 id={HEADING_ID} className="text-lg font-medium text-text-secondary tracking-tight mb-3">
      Your day
    </h2>
    {items.length === 0 ? (
      <p className="text-sm text-text-muted italic">Nothing on your calendar today.</p>
    ) : (
      <ul className="space-y-2">
        {items.map((item, i) => (
          <li key={`${item.text}-${i}`} className="text-sm text-text-primary">
            <span>{item.text}</span>
            {item.wikilink && (
              <>
                {' '}
                <Link href={`#/vault/${item.wikilink}`} size="2" className="font-mono">
                  {item.wikilink}
                </Link>
              </>
            )}
          </li>
        ))}
      </ul>
    )}
  </section>
);

export default YourDaySection;
