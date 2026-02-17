import React from 'react';
import { Flex } from '@radix-ui/themes';
import { Button } from '@/components/ui/Button';

export interface DialogAction {
  label: string;
  onClick: () => void;
  variant?: 'classic' | 'solid' | 'soft' | 'surface' | 'outline' | 'ghost';
  color?:
    | 'gray'
    | 'gold'
    | 'bronze'
    | 'brown'
    | 'yellow'
    | 'amber'
    | 'orange'
    | 'tomato'
    | 'red'
    | 'crimson'
    | 'pink'
    | 'plum'
    | 'purple'
    | 'violet'
    | 'iris'
    | 'indigo'
    | 'blue'
    | 'cyan'
    | 'teal'
    | 'jade'
    | 'green'
    | 'grass'
    | 'lime'
    | 'mint'
    | 'sky';
  disabled?: boolean;
  loading?: boolean;
  type?: 'button' | 'submit';
}

interface DialogActionBarProps {
  actions: DialogAction[];
  align?: 'start' | 'center' | 'end';
  gap?: '1' | '2' | '3' | '4' | '5';
  className?: string;
}

export const DialogActionBar: React.FC<DialogActionBarProps> = ({ actions, align = 'end', gap = '3', className }) => {
  return (
    <Flex gap={gap} justify={align} className={className}>
      {actions.map((action, index) => (
        <Button
          key={index}
          variant={action.variant || 'solid'}
          color={action.color}
          disabled={action.disabled || action.loading}
          type={action.type || 'button'}
          onClick={action.onClick}
        >
          {action.loading ? 'Loading...' : action.label}
        </Button>
      ))}
    </Flex>
  );
};

export default DialogActionBar;
