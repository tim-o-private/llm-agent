import React, { useState } from 'react';
import { useTaskStore } from '@/stores/useTaskStore';
import { Task } from '@/api/types';
import { Input } from '@/components/ui/Input';
import { Button } from '@/components/ui/Button';
import { TrashIcon, Pencil1Icon } from '@radix-ui/react-icons'; // For delete/edit icons

interface SubtaskListProps {
  parentTaskId: string;
}

interface SubtaskListItemProps {
  subtask: Task;
  onUpdate: (id: string, updates: Partial<Task>) => void; // Placeholder for update functionality
  onRemove: (id: string) => void;
}

const SubtaskListItem: React.FC<SubtaskListItemProps> = ({ subtask, onUpdate, onRemove }) => {
  const [isEditing, setIsEditing] = useState(false);
  const [editTitle, setEditTitle] = useState(subtask.title);

  const handleUpdate = () => {
    if (editTitle.trim() !== subtask.title) {
      onUpdate(subtask.id, { title: editTitle.trim() });
    }
    setIsEditing(false);
  };

  return (
    <div className="flex items-center justify-between p-2 border-b border-ui-border-light hover:bg-ui-element-bg-hover">
      {isEditing ? (
        <Input 
          type="text"
          value={editTitle}
          onChange={(e) => setEditTitle(e.target.value)}
          onBlur={handleUpdate} // Save on blur
          onKeyDown={(e) => {
            if (e.key === 'Enter') handleUpdate();
            if (e.key === 'Escape') {
              setEditTitle(subtask.title);
              setIsEditing(false);
            }
          }}
          autoFocus
          className="flex-grow mr-2 h-8 text-sm"
        />
      ) : (
        <span 
            className={`flex-grow cursor-pointer ${subtask.status === 'completed' ? 'line-through text-text-muted' : 'text-text-primary'}`}
            onClick={() => setIsEditing(true)} // Click to edit title
        >
            {subtask.title}
        </span>
      )}
      <div className="flex items-center space-x-2">
        <Button onClick={() => setIsEditing(!isEditing)} aria-label="Edit subtask" className="p-1">
            <Pencil1Icon className="w-4 h-4" />
        </Button>
        <Button onClick={() => onRemove(subtask.id)} aria-label="Remove subtask" className="p-1">
            <TrashIcon className="w-4 h-4 text-destructive" />
        </Button>
      </div>
    </div>
  );
};

const SubtaskList: React.FC<SubtaskListProps> = ({ parentTaskId }) => {
  const subtasks = useTaskStore((state) => state.getSubtasksByParentId(parentTaskId));
  const { createTask, updateTask, deleteTask } = useTaskStore.getState(); // Get actions
  const [newSubtaskTitle, setNewSubtaskTitle] = useState('');

  const handleAddSubtask = async () => {
    if (!newSubtaskTitle.trim()) return;

    // Get parent task to copy user_id and potentially other fields
    const parentTask = useTaskStore.getState().getTaskById(parentTaskId);
    if (!parentTask) {
        console.error("Parent task not found, cannot create subtask");
        // Potentially show a toast error
        return;
    }

    const newSubtaskData = {
      title: newSubtaskTitle.trim(),
      parent_task_id: parentTaskId,
      user_id: parentTask.user_id, // Important: Ensure user_id is set
      status: 'pending', // Default status
      priority: parentTask.priority, // Inherit priority from parent, or set a default
      // position / subtask_position would ideally be handled by the store/backend
    } as Omit<Task, 'id' | 'created_at' | 'updated_at' | 'completed' | 'subtasks'>;

    try {
      await createTask(newSubtaskData);
      setNewSubtaskTitle('');
    } catch (error) {
      console.error("Failed to create subtask:", error);
      // Handle error (e.g., show toast)
    }
  };

  const handleUpdateSubtask = (id: string, updates: Partial<Task>) => {
    updateTask(id, updates); // Assuming updateTask handles partial updates
  };

  const handleRemoveSubtask = (id: string) => {
    deleteTask(id);
  };

  return (
    <div className="mt-4">
      <div className="space-y-1 mb-3">
        {subtasks.length > 0 ? (
          subtasks.map(subtask => (
            <SubtaskListItem 
              key={subtask.id} 
              subtask={subtask} 
              onUpdate={handleUpdateSubtask}
              onRemove={handleRemoveSubtask}
            />
          ))
        ) : (
          <p className="text-sm text-text-muted px-2">No subtasks yet.</p>
        )}
      </div>
      <div className="flex items-center mt-2 px-2">
        <Input 
          type="text"
          value={newSubtaskTitle}
          onChange={(e) => setNewSubtaskTitle(e.target.value)}
          placeholder="Add new subtask..."
          className="h-9 text-sm flex-grow mr-2"
          onKeyDown={(e) => {
            if (e.key === 'Enter') {
              e.preventDefault();
              handleAddSubtask();
            }
          }}
        />
        <Button 
          type="button" 
          onClick={handleAddSubtask}
          disabled={!newSubtaskTitle.trim()}
          variant="secondary"
          className="px-3 py-1.5 text-sm"
        >
          Add Subtask
        </Button>
      </div>
    </div>
  );
};

export default SubtaskList; 