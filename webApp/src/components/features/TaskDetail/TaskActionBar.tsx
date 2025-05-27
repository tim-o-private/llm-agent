import React, { useState } from 'react';
import { Button } from '@/components/ui/Button';
import { TrashIcon } from '@radix-ui/react-icons';
import { useTaskStore } from '@/stores/useTaskStore';
import { toast } from '@/components/ui/toast';

interface FormState {
  canSave: boolean;
  isSaving: boolean;
  isCreating: boolean;
  saveError: any;
  handleSave: () => void;
  handleCancel: () => void;
}

interface TaskActionBarProps {
  taskId: string | null;
  formState: FormState | null;
  onSaveSuccess?: () => void;
  onCancel?: () => void;
  onDeleteSuccess?: () => void;
}

export const TaskActionBar: React.FC<TaskActionBarProps> = ({
  taskId,
  formState,
  onSaveSuccess: _onSaveSuccess,
  onCancel,
  onDeleteSuccess,
}) => {
  const [isDeleting, setIsDeleting] = useState(false);
  const storeActions = useTaskStore.getState();

  const handleDelete = async () => {
    if (!taskId) return;

    const confirmed = window.confirm(
      'Are you sure you want to delete this task? This action cannot be undone. All subtasks will also be deleted.'
    );

    if (!confirmed) return;

    setIsDeleting(true);
    try {
      // Delete subtasks first (cascade deletion) - using same logic as TaskDetailView
      const subtasks = storeActions.getSubtasksByParentId(taskId);
      for (const sub of subtasks) {
        await storeActions.deleteTask(sub.id);
      }
      
      // Then delete the main task
      await storeActions.deleteTask(taskId);
      
      toast.success('Task deleted successfully');
      onDeleteSuccess?.();
    } catch (error) {
      console.error('Error deleting task:', error);
      toast.error('Failed to delete task. Please try again.');
    } finally {
      setIsDeleting(false);
    }
  };

  const handleSave = () => {
    if (formState?.handleSave) {
      formState.handleSave();
      // onSaveSuccess will be called by the form's success handler
    }
  };

  const handleCancel = () => {
    if (formState?.handleCancel) {
      formState.handleCancel();
    }
    onCancel?.();
  };

  if (!formState) {
    return null; // Form not ready yet
  }

  const { canSave, isSaving, isCreating, saveError } = formState;

  return (
    <div className="flex items-center justify-between pt-4 border-t border-ui-border">
      {/* Left side: Delete (destructive action, only for existing tasks) */}
      {taskId ? (
        <Button
          type="button"
          variant="danger"
          onClick={handleDelete}
          disabled={isSaving || isDeleting}
          className="min-w-[80px] flex items-center space-x-1"
        >
          {isDeleting ? (
            <span className="flex items-center">
              <div className="animate-spin rounded-full h-3 w-3 border-b-2 border-white mr-1"></div>
              Deleting...
            </span>
          ) : (
            <>
              <TrashIcon className="h-3 w-3" />
              <span>Delete</span>
            </>
          )}
        </Button>
      ) : (
        <div className="min-w-[80px]" /> // Spacer for new tasks (no delete button)
      )}

      {/* Right side: Cancel and Save actions */}
      <div className="flex items-center space-x-3">
        {saveError && (
          <span className="text-sm text-destructive mr-2">
            Save failed
          </span>
        )}
        
        <Button
          type="button"
          variant="secondary"
          onClick={handleCancel}
          disabled={isSaving || isDeleting}
          className="min-w-[80px]"
        >
          Cancel
        </Button>

        <Button
          type="button"
          variant="primary"
          onClick={handleSave}
          disabled={!canSave || isSaving || isDeleting}
          className="min-w-[80px] bg-bg-success-indicator hover:bg-success-strong focus:ring-success-indicator"
        >
          {isSaving ? (
            <span className="flex items-center">
              <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white mr-2"></div>
              {isCreating ? 'Creating...' : 'Saving...'}
            </span>
          ) : (
            isCreating ? 'Create Task' : 'Save'
          )}
        </Button>
      </div>
    </div>
  );
};

export default TaskActionBar; 