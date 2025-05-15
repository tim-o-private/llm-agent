import React from 'react';
import clsx from 'clsx';

interface FABProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  icon: React.ReactNode;
  'aria-label': string;
  tooltip?: string;
  position?: 'bottom-right' | 'bottom-left' | 'top-right' | 'top-left';
  size?: 'sm' | 'md' | 'lg';
}

export const FAB: React.FC<FABProps> = ({
  icon,
  tooltip,
  position = 'bottom-right',
  size = 'md',
  className,
  ...props
}) => {
  const positionClasses = {
    'bottom-right': 'bottom-4 right-4',
    'bottom-left': 'bottom-4 left-4',
    'top-right': 'top-4 right-4',
    'top-left': 'top-4 left-4',
  };

  const sizeClasses = {
    sm: 'p-2 h-10 w-10',
    md: 'p-3 h-12 w-12',
    lg: 'p-4 h-14 w-14',
  };

  const iconSizeClasses = {
    sm: 'h-5 w-5',
    md: 'h-6 w-6',
    lg: 'h-7 w-7',
  }

  return (
    <button
      type="button"
      className={clsx(
        'fixed inline-flex items-center justify-center rounded-full shadow-lg text-brand-primary-text transition-colors focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-offset-ui-bg',
        'bg-brand-primary hover:bg-brand-primary-hover focus:ring-brand-primary', 
        positionClasses[position],
        sizeClasses[size],
        className
      )}
      title={tooltip}
      {...props}
    >
      <span className={clsx(iconSizeClasses[size])}>{icon}</span>
      {tooltip && <span className="sr-only">{tooltip}</span>}
    </button>
  );
}; 