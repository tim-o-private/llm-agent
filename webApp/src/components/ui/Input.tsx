import React from 'react';
import { clsx } from 'clsx';
import { useTaskViewStore } from '@/stores/useTaskViewStore';

export type InputProps = React.InputHTMLAttributes<HTMLInputElement>;

export const Input = React.forwardRef<HTMLInputElement, InputProps>(
  ({ className, onFocus:_onFocus, onBlur: _onBlur, ...props }, ref) => {
    const setInputFocusState = useTaskViewStore((state) => state.setInputFocusState);

    const handleFocus = (event: React.FocusEvent<HTMLInputElement>) => {
      setInputFocusState(true);
      if (_onFocus) {
        _onFocus(event);
      }
    };

    const handleBlur = (event: React.FocusEvent<HTMLInputElement>) => {
      setInputFocusState(false);
      if (_onBlur) {
        _onBlur(event);
      }
    };

    return (
      <input
        ref={ref}
        className={clsx(
          'block w-full rounded-md border border-ui-border px-3 py-2 text-text-primary shadow-sm focus:border-brand-primary focus:ring-brand-primary focus:outline-none',
          className
        )}
        onFocus={handleFocus}
        onBlur={handleBlur}
        {...props}
      />
    );
  }
);
Input.displayName = 'Input'; 