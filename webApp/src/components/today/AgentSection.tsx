import React from 'react';
import type { AgentItem, TodayResponse } from '@/api/types/today';
import { useActivityStore } from '@/stores/useActivityStore';

const HEADING_ID = 'today-agent-heading';

interface GroupDef {
  key: 'running' | 'watching' | 'recent' | 'blocked';
  label: string;
  emptyCopy: string;
}

const GROUPS: GroupDef[] = [
  { key: 'running', label: 'Running', emptyCopy: 'Nothing running.' },
  { key: 'watching', label: 'Watching', emptyCopy: 'Nothing to watch.' },
  { key: 'recent', label: 'Recently done', emptyCopy: 'Nothing recent.' },
  { key: 'blocked', label: 'Blocked', emptyCopy: 'Nothing blocked.' },
];

const AgentItemRow: React.FC<{ item: AgentItem }> = ({ item }) => (
  <li className="text-sm text-text-primary">
    {item.link ? (
      <a href={item.link} className="text-brand-primary hover:underline">
        {item.text}
      </a>
    ) : (
      item.text
    )}
  </li>
);

export const AgentSection: React.FC<{ agent: TodayResponse['agent'] }> = ({ agent }) => {
  const openActivityPanel = useActivityStore((s) => s.open);

  return (
    <section aria-labelledby={HEADING_ID} className="py-6">
      <h2 id={HEADING_ID} className="text-lg font-medium text-text-secondary tracking-tight mb-3">
        Agent
      </h2>
      <div className="space-y-4">
        {GROUPS.map((g) => {
          const items = agent[g.key] ?? [];
          const subheadingId = `today-agent-${g.key}-heading`;
          return (
            <div
              key={g.key}
              role="group"
              aria-labelledby={subheadingId}
            >
              <h3 id={subheadingId} className="text-sm font-medium text-text-primary mb-1">
                {g.label}
              </h3>
              {items.length === 0 ? (
                <p className="text-sm text-text-muted italic">{g.emptyCopy}</p>
              ) : (
                <ul className="space-y-1 pl-1">
                  {items.map((item, i) => (
                    <AgentItemRow key={`${item.text}-${i}`} item={item} />
                  ))}
                </ul>
              )}
            </div>
          );
        })}
      </div>

      {/* AC-18: "View activity log" link at bottom of Agent section */}
      <button
        type="button"
        onClick={openActivityPanel}
        aria-label="View full activity log"
        className="mt-3 text-sm text-brand-primary hover:underline"
      >
        View activity log
      </button>
    </section>
  );
};

export default AgentSection;
