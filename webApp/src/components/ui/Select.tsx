import React from 'react';
import * as SelectPrimitive from '@radix-ui/react-select';
import { ChevronDownIcon, CheckIcon } from '@radix-ui/react-icons';
import { clsx } from 'clsx';

// Updated Select component using Radix UI primitives for better modal compatibility
export interface SelectProps {
  // Core props
  value?: string;
  defaultValue?: string;
  onValueChange?: (value: string) => void;
  placeholder?: string;
  disabled?: boolean;
  required?: boolean;
  name?: string;
  
  // Styling props
  size?: "1" | "2" | "3";
  variant?: "classic" | "surface" | "soft" | "ghost";
  color?: "ruby" | "gray" | "gold" | "bronze" | "brown" | "yellow" | "amber" | "orange" | "tomato" | "red" | "crimson" | "pink" | "plum" | "purple" | "violet" | "iris" | "indigo" | "blue" | "cyan" | "teal" | "jade" | "green" | "grass" | "lime" | "mint" | "sky";
  radius?: "none" | "small" | "medium" | "large" | "full";
  
  // Layout props
  className?: string;
  children: React.ReactNode;
}

export const Select = React.forwardRef<HTMLButtonElement, SelectProps>(
  ({ 
    // Core props
    value,
    defaultValue,
    onValueChange,
    placeholder,
    disabled,
    required,
    name,
    
    // Styling props
    size = "2",
    variant = "surface",
    color,
    radius,
    
    // Layout props
    className,
    children,
  }, ref) => {
    console.log('Select render:', { value, placeholder, size, variant, color });
    
    // Size-based styling
    const sizeClasses = {
      "1": "h-6 text-xs px-2",
      "2": "h-8 text-sm px-3", 
      "3": "h-10 text-base px-4"
    };
    
    // Variant-based styling
    const variantClasses = {
      "classic": "bg-white border-gray-300 hover:border-gray-400 focus:border-blue-500",
      "surface": "bg-ui-element-bg border-ui-border hover:border-ui-border-hover focus:border-brand-primary",
      "soft": "bg-ui-element-bg/50 border-ui-border/50 hover:bg-ui-element-bg hover:border-ui-border",
      "ghost": "bg-transparent border-transparent hover:bg-ui-element-bg/50"
    };
    
    return (
      <SelectPrimitive.Root 
        value={value}
        defaultValue={defaultValue}
        onValueChange={onValueChange}
        disabled={disabled}
        required={required}
        name={name}
      >
        <SelectPrimitive.Trigger
          ref={ref}
          className={clsx(
            // Base styles
            "flex items-center justify-between rounded-md border transition-colors",
            "focus:outline-none focus:ring-2 focus:ring-brand-primary/20",
            "disabled:opacity-50 disabled:cursor-not-allowed",
            // Size classes
            sizeClasses[size],
            // Variant classes
            variantClasses[variant],
            className
          )}
        >
          <SelectPrimitive.Value placeholder={placeholder} />
          <SelectPrimitive.Icon asChild>
            <ChevronDownIcon className="h-4 w-4 opacity-50" />
          </SelectPrimitive.Icon>
        </SelectPrimitive.Trigger>
        
        <SelectPrimitive.Portal>
          <SelectPrimitive.Content
            className={clsx(
              "relative z-50 min-w-[8rem] overflow-hidden rounded-md border bg-ui-element-bg text-text-primary shadow-md",
              "data-[state=open]:animate-in data-[state=closed]:animate-out",
              "data-[state=closed]:fade-out-0 data-[state=open]:fade-in-0",
              "data-[state=closed]:zoom-out-95 data-[state=open]:zoom-in-95",
              "data-[side=bottom]:slide-in-from-top-2 data-[side=left]:slide-in-from-right-2",
              "data-[side=right]:slide-in-from-left-2 data-[side=top]:slide-in-from-bottom-2"
            )}
            position="popper"
            sideOffset={4}
        >
            <SelectPrimitive.Viewport className="p-1">
          {children}
            </SelectPrimitive.Viewport>
          </SelectPrimitive.Content>
        </SelectPrimitive.Portal>
      </SelectPrimitive.Root>
    );
  }
);

Select.displayName = 'Select';

// Updated SelectItem component
export const SelectItem = React.forwardRef<
  React.ElementRef<typeof SelectPrimitive.Item>,
  React.ComponentPropsWithoutRef<typeof SelectPrimitive.Item>
>(({ className, children, ...props }, ref) => (
  <SelectPrimitive.Item
    ref={ref}
    className={clsx(
      "relative flex w-full cursor-default select-none items-center rounded-sm py-1.5 pl-8 pr-2 text-sm outline-none",
      "focus:bg-ui-interactive-bg-hover focus:text-text-primary",
      "data-[disabled]:pointer-events-none data-[disabled]:opacity-50",
      className
    )}
    {...props}
  >
    <span className="absolute left-2 flex h-3.5 w-3.5 items-center justify-center">
      <SelectPrimitive.ItemIndicator>
        <CheckIcon className="h-4 w-4" />
      </SelectPrimitive.ItemIndicator>
    </span>
    <SelectPrimitive.ItemText>{children}</SelectPrimitive.ItemText>
  </SelectPrimitive.Item>
));
SelectItem.displayName = SelectPrimitive.Item.displayName;

// Export additional components for advanced usage
export const SelectGroup = SelectPrimitive.Group;
export const SelectLabel = React.forwardRef<
  React.ElementRef<typeof SelectPrimitive.Label>,
  React.ComponentPropsWithoutRef<typeof SelectPrimitive.Label>
>(({ className, ...props }, ref) => (
  <SelectPrimitive.Label
    ref={ref}
    className={clsx("py-1.5 pl-8 pr-2 text-sm font-semibold", className)}
    {...props}
  />
));
SelectLabel.displayName = SelectPrimitive.Label.displayName;

export const SelectSeparator = React.forwardRef<
  React.ElementRef<typeof SelectPrimitive.Separator>,
  React.ComponentPropsWithoutRef<typeof SelectPrimitive.Separator>
>(({ className, ...props }, ref) => (
  <SelectPrimitive.Separator
    ref={ref}
    className={clsx("-mx-1 my-1 h-px bg-ui-border", className)}
    {...props}
  />
));
SelectSeparator.displayName = SelectPrimitive.Separator.displayName; 