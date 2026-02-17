import React, { useEffect, useRef } from 'react';
import { Dialog, Flex } from '@radix-ui/themes';
import { useTaskStore } from '@/stores/useTaskStore';
import { useTaskViewStore } from '@/stores/useTaskViewStore';
import { toast } from '@/components/ui/toast';
import TaskForm, { TaskFormRef } from './TaskForm';
import SubtaskList from './SubtaskList';
import DialogActionBar, { DialogAction } from '@/components/ui/DialogActionBar';
import { createComponentLogger } from '@/utils/logger';
import { useDialogState } from '@/hooks/useDialogState';
import { useSubtaskManagement } from '@/hooks/useSubtaskManagement';

const log = createComponentLogger('TaskDetailView');

interface TaskDetailViewProps {
  taskId: string | null;
  isOpen: boolean;
  onOpenChange: (isOpen: boolean) => void;
  onTaskUpdated: () => void;
  onDeleteTaskFromDetail?: (taskId: string) => void;
}

export const TaskDetailView: React.FC<TaskDetailViewProps> = ({
  taskId,
  isOpen,
  onOpenChange,
  onTaskUpdated,
  onDeleteTaskFromDetail,
}) => {
  log.debug('Render', { taskId, isOpen });

  const task = useTaskStore((state) => (taskId ? state.getTaskById(taskId) : undefined));
  const setModalOpenState = useTaskViewStore((state) => state.setModalOpenState);
  const taskFormRef = useRef<TaskFormRef>(null);

  // Use subtask management hook
  const subtaskManagement = useSubtaskManagement(taskId);

  // Use dialog state hook
  const dialogState = useDialogState({
    onOpenChange,
    onTaskUpdated,
    setModalOpenState,
    additionalDirtyState: subtaskManagement.isSubtasksDirty,
    onResetState: subtaskManagement.resetSubtaskState,
  });

  // Register modal state for keyboard shortcut management
  useEffect(() => {
    const modalId = taskId ?? 'new-task';
    dialogState.registerModalState(modalId, isOpen);
    return () => {
      if (setModalOpenState) {
        setModalOpenState(modalId, false);
      }
    };
  }, [isOpen, taskId, dialogState.registerModalState, setModalOpenState]);

  // Combined save function
  const handleSave = async () => {
    if (!taskFormRef.current) {
      log.error('TaskForm ref not available');
      return;
    }

    await dialogState.handleSave(async () => {
      // Save the main task form first
      await taskFormRef.current!.save();

      // Apply pending subtask changes if any
      if (subtaskManagement.isSubtasksDirty && taskId) {
        await subtaskManagement.applyPendingSubtaskChanges(taskId);
      }
    });
  };

  const handleSaveSuccess = () => {
    log.debug('handleSaveSuccess called');
    dialogState.handleSaveSuccess();
  };

  const handleDelete = async () => {
    if (!taskId) return;

    if (window.confirm('Are you sure you want to delete this task? This action cannot be undone.')) {
      try {
        const { deleteTask } = useTaskStore.getState();
        await deleteTask(taskId);
        log.debug('handleDelete called');
        toast.success('Task deleted successfully');
        onDeleteTaskFromDetail?.(taskId);
        onOpenChange(false); // Direct close after successful delete
      } catch (error) {
        log.error('Delete failed', error);
        toast.error('Failed to delete task');
      }
    }
  };

  // Dynamic title and description
  const title = taskId ? task?.title || 'Edit Task' : 'Create New Task';
  const description = taskId ? 'View and edit task information.' : 'Enter details for the new task.';

  // Define dialog actions
  const actions: DialogAction[] = [
    {
      label: 'Cancel',
      onClick: dialogState.handleCancel,
      variant: 'soft',
      color: 'gray',
    },
    ...(taskId
      ? [
          {
            label: 'Delete',
            onClick: handleDelete,
            variant: 'soft' as const,
            color: 'red' as const,
          },
        ]
      : []),
    {
      label: taskId ? 'Save Changes' : 'Create Task',
      onClick: handleSave,
      variant: 'solid' as const,
      disabled: !dialogState.isDirty,
      loading: dialogState.isSaving,
      type: 'submit' as const,
    },
  ];

  return (
    <Dialog.Root open={isOpen} onOpenChange={dialogState.wrappedOnOpenChange}>
      <Dialog.Content size="4" maxWidth="700px">
        <Dialog.Title>{title}</Dialog.Title>
        <Dialog.Description size="2" mb="4">
          {description}
        </Dialog.Description>

        <Flex direction="column" gap="5">
          {/* Main Task Form */}
          <TaskForm
            ref={taskFormRef}
            taskId={taskId}
            onSaveSuccess={handleSaveSuccess}
            onCancel={dialogState.handleCancel}
            onDirtyStateChange={dialogState.setIsFormDirty}
          />

          {/* Subtasks Section - Only show for existing tasks */}
          {taskId && (
            <div>
              <h3 className="text-lg font-semibold text-text-primary mb-3">Subtasks</h3>
              <SubtaskList
                parentTaskId={taskId}
                showAddSubtask={true}
                className="border border-ui-border rounded-lg p-4 bg-ui-element-bg"
                onSubtaskChange={subtaskManagement.handleSubtaskChange}
                onSubtaskReorder={subtaskManagement.handleSubtaskReorder}
                onSubtaskCreate={subtaskManagement.handleSubtaskCreate}
                onSubtaskUpdate={subtaskManagement.handleSubtaskUpdate}
                onSubtaskDelete={subtaskManagement.handleSubtaskDelete}
                optimisticSubtasks={subtaskManagement.optimisticSubtasks}
              />
            </div>
          )}

          {/* Generic Action Bar */}
          <DialogActionBar actions={actions} />
        </Flex>
      </Dialog.Content>
    </Dialog.Root>
  );
};

export default TaskDetailView;
