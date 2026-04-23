/**
 * SPEC-048 AC-17/AC-18/AC-19/AC-20/AC-21: Run history panel (right sub-pane).
 *
 * Lists past runs from useWorkflowRuns with adaptive polling.
 * Each entry is expandable (one at a time). Bottom shows last output preview.
 */

import React, { useState } from 'react';
import { useWorkflowRuns } from '@/api/hooks/useWorkflowEditorHooks';
import { RunHistoryEntry } from './RunHistoryEntry';
import { LastOutputPreview } from './LastOutputPreview';
import { Spinner } from '@/components/ui/Spinner';

interface RunHistoryPanelProps {
  templateName: string;
}

export const RunHistoryPanel: React.FC<RunHistoryPanelProps> = ({
  templateName,
}) => {
  const { data: runs, isLoading, error } = useWorkflowRuns(templateName);
  const [expandedRunId, setExpandedRunId] = useState<string | null>(null);

  const handleToggle = (runId: string) => {
    setExpandedRunId((prev) => (prev === runId ? null : runId));
  };

  if (isLoading) {
    return (
      <section
        aria-label="Run history"
        className="h-full flex items-center justify-center"
      >
        <Spinner size={16} />
      </section>
    );
  }

  if (error) {
    return (
      <section aria-label="Run history" className="h-full p-3">
        <p className="text-xs text-red-500">Failed to load run history</p>
      </section>
    );
  }

  const items = runs ?? [];

  return (
    <section aria-label="Run history" className="h-full flex flex-col">
      {/* Header */}
      <div className="px-3 py-2 border-b border-ui-border flex-shrink-0">
        <h2 className="text-xs font-semibold text-text-muted uppercase tracking-wider">
          Run History
        </h2>
      </div>

      {/* Run list */}
      <div className="flex-1 overflow-y-auto min-h-0">
        {items.length === 0 ? (
          <div className="px-3 py-8 text-center">
            <p className="text-xs text-text-muted">
              No runs yet. Click &quot;Run now&quot; to start.
            </p>
          </div>
        ) : (
          <div role="list">
            {items.map((run) => (
              <RunHistoryEntry
                key={run.id}
                run={run}
                isExpanded={expandedRunId === run.id}
                onToggle={() => handleToggle(run.id)}
              />
            ))}
          </div>
        )}
      </div>

      {/* Last output preview */}
      <div className="flex-shrink-0 border-t border-ui-border">
        <LastOutputPreview runs={items} />
      </div>
    </section>
  );
};
