import React from 'react';
import * as RadixCheckbox from '@radix-ui/react-checkbox'; // Import Radix Checkbox
import { CheckIcon } from '@heroicons/react/16/solid'; // Keep Heroicons for the check mark
import clsx from 'clsx';

export interface CheckboxProps {
  checked: RadixCheckbox.CheckboxProps['checked']; // Use Radix's checked type
  onCheckedChange: RadixCheckbox.CheckboxProps['onCheckedChange']; // Use Radix's onCheckedChange
  id?: string; // id is useful for associating with a <label>
  name?: string;
  value?: string;
  disabled?: boolean;
  srLabel?: string; // Screen reader label, can be applied as aria-label if no visible label
  className?: string; // For the RadixCheckbox.Root element for positioning/sizing
  // Add any other props you might need
}

export const Checkbox: React.FC<CheckboxProps> = (
  {
    checked,
    onCheckedChange,
    id,
    name,
    value,
    disabled = false,
    srLabel = 'Checkbox',
    className,
  }
) => {
  return (
    <RadixCheckbox.Root
      id={id}
      checked={checked}
      onCheckedChange={onCheckedChange}
      disabled={disabled}
      name={name}
      value={value}
      aria-label={srLabel} // Apply srLabel as aria-label directly on the root
      className={clsx(
        'group flex items-center justify-center size-5 rounded border focus:outline-none',
        'data-[disabled]:cursor-not-allowed data-[disabled]:opacity-60',
        // Apply styles based on Radix's data-state attribute
        'data-[state=checked]:bg-indigo-600 data-[state=checked]:border-transparent dark:data-[state=checked]:bg-indigo-500',
        'bg-white border-gray-400 dark:bg-gray-700 dark:border-gray-500',
        'focus-visible:ring-2 focus-visible:ring-indigo-500 focus-visible:ring-offset-2 dark:focus-visible:ring-offset-gray-800',
        className
      )}
    >
      <RadixCheckbox.Indicator className="flex items-center justify-center w-full h-full">
        <CheckIcon 
          className={clsx(
              'size-4 fill-white' // Icon is always present in Indicator, visibility controlled by Radix
          )}
        />
      </RadixCheckbox.Indicator>
    </RadixCheckbox.Root>
  );
};

// Make sure to export it from web/packages/ui/src/index.ts if not already handled by `export *` 