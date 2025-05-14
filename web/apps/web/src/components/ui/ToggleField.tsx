import React from 'react';
import * as RadixSwitch from '@radix-ui/react-switch'; // Import Radix Switch
import clsx from 'clsx';

interface ToggleFieldProps {
  id?: string; // Recommended for associating label
  label: string;
  checked: boolean;
  onCheckedChange: (checked: boolean) => void; // Changed from onChange to onCheckedChange
  disabled?: boolean;
  srLabel?: string; // Screen reader label for the switch itself if no visible label
  description?: string;
  className?: string; // For the container div
}

const ToggleField: React.FC<ToggleFieldProps> = ({
  id,
  label,
  checked,
  onCheckedChange,
  disabled = false,
  srLabel, // If an id is provided and connected to a <label htmlFor={id}>, srLabel on Switch might be redundant.
  description,
  className,
}) => {
  const internalId = id || React.useId(); // Generate id if not provided

  return (
    <div className={clsx("flex items-center justify-between", disabled && "opacity-50", className)}>
      <span className="flex flex-col mr-3"> {/* Added mr-3 for spacing */}
        <label htmlFor={internalId} className="text-sm font-medium text-gray-900 dark:text-gray-100 cursor-pointer">
          {label}
        </label>
        {description && (
          <span id={`${internalId}-description`} className="text-xs text-gray-500 dark:text-gray-400">
            {description}
          </span>
        )}
      </span>
      <RadixSwitch.Root
        id={internalId}
        checked={checked}
        onCheckedChange={onCheckedChange}
        disabled={disabled}
        aria-label={srLabel} // Use srLabel if provided, especially if no <label htmlFor>
        aria-describedby={description ? `${internalId}-description` : undefined}
        className={clsx(
          'group relative inline-flex h-6 w-11 flex-shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors duration-200 ease-in-out focus:outline-none focus-visible:ring-2 focus-visible:ring-indigo-500 focus-visible:ring-offset-2 dark:focus-visible:ring-offset-gray-800',
          'data-[state=checked]:bg-indigo-600',
          'data-[state=unchecked]:bg-gray-200 dark:data-[state=unchecked]:bg-gray-700',
          'data-[disabled]:cursor-not-allowed data-[disabled]:opacity-70' // Adjusted opacity for disabled
        )}
      >
        <RadixSwitch.Thumb
          className={clsx(
            'pointer-events-none inline-block h-5 w-5 transform rounded-full bg-white shadow ring-0 transition duration-200 ease-in-out',
            'data-[state=checked]:translate-x-5',
            'data-[state=unchecked]:translate-x-0'
          )}
        />
      </RadixSwitch.Root>
    </div>
  );
};

export default ToggleField; 