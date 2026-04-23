import React, { useState } from 'react';
import { clsx } from 'clsx';
import type { ActivityEntry as ActivityEntryType } from '@/api/types/activity';
import { relativeTime } from '@/lib/formatRelativeTime';

const STATUS_STYLES: Record<
  ActivityEntryType['status'],
  { color: string; label: string }
> = {
  done: { color: 'bg-green-500', label: 'Status: done' },
  failed: { color: 'bg-red-500', label: 'Status: failed' },
  awaiting_approval: { color: 'bg-amber-500', label: 'Status: awaiting_approval' },
};

function shortId(id: string): string {
  return id.slice(0, 8);
}

export const ActivityEntryComponent: React.FC<{ entry: ActivityEntryType }> = ({
  entry,
}) => {
  const [showReasoning, setShowReasoning] = useState(false);
  const statusInfo = STATUS_STYLES[entry.status];

  return (
    <article
      aria-label={`Activity: ${entry.action}`}
      className="border-b border-ui-border px-4 py-3 last:border-b-0"
    >
      {/* Top row: timestamp + actor + status dot */}
      <div className="flex items-center justify-between gap-2 mb-1">
        <div className="flex items-center gap-2 min-w-0">
          <time
            dateTime={entry.created_at}
            className="font-mono text-xs text-text-muted whitespace-nowrap"
          >
            {relativeTime(entry.created_at)}
          </time>
          <span className="text-xs text-text-secondary truncate">
            {entry.actor}
          </span>
        </div>
        <span
          className={clsx('h-2 w-2 rounded-full flex-shrink-0', statusInfo.color)}
          aria-label={statusInfo.label}
          role="img"
        />
      </div>

      {/* Action text */}
      <p className="text-sm text-text-primary mb-1">{entry.action}</p>

      {/* Subject path */}
      {entry.subject_path && (
        <a
          href={`/vault/${entry.subject_path}`}
          className="block font-mono text-xs text-brand-primary hover:underline truncate mb-1"
        >
          {entry.subject_path}
        </a>
      )}

      {/* Workflow run link */}
      {entry.workflow_run_id && (
        <a
          href={`/vault/_workflows/_runs/${entry.workflow_run_id}`}
          className="inline-block text-xs px-2 py-0.5 rounded-full bg-ui-element-bg border border-ui-border text-text-secondary hover:text-text-primary transition-colors mb-1"
        >
          Run: {shortId(entry.workflow_run_id)}
        </a>
      )}

      {/* Reasoning toggle */}
      {entry.reasoning && (
        <div className="mt-1">
          <button
            type="button"
            onClick={() => setShowReasoning((prev) => !prev)}
            className="text-xs text-text-muted hover:text-text-secondary transition-colors"
          >
            {showReasoning ? 'Hide' : 'Why?'}
          </button>
          {showReasoning && (
            <p className="mt-1 text-xs text-text-secondary bg-ui-element-bg rounded p-2">
              {entry.reasoning}
            </p>
          )}
        </div>
      )}
    </article>
  );
};

export default ActivityEntryComponent;
