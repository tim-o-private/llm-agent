import React from 'react';
import { clsx } from 'clsx';

export interface CardProps extends React.HTMLAttributes<HTMLDivElement> {
  children: React.ReactNode;
}

export const Card: React.FC<CardProps> = ({ children, className, ...props }) => (
  <div
    className={clsx(
      'bg-white rounded-lg shadow p-6',
      className
    )}
    {...props}
  >
    {children}
  </div>
); 