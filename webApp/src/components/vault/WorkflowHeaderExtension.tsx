/**
 * SPEC-048 AC-10/AC-12: Workflow-specific toolbar extension.
 *
 * Renders into FileHeaderBar's `extension` slot.
 * Contains: ValidationStatus indicator + "Dry run" button + "Run now" button.
 * Both buttons disabled when validation is "Invalid".
 */

import React, { useState, useCallback } from 'react';
import { ValidationStatus } from './ValidationStatus';
import type { ValidationResult } from '@/lib/validateWorkflowTemplate';
import * as Tooltip from '@radix-ui/react-tooltip';

interface WorkflowHeaderExtensionProps {
  /** Current editor content for validation */
  editorContent: string;
  /** Whether a dry-run is currently in progress */
  isDryRunning: boolean;
  /** Whether a run is currently being dispatched */
  isRunning: boolean;
  /** Called when user clicks "Dry run" */
  onDryRun: () => void;
  /** Called when user clicks "Run now" */
  onRunNow: () => void;
}

export const WorkflowHeaderExtension: React.FC<
  WorkflowHeaderExtensionProps
> = ({ editorContent, isDryRunning, isRunning, onDryRun, onRunNow }) => {
  const [isValid, setIsValid] = useState(false);

  const handleValidationChange = useCallback((result: ValidationResult) => {
    setIsValid(result.valid);
  }, []);

  const buttonsDisabled = !isValid;
  const disabledTooltip = 'Fix validation errors before running';

  return (
    <div className="flex items-center gap-2">
      <ValidationStatus
        content={editorContent}
        onValidationChange={handleValidationChange}
      />

      <div className="w-px h-4 bg-ui-border" />

      <Tooltip.Provider delayDuration={300}>
        <Tooltip.Root>
          <Tooltip.Trigger asChild>
            <button
              data-testid="btn-dry-run"
              aria-label="Dry run workflow"
              disabled={buttonsDisabled || isDryRunning}
              onClick={onDryRun}
              className="inline-flex items-center gap-1 px-2 py-1 text-xs font-medium rounded-md border border-ui-border transition-colors focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-brand-primary disabled:opacity-50 disabled:cursor-not-allowed text-text-muted hover:text-text-primary bg-ui-element-bg hover:bg-ui-interactive-bg-hover"
            >
              {isDryRunning ? (
                <svg
                  className="h-3 w-3 animate-spin"
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
              ) : null}
              Dry run
            </button>
          </Tooltip.Trigger>
          {buttonsDisabled && (
            <Tooltip.Portal>
              <Tooltip.Content
                side="bottom"
                sideOffset={4}
                className="z-50 rounded-md bg-ui-element-bg border border-ui-border px-2 py-1 text-xs text-text-secondary shadow-md"
              >
                {disabledTooltip}
                <Tooltip.Arrow className="fill-ui-element-bg" />
              </Tooltip.Content>
            </Tooltip.Portal>
          )}
        </Tooltip.Root>
      </Tooltip.Provider>

      <Tooltip.Provider delayDuration={300}>
        <Tooltip.Root>
          <Tooltip.Trigger asChild>
            <button
              data-testid="btn-run-now"
              aria-label="Run workflow now"
              disabled={buttonsDisabled || isRunning}
              onClick={onRunNow}
              className="inline-flex items-center gap-1 px-2 py-1 text-xs font-medium rounded-md border border-brand-primary/30 transition-colors focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-brand-primary disabled:opacity-50 disabled:cursor-not-allowed text-brand-primary bg-brand-primary/10 hover:bg-brand-primary/20"
            >
              {isRunning ? (
                <svg
                  className="h-3 w-3 animate-spin"
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
              ) : null}
              Run now
            </button>
          </Tooltip.Trigger>
          {buttonsDisabled && (
            <Tooltip.Portal>
              <Tooltip.Content
                side="bottom"
                sideOffset={4}
                className="z-50 rounded-md bg-ui-element-bg border border-ui-border px-2 py-1 text-xs text-text-secondary shadow-md"
              >
                {disabledTooltip}
                <Tooltip.Arrow className="fill-ui-element-bg" />
              </Tooltip.Content>
            </Tooltip.Portal>
          )}
        </Tooltip.Root>
      </Tooltip.Provider>
    </div>
  );
};
