/**
 * SPEC-048 AC-11: Validation status indicator.
 *
 * Three states: Valid (green check), Invalid (red X + tooltip), Checking (spinner).
 * Validation runs debounced 800ms after editor change.
 */

import React, { useEffect, useState, useRef, useCallback } from 'react';
import { CheckIcon, Cross2Icon } from '@radix-ui/react-icons';
import * as Tooltip from '@radix-ui/react-tooltip';
import {
  validateWorkflowTemplate,
  type ValidationResult,
} from '@/lib/validateWorkflowTemplate';

export type ValidationState = 'valid' | 'invalid' | 'checking';

interface ValidationStatusProps {
  /** Current editor content to validate */
  content: string;
  /** Callback when validation completes */
  onValidationChange?: (result: ValidationResult) => void;
}

export const ValidationStatus: React.FC<ValidationStatusProps> = ({
  content,
  onValidationChange,
}) => {
  const [state, setState] = useState<ValidationState>('checking');
  const [errors, setErrors] = useState<string[]>([]);
  const debounceRef = useRef<ReturnType<typeof setTimeout>>();
  const onValidationChangeRef = useRef(onValidationChange);

  useEffect(() => {
    onValidationChangeRef.current = onValidationChange;
  }, [onValidationChange]);

  const runValidation = useCallback((text: string) => {
    const result = validateWorkflowTemplate(text);
    setState(result.valid ? 'valid' : 'invalid');
    setErrors(result.errors);
    onValidationChangeRef.current?.(result);
  }, []);

  useEffect(() => {
    setState('checking');

    if (debounceRef.current) {
      clearTimeout(debounceRef.current);
    }

    debounceRef.current = setTimeout(() => {
      runValidation(content);
    }, 800);

    return () => {
      if (debounceRef.current) {
        clearTimeout(debounceRef.current);
      }
    };
  }, [content, runValidation]);

  if (state === 'checking') {
    return (
      <span
        data-testid="validation-checking"
        className="inline-flex items-center gap-1.5 text-xs font-medium text-text-muted"
      >
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
        Checking...
      </span>
    );
  }

  if (state === 'valid') {
    return (
      <span
        data-testid="validation-valid"
        className="inline-flex items-center gap-1 text-xs font-medium text-green-600 dark:text-green-400"
      >
        <CheckIcon className="h-3.5 w-3.5" />
        Valid
      </span>
    );
  }

  // Invalid -- show with tooltip listing errors
  return (
    <Tooltip.Provider delayDuration={200}>
      <Tooltip.Root>
        <Tooltip.Trigger asChild>
          <span
            data-testid="validation-invalid"
            className="inline-flex items-center gap-1 text-xs font-medium text-red-600 dark:text-red-400 cursor-help"
          >
            <Cross2Icon className="h-3.5 w-3.5" />
            Invalid
          </span>
        </Tooltip.Trigger>
        <Tooltip.Portal>
          <Tooltip.Content
            side="bottom"
            sideOffset={4}
            className="z-50 max-w-xs rounded-md bg-ui-element-bg border border-ui-border px-3 py-2 text-xs text-text-secondary shadow-md"
          >
            <ul className="space-y-1">
              {errors.map((err, i) => (
                <li key={i} className="flex items-start gap-1.5">
                  <Cross2Icon className="h-3 w-3 text-red-500 mt-0.5 flex-shrink-0" />
                  <span>{err}</span>
                </li>
              ))}
            </ul>
            <Tooltip.Arrow className="fill-ui-element-bg" />
          </Tooltip.Content>
        </Tooltip.Portal>
      </Tooltip.Root>
    </Tooltip.Provider>
  );
};
