import * as Dialog from '@radix-ui/react-dialog';
import React from 'react';
import { clsx } from 'clsx';

export interface ModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  title?: string;
  description?: string;
  children: React.ReactNode;
}

export const Modal: React.FC<ModalProps> = ({ open, onOpenChange, title, description, children }) => (
  <Dialog.Root open={open} onOpenChange={onOpenChange}>
    <Dialog.Portal>
      <Dialog.Overlay className="fixed inset-0 bg-black/40 z-40" />
      <Dialog.Content className={clsx(
        'fixed z-50 left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2',
        'bg-white dark:bg-gray-900 rounded-lg shadow-lg p-6 w-full max-w-md'
      )}>
        {title && <Dialog.Title className="text-lg font-bold mb-2">{title}</Dialog.Title>}
        {description && <Dialog.Description className="mb-4 text-gray-500">{description}</Dialog.Description>}
        {children}
        <Dialog.Close asChild>
          <button className="absolute top-2 right-2 text-gray-400 hover:text-gray-700 dark:hover:text-gray-200" aria-label="Close">✕</button>
        </Dialog.Close>
      </Dialog.Content>
    </Dialog.Portal>
  </Dialog.Root>
); 