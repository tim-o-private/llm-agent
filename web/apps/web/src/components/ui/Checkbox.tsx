import React from 'react';
import { Checkbox as HeadlessCheckbox } from '@headlessui/react'; // Renamed to avoid conflict with component name
import { CheckIcon } from '@heroicons/react/16/solid';
import clsx from 'clsx';

export interface CheckboxProps {
  checked: boolean;
  onChange: (checked: boolean) => void;
  name?: string;
  value?: string; // Optional, if needed for form submissions
  disabled?: boolean;
  srLabel?: string; // Screen reader label, helpful if no visible label is associated
  className?: string; // For the outer container/positioning
  // Add any other props you might need, e.g., for specific styling variants if not covered by className
}

export const Checkbox: React.FC<CheckboxProps> = (
  {
    checked,
    onChange,
    name,
    value,
    disabled = false,
    srLabel = 'Checkbox',
    className,
  }
) => {
  return (
    <HeadlessCheckbox
      checked={checked}
      onChange={onChange}
      disabled={disabled}
      name={name}
      value={value}      
      className={clsx(
        'group inline-block size-5 rounded border focus:outline-none data-[disabled]:cursor-not-allowed data-[disabled]:opacity-60',
        'data-[checked]:bg-indigo-600 data-[checked]:border-transparent dark:data-[checked]:bg-indigo-500',
        'bg-white border-gray-400 dark:bg-gray-700 dark:border-gray-500',
        'focus-visible:ring-2 focus-visible:ring-indigo-500 focus-visible:ring-offset-2 dark:focus-visible:ring-offset-gray-800',
        className // Allows for additional classes to be passed for positioning/sizing etc.
      )}
    >
      {/* Screen reader label if provided and useful */}
      {/* The Headless UI Checkbox itself is a span, so srLabel can be handled by parent <label> or here for standalone cases */}
      <span className="sr-only">{srLabel}</span>
      
      {/* Checkmark icon - visibility controlled by Headless UI state via group-data-checked */}
      <CheckIcon 
        className={clsx(
            'hidden size-4 fill-white group-data-[checked]:block mx-auto my-auto',
            // If you want the checkmark color to be different from the background in some themes:
            // checked ? 'text-white' : 'text-transparent' // Example for explicit color control
        )}
      />
    </HeadlessCheckbox>
  );
};

// Make sure to export it from web/packages/ui/src/index.ts if not already handled by `export *` 