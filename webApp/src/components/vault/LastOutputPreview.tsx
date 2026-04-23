/**
 * SPEC-048 AC-20: Last output preview at bottom of run history panel.
 *
 * Shows the final step's output from the most recent completed run,
 * truncated to 500 characters with "Show full output" toggle.
 */

import React, { useState, useMemo } from 'react';
import type { WorkflowRunEntry } from '@/api/types/workflowEditor';

interface LastOutputPreviewProps {
  runs: WorkflowRunEntry[];
}

const MAX_PREVIEW_LENGTH = 500;

export const LastOutputPreview: React.FC<LastOutputPreviewProps> = ({
  runs,
}) => {
  const [showFull, setShowFull] = useState(false);

  const lastOutput = useMemo(() => {
    const lastCompleted = runs.find((r) => r.status === 'completed');
    if (!lastCompleted?.step_outputs) return null;

    const outputs = Object.entries(lastCompleted.step_outputs);
    if (outputs.length === 0) return null;

    // Last step by order in the step_outputs object
    const [stepName, output] = outputs[outputs.length - 1];
    return { stepName, output: String(output) };
  }, [runs]);

  if (!lastOutput) {
    return (
      <div aria-label="Last run output" className="px-3 py-2">
        <p className="text-xs text-text-muted">No completed runs yet.</p>
      </div>
    );
  }

  const isTruncated = lastOutput.output.length > MAX_PREVIEW_LENGTH;
  const displayText =
    showFull || !isTruncated
      ? lastOutput.output
      : lastOutput.output.slice(0, MAX_PREVIEW_LENGTH) + '...';

  return (
    <div aria-label="Last run output" className="px-3 py-2">
      <div className="flex items-center justify-between mb-1">
        <h4 className="text-xs font-medium text-text-muted">Last output</h4>
        {isTruncated && (
          <button
            onClick={() => setShowFull(!showFull)}
            className="text-xs text-brand-primary hover:text-brand-primary/80 transition-colors"
          >
            {showFull ? 'Show less' : 'Show full output'}
          </button>
        )}
      </div>
      <pre className="text-xs text-text-secondary whitespace-pre-wrap break-words max-h-48 overflow-y-auto bg-ui-element-bg/50 rounded p-2">
        {displayText}
      </pre>
    </div>
  );
};
