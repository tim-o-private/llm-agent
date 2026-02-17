import React from 'react';
import { clsx } from 'clsx';

interface ErrorMessageProps {
  children: React.ReactNode;
  className?: string;
  id?: string; // For aria-describedby
}

export const ErrorMessage: React.FC<ErrorMessageProps> = ({ children, className, id }) => {
  if (!children) {
    return null;
  }

  return (
    <p role="alert" id={id} className={clsx('text-sm text-text-destructive mt-1', className)}>
      {children}
    </p>
  );
};
