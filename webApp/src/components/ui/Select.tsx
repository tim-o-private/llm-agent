import React from 'react';
import { Select as RadixSelect } from '@radix-ui/themes';
import { clsx } from 'clsx';
import { getFocusClasses } from '@/utils/focusStates';

export interface SelectProps extends React.ComponentProps<typeof RadixSelect.Root> {
  placeholder?: string;
  children: React.ReactNode;
  className?: string;
}

export const Select = React.forwardRef<HTMLButtonElement, SelectProps>(
  ({ className, disabled, children, placeholder, ...props }, ref) => {
    return (
      <RadixSelect.Root disabled={disabled} {...props}>
        <RadixSelect.Trigger
          ref={ref}
          className={clsx(
            // Override Radix focus styles with our global focus system
            '[&]:focus-within:outline-none [&]:focus:outline-none [&]:focus-visible:outline-none',
            !disabled && getFocusClasses(),
            className
          )}
          placeholder={placeholder}
        />
        <RadixSelect.Content>
          {children}
        </RadixSelect.Content>
      </RadixSelect.Root>
    );
  }
);

Select.displayName = 'Select';

// Export sub-components for easier usage
export const SelectItem = RadixSelect.Item;
export const SelectGroup = RadixSelect.Group;
export const SelectLabel = RadixSelect.Label;
export const SelectSeparator = RadixSelect.Separator; 