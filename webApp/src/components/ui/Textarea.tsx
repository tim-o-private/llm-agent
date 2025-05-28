import React from 'react';
import { TextArea } from '@radix-ui/themes';
import { clsx } from 'clsx';
import { getFocusClasses } from '@/utils/focusStates';

export interface TextareaProps extends React.ComponentProps<typeof TextArea> {
  className?: string;
}

export const Textarea = React.forwardRef<HTMLTextAreaElement, TextareaProps>(
  ({ className, disabled, ...props }, ref) => {
    return (
      <TextArea
        ref={ref}
        disabled={disabled}
        className={clsx(
          // Override Radix focus styles with our global focus system
          '[&]:focus-within:outline-none [&]:focus:outline-none [&]:focus-visible:outline-none',
          !disabled && getFocusClasses(),
          className
        )}
        {...props}
      />
    );
  }
);
Textarea.displayName = 'Textarea'; 