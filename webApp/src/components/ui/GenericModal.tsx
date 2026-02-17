import React, { useCallback, useEffect } from 'react';
import * as Dialog from '@radix-ui/react-dialog';
import { Cross2Icon } from '@radix-ui/react-icons';
import { useTaskViewStore } from '@/stores/useTaskViewStore';
import { clsx } from 'clsx';

interface GenericModalProps {
  // Core modal props
  isOpen: boolean;
  onOpenChange: (open: boolean) => void;
  children: React.ReactNode;

  // Content props
  title?: string;
  description?: string;

  // Behavior props
  isDirty?: boolean;
  modalId?: string; // For focus management

  // Styling props
  size?: 'sm' | 'md' | 'lg' | 'xl';
  className?: string;

  // Loading/error states
  isLoading?: boolean;
  error?: string | Error | null;
  loadingMessage?: string;
}

const sizeClasses = {
  sm: 'max-w-md',
  md: 'max-w-lg',
  lg: 'max-w-2xl',
  xl: 'max-w-4xl',
};

export const GenericModal: React.FC<GenericModalProps> = ({
  isOpen,
  onOpenChange,
  children,
  title,
  description,
  isDirty = false,
  modalId = 'generic-modal',
  size = 'md',
  className,
  isLoading = false,
  error = null,
  loadingMessage = 'Loading...',
}) => {
  const setModalOpenState = useTaskViewStore((state) => state.setModalOpenState);

  // Handle dirty state confirmation
  const wrappedOnOpenChange = useCallback(
    (open: boolean) => {
      if (!open && isDirty) {
        if (window.confirm('You have unsaved changes. Are you sure you want to discard them?')) {
          onOpenChange(false);
        } else {
          return; // Prevent closing if user cancels discard
        }
      } else {
        onOpenChange(open);
      }
    },
    [isDirty, onOpenChange],
  );

  // Register modal state for keyboard shortcut management
  useEffect(() => {
    setModalOpenState(modalId, isOpen);
    return () => {
      setModalOpenState(modalId, false);
    };
  }, [isOpen, modalId, setModalOpenState]);

  return (
    <Dialog.Root open={isOpen} onOpenChange={wrappedOnOpenChange}>
      <Dialog.Portal>
        <Dialog.Overlay className="fixed inset-0 bg-black/50 data-[state=open]:animate-overlayShow" />
        <Dialog.Content
          className={clsx(
            'fixed top-1/2 left-1/2 w-[90vw] max-h-[85vh] -translate-x-1/2 -translate-y-1/2',
            'rounded-lg bg-ui-modal-bg p-6 shadow-lg',
            'data-[state=open]:animate-contentShow focus:outline-none',
            'flex flex-col',
            sizeClasses[size],
            className,
          )}
        >
          {/* Header */}
          {(title || description) && (
            <div className="mb-4">
              {title && <Dialog.Title className="text-xl font-semibold text-text-primary mb-1">{title}</Dialog.Title>}
              {description && (
                <Dialog.Description className="text-sm text-text-muted">{description}</Dialog.Description>
              )}
            </div>
          )}

          {/* Content */}
          <div className="flex-grow overflow-y-auto pr-2 custom-scrollbar">
            {isLoading ? (
              <div className="flex items-center justify-center h-40">
                <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-ui-border"></div>
                <p className="ml-2 text-text-muted">{loadingMessage}</p>
              </div>
            ) : error ? (
              <div className="text-destructive p-4 text-center">
                Error: {typeof error === 'string' ? error : error.message || 'Unknown error'}
              </div>
            ) : (
              children
            )}
          </div>

          {/* Close button */}
          <Dialog.Close asChild>
            <button
              className="absolute top-3.5 right-3.5 inline-flex h-6 w-6 appearance-none items-center justify-center rounded-full text-text-muted hover:bg-ui-interactive-bg-hover"
              aria-label="Close"
              type="button"
            >
              <Cross2Icon />
            </button>
          </Dialog.Close>
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  );
};

export default GenericModal;
