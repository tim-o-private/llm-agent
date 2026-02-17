/**
 * @docs memory-bank/patterns/ui-patterns.md#pattern-1-radix-themes-primitives-tailwind
 * @rules memory-bank/rules/ui-rules.json#ui-002
 * @examples memory-bank/patterns/ui-patterns.md#pattern-3-button-variants
 */
import React from 'react';
import { Button as RadixButton } from '@radix-ui/themes';
import { clsx } from 'clsx';
import { getFocusClasses } from '@/utils/focusStates';

export interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  asChild?: boolean;
  variant?: 'classic' | 'solid' | 'soft' | 'surface' | 'outline' | 'ghost';
  size?: '1' | '2' | '3' | '4';
  color?:
    | 'gray'
    | 'gold'
    | 'bronze'
    | 'brown'
    | 'yellow'
    | 'amber'
    | 'orange'
    | 'tomato'
    | 'red'
    | 'crimson'
    | 'pink'
    | 'plum'
    | 'purple'
    | 'violet'
    | 'iris'
    | 'indigo'
    | 'blue'
    | 'cyan'
    | 'teal'
    | 'jade'
    | 'green'
    | 'grass'
    | 'lime'
    | 'mint'
    | 'sky';
}

export const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  ({ asChild = false, variant = 'solid', size = '2', className, disabled, children, ...props }, ref) => {
    return (
      <RadixButton
        ref={ref}
        variant={variant}
        size={size}
        disabled={disabled}
        asChild={asChild}
        className={clsx(
          // Override Radix focus styles with our global focus system
          '[&]:focus:outline-none [&]:focus-visible:outline-none',
          !disabled && getFocusClasses(),
          className,
        )}
        {...props}
      >
        {asChild ? children : <span>{children}</span>}
      </RadixButton>
    );
  },
);

Button.displayName = 'Button';
