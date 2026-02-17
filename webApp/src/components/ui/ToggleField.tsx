import React from 'react';
import { Switch } from '@radix-ui/react-switch';
import clsx from 'clsx';
import { getFocusClasses } from '@/utils/focusStates';

interface ToggleFieldProps {
  id: string;
  label: string;
  checked: boolean;
  onChange: (checked: boolean) => void;
  disabled?: boolean;
  description?: string;
}

export const ToggleField: React.FC<ToggleFieldProps> = ({
  id,
  label,
  checked,
  onChange,
  disabled = false,
  description,
}) => {
  return (
    <div className="flex items-center justify-between">
      <div className="flex flex-col">
        <label htmlFor={id} className="text-sm font-medium text-text-primary">
          {label}
        </label>
        {description && <p className="text-sm text-text-secondary">{description}</p>}
      </div>
      <Switch
        id={id}
        checked={checked}
        onCheckedChange={onChange}
        disabled={disabled}
        className={clsx(
          'group relative inline-flex h-6 w-11 flex-shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors duration-200 ease-in-out',
          'data-[state=checked]:bg-brand-primary data-[state=unchecked]:bg-ui-border',
          'disabled:cursor-not-allowed disabled:opacity-50',
          // Use our consistent focus system
          !disabled && getFocusClasses(),
        )}
      >
        <span
          className={clsx(
            'pointer-events-none inline-block h-5 w-5 transform rounded-full bg-white shadow ring-0 transition duration-200 ease-in-out',
            'group-data-[state=checked]:translate-x-5 group-data-[state=unchecked]:translate-x-0',
          )}
        />
      </Switch>
    </div>
  );
};
