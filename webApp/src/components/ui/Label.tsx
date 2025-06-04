import React from 'react';
import { clsx } from 'clsx';

export type LabelProps = React.LabelHTMLAttributes<HTMLLabelElement>;

export const Label: React.FC<LabelProps> = ({ className, ...props }) => (
  <label
    className={clsx('block text-sm font-medium text-text-secondary mb-1', className)}
    {...props}
  />
); 