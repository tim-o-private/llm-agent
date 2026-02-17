import React from 'react';
import * as RadixCheckbox from '@radix-ui/react-checkbox'; // Import Radix Checkbox
import { CheckIcon } from '@heroicons/react/16/solid'; // Keep Heroicons for the check mark
import clsx from 'clsx';
import { getFocusClasses } from '@/utils/focusStates';

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

export const Checkbox: React.FC<CheckboxProps> = ({
  checked,
  onCheckedChange,
  id,
  name,
  value,
  disabled = false,
  srLabel = 'Checkbox',
  className,
}) => {
  return (
    <RadixCheckbox.Root
      id={id}
      checked={checked}
      onCheckedChange={onCheckedChange}
      disabled={disabled}
      name={name}
      value={value}
      aria-label={srLabel}
      className={clsx(
        'group flex items-center justify-center size-5 rounded border focus:outline-none',
        'data-[disabled]:cursor-not-allowed data-[disabled]:opacity-60',
        // Apply styles based on Radix's data-state attribute and semantic tokens
        'data-[state=checked]:bg-brand-primary data-[state=checked]:border-transparent',
        'bg-ui-element-bg border-ui-border', // Unchecked state
        // Use our consistent focus system
        !disabled && getFocusClasses(),
        className,
      )}
    >
      <RadixCheckbox.Indicator className="flex items-center justify-center w-full h-full">
        <CheckIcon
          className={clsx(
            'size-4 fill-white', // Icon is always white, ensure brand-primary is dark enough
          )}
        />
      </RadixCheckbox.Indicator>
    </RadixCheckbox.Root>
  );
};

// Make sure to export it from web/packages/ui/src/index.ts if not already handled by `export *`
