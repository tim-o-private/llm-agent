import React from 'react';
import { Button, ButtonProps } from './Button';
import { clsx } from 'clsx';

export interface IconButtonProps extends Omit<ButtonProps, 'asChild'> {
  variant?: 'ghost' | 'soft' | 'surface' | 'outline';
  size?: '1' | '2' | '3';
  children: React.ReactNode;
}

export const IconButton = React.forwardRef<HTMLButtonElement, IconButtonProps>(
  ({ variant = 'ghost', size = '2', className, children, ...props }, ref) => {
    return (
      <Button
        ref={ref}
        variant={variant}
        size={size}
        className={clsx(
          // Make it square for icons
          'aspect-square',
          className,
        )}
        {...props}
      >
        {children}
      </Button>
    );
  },
);

IconButton.displayName = 'IconButton';
