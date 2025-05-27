/**
 * @docs memory-bank/patterns/ui-patterns.md#pattern-1-radix-themes-primitives-tailwind
 * @rules memory-bank/rules/ui-rules.json#ui-001
 * @examples memory-bank/patterns/ui-patterns.md#pattern-4-modal-dialogs
 */
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
      <Dialog.Overlay 
        className={clsx(
          "fixed inset-0 bg-black/40 z-40",
          "transition-opacity duration-300 ease-in-out",
          "data-[state=closed]:opacity-0 data-[state=open]:opacity-100"
        )}
      />
      <Dialog.Content 
        className={clsx(
          'fixed z-50 left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2',
          'rounded-lg shadow-lg p-6 w-full max-w-md',
          'bg-ui-modal-bg',
          "transition-all duration-300 ease-in-out",
          "data-[state=closed]:opacity-0 data-[state=closed]:scale-95",
          "data-[state=open]:opacity-100 data-[state=open]:scale-100"
        )}
      >
        {title && <Dialog.Title className="text-lg font-bold mb-2 text-text-primary">{title}</Dialog.Title>}
        {description && <Dialog.Description className="mb-4 text-text-secondary">{description}</Dialog.Description>}
        {children}
        <Dialog.Close asChild>
          <button 
            className="absolute top-3 right-3 p-1 rounded-full text-text-muted hover:text-text-secondary focus:outline-none focus:ring-2 focus:ring-ui-border-focus focus:ring-offset-2 focus:ring-offset-ui-element-bg transition-colors"
            aria-label="Close"
          >
            ✕
          </button>
        </Dialog.Close>
      </Dialog.Content>
    </Dialog.Portal>
  </Dialog.Root>
); 