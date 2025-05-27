import React, { useState } from 'react';
import { Task } from '@/api/types';
import { toast } from '@/components/ui/toast';
import TaskForm from './TaskForm';
import SubtaskList from './SubtaskList';
import TaskModalWrapper from './TaskModalWrapper';
import TaskActionBar from './TaskActionBar';

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
  const [formState, setFormState] = useState<{
    canSave: boolean;
    isSaving: boolean;
    isCreating: boolean;
    saveError: any;
    handleSave: () => void;
    handleCancel: () => void;
  } | null>(null);
  const [isFormDirty, setIsFormDirty] = useState(false);

  const handleSaveSuccess = (_savedTask?: Task | void) => {
    toast.success(`Task saved successfully!`);
    onTaskUpdated();
    onOpenChange(false);
  };

  const handleDeleteSuccess = () => {
    onDeleteTaskFromDetail?.(taskId!);
    onOpenChange(false);
  };

  const handleCancel = () => {
    onOpenChange(false);
  };

  return (
    <TaskModalWrapper
      taskId={taskId}
      isOpen={isOpen}
      onOpenChange={onOpenChange}
      isDirty={isFormDirty}
    >
      <div className="space-y-4">
        <TaskForm
          taskId={taskId}
          onSaveSuccess={handleSaveSuccess}
          onCancel={handleCancel}
          onDirtyStateChange={setIsFormDirty}
          onFormStateChange={setFormState}
        />
        
        {taskId && (
          <SubtaskList parentTaskId={taskId} />
        )}
        
        <TaskActionBar
          taskId={taskId}
          formState={formState}
          onSaveSuccess={handleSaveSuccess}
          onCancel={handleCancel}
          onDeleteSuccess={handleDeleteSuccess}
        />
      </div>
    </TaskModalWrapper>
  );
};

export default TaskDetailView; 