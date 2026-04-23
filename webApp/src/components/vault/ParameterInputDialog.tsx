/**
 * SPEC-048 AC-16: Parameter input dialog for "Run now".
 *
 * Lists required params with text inputs, optional params with defaults pre-filled.
 * "Run" and "Cancel" buttons. Uses Radix Dialog.
 */

import React, { useState, useCallback, useEffect } from 'react';
import * as Dialog from '@radix-ui/react-dialog';
import { Cross2Icon } from '@radix-ui/react-icons';
import { clsx } from 'clsx';
import type { DryRunParameter } from '@/api/types/workflowEditor';

interface ParameterInputDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  parameters: DryRunParameter[];
  /** Called when user confirms; receives parameter values */
  onRun: (values: Record<string, string>) => void;
  isRunning: boolean;
}

export const ParameterInputDialog: React.FC<ParameterInputDialogProps> = ({
  open,
  onOpenChange,
  parameters,
  onRun,
  isRunning,
}) => {
  const [values, setValues] = useState<Record<string, string>>({});

  // Reset values when dialog opens with new parameters
  useEffect(() => {
    if (open) {
      const initial: Record<string, string> = {};
      for (const param of parameters) {
        initial[param.name] = '';
      }
      setValues(initial);
    }
  }, [open, parameters]);

  const handleChange = useCallback((name: string, value: string) => {
    setValues((prev) => ({ ...prev, [name]: value }));
  }, []);

  const handleSubmit = useCallback(
    (e: React.FormEvent) => {
      e.preventDefault();
      // Filter out empty optional params
      const filtered: Record<string, string> = {};
      for (const param of parameters) {
        const val = values[param.name]?.trim();
        if (val) {
          filtered[param.name] = val;
        }
      }
      onRun(filtered);
    },
    [parameters, values, onRun],
  );

  const requiredParams = parameters.filter((p) => p.required);
  const optionalParams = parameters.filter((p) => !p.required);

  // Check if all required params have values
  const allRequiredFilled = requiredParams.every(
    (p) => values[p.name]?.trim(),
  );

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
          aria-label="Workflow parameters"
          className={clsx(
            'fixed z-50 left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2',
            'rounded-lg shadow-lg p-6 w-full max-w-md max-h-[80vh] overflow-y-auto',
            'bg-ui-modal-bg',
            'transition-all duration-300 ease-in-out',
            'data-[state=closed]:opacity-0 data-[state=closed]:scale-95',
            'data-[state=open]:opacity-100 data-[state=open]:scale-100',
          )}
        >
          <Dialog.Title className="text-lg font-semibold text-text-primary mb-1">
            Workflow Parameters
          </Dialog.Title>
          <Dialog.Description className="text-sm text-text-secondary mb-4">
            Enter values for workflow parameters before running.
          </Dialog.Description>

          <form onSubmit={handleSubmit}>
            {/* Required parameters */}
            {requiredParams.length > 0 && (
              <div className="mb-4">
                <h3 className="text-xs font-semibold text-text-muted uppercase tracking-wider mb-2">
                  Required
                </h3>
                <div className="space-y-3">
                  {requiredParams.map((param) => (
                    <div key={param.name}>
                      <label className="block text-sm font-medium text-text-primary mb-1">
                        {param.name}
                        {param.description && (
                          <span className="ml-1 text-xs font-normal text-text-muted">
                            — {param.description}
                          </span>
                        )}
                      </label>
                      <input
                        type="text"
                        required
                        value={values[param.name] ?? ''}
                        onChange={(e) =>
                          handleChange(param.name, e.target.value)
                        }
                        className="w-full px-3 py-1.5 text-sm rounded-md border border-ui-border bg-ui-element-bg text-text-primary placeholder:text-text-muted focus:outline-2 focus:outline-brand-primary"
                        placeholder={`Enter ${param.name}`}
                      />
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Optional parameters */}
            {optionalParams.length > 0 && (
              <div className="mb-4">
                <h3 className="text-xs font-semibold text-text-muted uppercase tracking-wider mb-2">
                  Optional
                </h3>
                <div className="space-y-3">
                  {optionalParams.map((param) => (
                    <div key={param.name}>
                      <label className="block text-sm font-medium text-text-primary mb-1">
                        {param.name}
                        {param.description && (
                          <span className="ml-1 text-xs font-normal text-text-muted">
                            — {param.description}
                          </span>
                        )}
                      </label>
                      <input
                        type="text"
                        value={values[param.name] ?? ''}
                        onChange={(e) =>
                          handleChange(param.name, e.target.value)
                        }
                        className="w-full px-3 py-1.5 text-sm rounded-md border border-ui-border bg-ui-element-bg text-text-primary placeholder:text-text-muted focus:outline-2 focus:outline-brand-primary"
                        placeholder={`Enter ${param.name} (optional)`}
                      />
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Action buttons */}
            <div className="flex gap-3 justify-end mt-6">
              <Dialog.Close asChild>
                <button
                  type="button"
                  className="px-3 py-1.5 text-sm rounded-md text-text-primary bg-ui-element-bg border border-ui-border hover:bg-ui-interactive-bg-hover transition-colors"
                >
                  Cancel
                </button>
              </Dialog.Close>
              <button
                type="submit"
                disabled={!allRequiredFilled || isRunning}
                className="px-3 py-1.5 text-sm font-medium rounded-md text-white bg-brand-primary hover:bg-brand-primary/90 disabled:opacity-50 disabled:cursor-not-allowed transition-colors inline-flex items-center gap-1.5"
              >
                {isRunning && (
                  <svg
                    className="h-3.5 w-3.5 animate-spin"
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
                )}
                Run
              </button>
            </div>
          </form>

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
