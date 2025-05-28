import React, { useCallback, useEffect } from 'react';
import * as RadixDialog from '@radix-ui/react-dialog';
import { Cross2Icon } from '@radix-ui/react-icons';
import { useTaskStore, useInitializeTaskStore } from '@/stores/useTaskStore';
import { useTaskViewStore } from '@/stores/useTaskViewStore';
import { Spinner } from '@/components/ui/Spinner';
import { getFocusClasses } from '@/utils/focusStates';
import { clsx } from 'clsx';

interface TaskModalWrapperProps {
  taskId: string | null;
  isOpen: boolean;
  onOpenChange: (open: boolean) => void;
  children: React.ReactNode;
  isDirty?: boolean;
}

export const TaskModalWrapper: React.FC<TaskModalWrapperProps> = ({
  taskId,
  isOpen,
  onOpenChange,
  children,
  isDirty = false,
}) => {
  useInitializeTaskStore(); // Ensure store is initialized
  const task = useTaskStore((state) => taskId ? state.getTaskById(taskId) : undefined);
  const setModalOpenState = useTaskViewStore((state) => state.setModalOpenState);

  const wrappedOnOpenChange = useCallback((open: boolean) => {
    if (!open && isDirty) {
      if (window.confirm("You have unsaved changes. Are you sure you want to discard them?")) {
        onOpenChange(false);
      } else {
        return; // Prevent closing if user cancels discard
      }
    } else {
      onOpenChange(open);
    }
  }, [isDirty, onOpenChange]);

  // Register modal state with the task view store
  useEffect(() => {
    const modalId = taskId || 'new-task';
    setModalOpenState(modalId, isOpen);
    return () => {
      setModalOpenState(modalId, false);
    };
  }, [isOpen, taskId, setModalOpenState]);

  // Determine display title and loading/error states based on store data
  const isLoading = taskId && task === undefined;
  const error = null; // Simplified: Assuming store handles error states

  if (!isOpen) {
    return null;
  }

  return (
    <RadixDialog.Root open={isOpen} onOpenChange={wrappedOnOpenChange}>
      <RadixDialog.Portal>
        <RadixDialog.Overlay className="fixed inset-0 bg-black/50 data-[state=open]:animate-overlayShow" />
        <RadixDialog.Content 
          className="fixed top-1/2 left-1/2 w-[90vw] max-w-lg max-h-[85vh] -translate-x-1/2 -translate-y-1/2 rounded-lg bg-ui-modal-bg p-6 shadow-lg data-[state=open]:animate-contentShow focus:outline-none flex flex-col"
        >
          <RadixDialog.Title className="text-xl font-semibold text-text-primary mb-1">
            {taskId ? (task?.title || 'Edit Task') : 'Create New Task'}
          </RadixDialog.Title>
          <RadixDialog.Description className="text-sm text-text-muted mb-4">
            {taskId ? 'View and edit task information.' : 'Enter details for the new task.'}
          </RadixDialog.Description>

          {isLoading && (
            <div className="flex items-center justify-center h-40">
              <Spinner size={32} />
              <p className="ml-2">Loading task details...</p>
            </div>
          )}
          
          {!isLoading && error && (
            <div className="text-destructive p-4">
              Error: {typeof error === 'string' ? error : (error as Error)?.message || 'Unknown error'}
            </div>
          )}

          {/* Main content */}
          {(!isLoading && !error) && (
            <div className="flex-grow overflow-y-auto pr-2 space-y-4 custom-scrollbar">
              {children}
            </div>
          )}

          <RadixDialog.Close asChild>
            <button
              className={clsx(
                "absolute top-3.5 right-3.5 inline-flex h-6 w-6 appearance-none items-center justify-center rounded-full text-text-muted hover:bg-ui-interactive-bg-hover",
                getFocusClasses()
              )}
              aria-label="Close"
              type="button"
              onClick={() => wrappedOnOpenChange(false)}
            >
              <Cross2Icon />
            </button>
          </RadixDialog.Close>
        </RadixDialog.Content>
      </RadixDialog.Portal>
    </RadixDialog.Root>
  );
};

export default TaskModalWrapper; 