/**
 * SPEC-047 AC-04: Save-status indicator with three states.
 *
 * Shows "Saved" (green check), "Unsaved changes" (amber dot), or
 * "Saving..." (spinner). Uses `aria-live="polite"` so screen readers
 * announce status changes.
 */

import React from 'react';
import { CheckIcon } from '@radix-ui/react-icons';

export type SaveState = 'saved' | 'unsaved' | 'saving';

interface SaveStatusProps {
  state: SaveState;
}

export const SaveStatus: React.FC<SaveStatusProps> = ({ state }) => {
  return (
    <span
      aria-live="polite"
      className="inline-flex items-center gap-1.5 text-xs font-medium select-none"
    >
      {state === 'saved' && (
        <>
          <CheckIcon className="h-3.5 w-3.5 text-green-500" />
          <span className="text-green-600 dark:text-green-400">Saved</span>
        </>
      )}
      {state === 'unsaved' && (
        <>
          <span className="h-2 w-2 rounded-full bg-amber-500" />
          <span className="text-amber-600 dark:text-amber-400">Unsaved changes</span>
        </>
      )}
      {state === 'saving' && (
        <>
          <svg
            className="h-3.5 w-3.5 animate-spin text-text-muted"
            viewBox="0 0 16 16"
            fill="none"
            aria-hidden="true"
          >
            <circle
              cx="8"
              cy="8"
              r="6"
              stroke="currentColor"
              strokeWidth="2"
              strokeDasharray="28"
              strokeDashoffset="8"
              strokeLinecap="round"
            />
          </svg>
          <span className="text-text-muted">Saving...</span>
        </>
      )}
    </span>
  );
};
