import React from 'react';
import { TextField } from '@radix-ui/themes';
import { clsx } from 'clsx';
import { getFocusClasses } from '@/utils/focusStates';

export interface InputProps extends React.ComponentProps<typeof TextField.Root> {
  error?: boolean;
}

export const Input = React.forwardRef<HTMLInputElement, InputProps>(
  ({ className, error, color, ...props }, ref) => {
    return (
      <TextField.Root
        ref={ref}
        color={error ? 'red' : color}
        className={clsx(
          // Override Radix focus styles with our global focus system
          '[&]:focus-within:outline-none [&_input]:focus:outline-none [&_input]:focus-visible:outline-none',
          getFocusClasses(),
          className
        )}
        {...props}
      />
    );
  }
);

Input.displayName = 'Input'; 