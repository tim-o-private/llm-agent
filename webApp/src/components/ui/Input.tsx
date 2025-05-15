import React from 'react';
import { clsx } from 'clsx';

export interface InputProps extends React.InputHTMLAttributes<HTMLInputElement> {}

export const Input = React.forwardRef<HTMLInputElement, InputProps>(
  ({ className, ...props }, ref) => (
    <input
      ref={ref}
      className={clsx(
        'block w-full rounded-md border border-ui-border px-3 py-2 text-text-primary shadow-sm focus:border-brand-primary focus:ring-brand-primary focus:outline-none',
        className
      )}
      {...props}
    />
  )
);
Input.displayName = 'Input'; 