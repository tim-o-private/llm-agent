import React from 'react';
import { Badge as RadixBadge } from '@radix-ui/themes';
import { clsx } from 'clsx';

export interface BadgeProps extends React.ComponentProps<typeof RadixBadge> {
  variant?: 'solid' | 'soft' | 'surface' | 'outline';
  size?: '1' | '2' | '3';
  color?: 'gray' | 'gold' | 'bronze' | 'brown' | 'yellow' | 'amber' | 'orange' | 'tomato' | 'red' | 'crimson' | 'pink' | 'plum' | 'purple' | 'violet' | 'iris' | 'indigo' | 'blue' | 'cyan' | 'teal' | 'jade' | 'green' | 'grass' | 'lime' | 'mint' | 'sky';
}

export const Badge = React.forwardRef<HTMLSpanElement, BadgeProps>(
  ({ variant = 'soft', size = '2', className, children, ...props }, ref) => {
    return (
      <RadixBadge
        ref={ref}
        variant={variant}
        size={size}
        className={clsx(className)}
        {...props}
      >
        {children}
      </RadixBadge>
    );
  }
);

Badge.displayName = 'Badge'; 