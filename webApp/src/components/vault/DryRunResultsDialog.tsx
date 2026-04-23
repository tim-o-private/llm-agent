/**
 * SPEC-048 AC-14 UI: Dry run results dialog.
 *
 * Modal showing parsed steps as a list with name, agent, dependencies, tools.
 * Shows errors if any. Shows parameters. Uses Radix Dialog.
 */

import React from 'react';
import * as Dialog from '@radix-ui/react-dialog';
import { Cross2Icon, CheckCircledIcon, CrossCircledIcon } from '@radix-ui/react-icons';
import { clsx } from 'clsx';
import type { DryRunResult } from '@/api/types/workflowEditor';

interface DryRunResultsDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  result: DryRunResult | null;
}

export const DryRunResultsDialog: React.FC<DryRunResultsDialogProps> = ({
  open,
  onOpenChange,
  result,
}) => {
  if (!result) return null;

  return (
    <Dialog.Root open={open} onOpenChange={onOpenChange}>
      <Dialog.Portal>
        <Dialog.Overlay
          className={clsx(
            'fixed inset-0 bg-black/40 z-40',
            'transition-opacity duration-300 ease-in-out',
            'data-[state=closed]:opacity-0 data-[state=open]:opacity-100',
          )}
        />
        <Dialog.Content
          aria-label="Dry run results"
          className={clsx(
            'fixed z-50 left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2',
            'rounded-lg shadow-lg p-6 w-full max-w-lg max-h-[80vh] overflow-y-auto',
            'bg-ui-modal-bg',
            'transition-all duration-300 ease-in-out',
            'data-[state=closed]:opacity-0 data-[state=closed]:scale-95',
            'data-[state=open]:opacity-100 data-[state=open]:scale-100',
          )}
        >
          <Dialog.Title className="text-lg font-semibold text-text-primary mb-4 flex items-center gap-2">
            {result.valid ? (
              <>
                <CheckCircledIcon className="h-5 w-5 text-green-500" />
                Dry run passed
              </>
            ) : (
              <>
                <CrossCircledIcon className="h-5 w-5 text-red-500" />
                Dry run failed
              </>
            )}
          </Dialog.Title>

          {/* Errors */}
          {result.errors.length > 0 && (
            <div className="mb-4 p-3 bg-red-500/10 border border-red-500/20 rounded-md">
              <h3 className="text-sm font-medium text-red-400 mb-2">Errors</h3>
              <ul className="space-y-1">
                {result.errors.map((err, i) => (
                  <li
                    key={i}
                    className="text-xs text-red-300 flex items-start gap-1.5"
                  >
                    <CrossCircledIcon className="h-3 w-3 mt-0.5 flex-shrink-0" />
                    <span>{err}</span>
                  </li>
                ))}
              </ul>
            </div>
          )}

          {/* Steps */}
          {result.steps.length > 0 && (
            <div className="mb-4">
              <h3 className="text-sm font-medium text-text-primary mb-2">
                Steps ({result.steps.length})
              </h3>
              <div className="space-y-2">
                {result.steps.map((step, i) => (
                  <div
                    key={i}
                    className="p-2.5 bg-ui-element-bg/50 border border-ui-border rounded-md"
                  >
                    <div className="text-sm font-medium text-text-primary">
                      {step.name}
                    </div>
                    <div className="mt-1 grid grid-cols-2 gap-x-4 gap-y-0.5">
                      <div className="text-xs text-text-muted">
                        <span className="font-medium">Agent:</span>{' '}
                        <span className="text-text-secondary">{step.agent}</span>
                      </div>
                      {step.depends_on.length > 0 && (
                        <div className="text-xs text-text-muted">
                          <span className="font-medium">Depends on:</span>{' '}
                          <span className="text-text-secondary">
                            {step.depends_on.join(', ')}
                          </span>
                        </div>
                      )}
                      {step.tools.length > 0 && (
                        <div className="text-xs text-text-muted col-span-2">
                          <span className="font-medium">Tools:</span>{' '}
                          <span className="text-text-secondary">
                            {step.tools.join(', ')}
                          </span>
                        </div>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Parameters */}
          {result.parameters.length > 0 && (
            <div className="mb-4">
              <h3 className="text-sm font-medium text-text-primary mb-2">
                Parameters ({result.parameters.length})
              </h3>
              <div className="space-y-1">
                {result.parameters.map((param, i) => (
                  <div
                    key={i}
                    className="flex items-center gap-2 text-xs text-text-secondary"
                  >
                    <span className="font-mono font-medium">{param.name}</span>
                    {param.required && (
                      <span className="px-1 py-0.5 bg-amber-500/10 text-amber-500 rounded text-[10px] font-medium">
                        required
                      </span>
                    )}
                    {param.description && (
                      <span className="text-text-muted">
                        — {param.description}
                      </span>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}

          <Dialog.Close asChild>
            <button
              className="absolute top-4 right-4 p-1 rounded-full text-text-muted hover:text-text-secondary transition-colors focus-visible:outline-2 focus-visible:outline-brand-primary"
              aria-label="Close"
            >
              <Cross2Icon className="h-4 w-4" />
            </button>
          </Dialog.Close>
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  );
};
