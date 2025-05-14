import React, { useState } from 'react';
import { Switch } from '@headlessui/react';
import clsx from 'clsx';

interface ToggleFieldProps {
  label: string;
  checked: boolean;
  onChange: (checked: boolean) => void;
  disabled?: boolean;
  srLabel?: string; // Optional screen-reader only label for the switch itself
  description?: string; // Optional description text below the label
}

const ToggleField: React.FC<ToggleFieldProps> = ({
  label,
  checked,
  onChange,
  disabled = false,
  srLabel,
  description,
}) => {
  return (
    <Switch.Group as="div" className={clsx("flex items-center justify-between", disabled && "opacity-50")}>
      <span className="flex flex-col">
        <Switch.Label as="span" className="text-sm font-medium text-gray-900 dark:text-gray-100" passive>
          {label}
        </Switch.Label>
        {description && (
          <Switch.Description as="span" className="text-xs text-gray-500 dark:text-gray-400">
            {description}
          </Switch.Description>
        )}
      </span>
      <Switch
        checked={checked}
        onChange={onChange}
        disabled={disabled}
        className={clsx(
          'relative inline-flex h-6 w-11 flex-shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors duration-200 ease-in-out focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:ring-offset-2 dark:focus:ring-offset-gray-800',
          checked ? 'bg-indigo-600' : 'bg-gray-200 dark:bg-gray-700',
          disabled && 'cursor-not-allowed'
        )}
      >
        <span className="sr-only">{srLabel || label}</span>
        <span
          aria-hidden="true"
          className={clsx(
            'pointer-events-none inline-block h-5 w-5 transform rounded-full bg-white shadow ring-0 transition duration-200 ease-in-out',
            checked ? 'translate-x-5' : 'translate-x-0'
          )}
        />
      </Switch>
    </Switch.Group>
  );
};

export default ToggleField; 