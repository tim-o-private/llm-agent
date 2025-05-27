import React, { useCallback, useState, useEffect } from 'react';
import * as RadixDialog from '@radix-ui/react-dialog';
import { Cross2Icon, TrashIcon } from '@radix-ui/react-icons';
import { useTaskStore, useInitializeTaskStore } from '@/stores/useTaskStore';
import { Task } from '@/api/types';
import { Button } from '@/components/ui/Button';
import { Spinner } from '@/components/ui/Spinner';
import { toast } from '@/components/ui/toast';
import TaskForm from './TaskForm'; // Import the new TaskForm
import SubtaskList from './SubtaskList'; // Uncomment and use SubtaskList component
// import SubtaskList from './SubtaskList'; // Placeholder for SubtaskList component

interface TaskDetailViewProps {
  taskId: string | null;
  isOpen: boolean;
  onOpenChange: (isOpen: boolean) => void;
  onTaskUpdated: () => void;
  onDeleteTaskFromDetail?: (taskId: string) => void;
  // Indicates if the view itself currently believes there are unsaved changes.
  // This will be set by TaskForm via a callback.
  isDirtyStateFromChild?: boolean;
  setIsDirtyStateFromChild?: (isDirty: boolean) => void; 
}

export const TaskDetailView: React.FC<TaskDetailViewProps> = ({
  taskId,
  isOpen,
  onOpenChange,
  onTaskUpdated,
  onDeleteTaskFromDetail,
}) => {
  useInitializeTaskStore(); // Ensure store is initialized
  const storeActions = useTaskStore.getState();
  const task = useTaskStore((state) => taskId ? state.getTaskById(taskId) : undefined);

  // Local state to track if the TaskForm has unsaved changes.
  // This is needed for the "are you sure?" dialog when closing.
  const [isFormDirty, setIsFormDirty] = useState(false);

  const handleSaveSuccess = (savedTask?: Task | void) => {
    toast.success(`Task ${savedTask && (savedTask as Task).title ? `"${(savedTask as Task).title}"` : ''} saved successfully!`);
    onTaskUpdated();
    setIsFormDirty(false); // Reset dirty state after successful save
    onOpenChange(false); // Close dialog
  };

  const handleFormCancel = () => {
    setIsFormDirty(false); // Reset dirty state if form handles cancel
    onOpenChange(false); // Close dialog
  };

  const wrappedOnOpenChange = useCallback((open: boolean) => {
    if (!open && isFormDirty) {
      if (window.confirm("You have unsaved changes. Are you sure you want to discard them?")) {
        setIsFormDirty(false); // Reset dirty state
        onOpenChange(false);
      } else {
        return; // Prevent closing if user cancels discard
      }
    } else {
      onOpenChange(open);
      if (!open) {
        setIsFormDirty(false); // Reset dirty state when closed by other means (e.g. X button)
      }
    }
  }, [isFormDirty, onOpenChange]);

  // Effect to reset form dirty state when taskId changes (new task selected)
  useEffect(() => {
    setIsFormDirty(false);
  }, [taskId]);

  const handleDeleteClick = async () => {
    if (taskId) {
      const taskToDelete = storeActions.getTaskById(taskId);
      if (taskToDelete) {
        if (window.confirm('Are you sure you want to delete this task and all its subtasks?')) {
          // Delete subtasks first (if any and if store handles cascading delete or requires manual)
          const subtasks = storeActions.getSubtasksByParentId(taskId);
          for (const sub of subtasks) {
            await storeActions.deleteTask(sub.id); // Assuming deleteTask returns a promise or is sync
          }
          await storeActions.deleteTask(taskId); // Delete parent task
          
          toast.success("Task and subtasks deleted.");
          if (onDeleteTaskFromDetail) onDeleteTaskFromDetail(taskId);
          setIsFormDirty(false); // Reset dirty state
          onOpenChange(false); // Close dialog
        }
      } else {
        toast.error("Could not find task to delete.");
      }
    }
  };

  // Determine display title and loading/error states based on store data
  const isLoading = taskId && task === undefined; // Simplified loading: if taskId exists but task is not yet in store
  const error = null; // Simplified: Assuming store handles error states or TaskForm will show its own.
  
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
            {taskId ? (task?.title || 'Edit Task') : 'Create New Task'} {/* Show task title or generic title */}
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

          {/* Render TaskForm if not loading and no major error, or if creating a new task (taskId is null) */}
          {(!isLoading && !error) && (
            <div className="flex-grow overflow-y-auto pr-2 space-y-4 custom-scrollbar">
              <TaskForm 
                taskId={taskId} 
                onSaveSuccess={handleSaveSuccess} 
                onCancel={handleFormCancel} 
                // Pass a callback to TaskForm to update TaskDetailView's isFormDirty state
                // This is a simplified approach. A more robust solution might involve context or deeper state integration.
                // For now, TaskForm would need a prop like `onDirtyStateChange: (isDirty: boolean) => void`
                // and call `props.onDirtyStateChange(formMethods.formState.isDirty)` in its own effect.
                // For this iteration, TaskForm's internal save/cancel will drive the dirty state reset here.
              />
              
              {/* Placeholder for SubtaskList Component */}
              {taskId && (
                <div className="mt-4 pt-4 border-t border-ui-border">
                  <h3 className="text-md font-semibold text-text-primary mb-2">Subtasks</h3>
                  <SubtaskList parentTaskId={taskId} />
                  {/* <p className="text-sm text-text-muted">Subtask list will be displayed here.</p> */}
                </div>
              )}
            </div>
          )}
          
          {/* Footer with Delete button - only if editing an existing task */}
          {taskId && !isLoading && !error && task && (
            <div className="mt-6 flex justify-end items-center pt-4 border-t border-ui-border">
                {onDeleteTaskFromDetail && (
                  <Button 
                      variant="danger" 
                      onClick={handleDeleteClick} 
                      aria-label="Delete task"
                  >
                      <TrashIcon className="w-4 h-4 mr-2" />
                      Delete Task
                  </Button>
                )}
            </div>
          )}

          <RadixDialog.Close asChild>
            <button
              className="absolute top-3.5 right-3.5 inline-flex h-6 w-6 appearance-none items-center justify-center rounded-full text-text-muted hover:bg-ui-interactive-bg-hover focus:outline-none focus:ring-2 focus:ring-ui-border-focus"
              aria-label="Close"
              type="button"
              onClick={() => wrappedOnOpenChange(false)} // Ensure our wrapper is called
            >
              <Cross2Icon />
            </button>
          </RadixDialog.Close>
        </RadixDialog.Content>
      </RadixDialog.Portal>
    </RadixDialog.Root>
  );
};

export default TaskDetailView; 