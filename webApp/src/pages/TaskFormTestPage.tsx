import React, { useState } from 'react';
import TaskForm from '@/components/features/TaskDetail/TaskForm';
import { Button } from '@/components/ui/Button';

const TaskFormTestPage: React.FC = () => {
  const [taskId, setTaskId] = useState<string | null>(null);
  const [showForm, setShowForm] = useState(false);

  const handleSaveSuccess = () => {
    console.log('Save success!');
    setShowForm(false);
  };

  const handleCancel = () => {
    console.log('Cancel clicked!');
    setShowForm(false);
  };

  const handleDeleteSuccess = () => {
    console.log('Delete success!');
    setShowForm(false);
  };

  const handleDirtyStateChange = (isDirty: boolean) => {
    console.log('Form dirty state:', isDirty);
  };

  return (
    <div className="p-8 max-w-4xl mx-auto">
      <h1 className="text-2xl font-bold mb-6">TaskForm Test Page</h1>

      <div className="space-y-4 mb-8">
        <Button
          onClick={() => {
            setTaskId(null);
            setShowForm(true);
          }}
        >
          Create New Task
        </Button>
        <Button
          onClick={() => {
            setTaskId('existing-task-id');
            setShowForm(true);
          }}
        >
          Edit Existing Task (Mock)
        </Button>
      </div>

      {showForm && (
        <div className="border border-ui-border rounded-lg p-6 bg-ui-element-bg">
          <h2 className="text-lg font-semibold mb-4">{taskId ? 'Edit Task' : 'Create New Task'}</h2>

          <TaskForm
            taskId={taskId}
            onSaveSuccess={handleSaveSuccess}
            onCancel={handleCancel}
            onDeleteSuccess={handleDeleteSuccess}
            onDirtyStateChange={handleDirtyStateChange}
          />
        </div>
      )}
    </div>
  );
};

export default TaskFormTestPage;
