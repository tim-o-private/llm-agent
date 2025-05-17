import React, { useState } from 'react';
import { Task } from '@/api/types';
import { Checkbox } from '@/components/ui/Checkbox';
import { Input } from '@/components/ui/Input';
import { Button } from '@/components/ui/Button';
import { TrashIcon, Pencil1Icon, CheckIcon, Cross1Icon, DragHandleDots2Icon } from '@radix-ui/react-icons';
import { useUpdateTask, useDeleteTask } from '@/api/hooks/useTaskHooks';
import { toast } from 'react-hot-toast';
import { useSortable } from '@dnd-kit/sortable';
import { CSS } from '@dnd-kit/utilities';

interface SubtaskItemProps {
  subtask: Task;
  onSubtaskUpdate?: () => void; // Callback to refetch parent task's subtasks
}

export const SubtaskItem: React.FC<SubtaskItemProps> = ({ subtask, onSubtaskUpdate }) => {
  const [isEditing, setIsEditing] = useState(false);
  const [editedTitle, setEditedTitle] = useState(subtask.title);

  const updateTaskMutation = useUpdateTask();
  const deleteTaskMutation = useDeleteTask();

  const {
    attributes,
    listeners,
    setNodeRef,
    transform,
    transition,
    isDragging,
  } = useSortable({ id: subtask.id });

  const style = {
    transform: CSS.Transform.toString(transform),
    transition,
    opacity: isDragging ? 0.5 : 1,
    zIndex: isDragging ? 10 : undefined, // Ensure dragging item is on top
  };

  const handleToggleComplete = () => {
    const newStatus = subtask.status === 'completed' ? 'pending' : 'completed';
    updateTaskMutation.mutate(
      { id: subtask.id, updates: { status: newStatus, completed: newStatus === 'completed' } },
      {
        onSuccess: () => {
          toast.success(`Subtask "${subtask.title}" marked ${newStatus}.`);
          onSubtaskUpdate?.();
        },
        onError: (error) => {
          toast.error(`Failed to update subtask: ${error.message}`);
        },
      }
    );
  };

  const handleTitleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setEditedTitle(e.target.value);
  };

  const handleSaveTitle = () => {
    if (editedTitle.trim() === '' || editedTitle.trim() === subtask.title) {
      setIsEditing(false);
      setEditedTitle(subtask.title); // Reset if unchanged or empty
      return;
    }
    updateTaskMutation.mutate(
      { id: subtask.id, updates: { title: editedTitle.trim() } },
      {
        onSuccess: () => {
          toast.success('Subtask title updated.');
          setIsEditing(false);
          onSubtaskUpdate?.();
        },
        onError: (error) => {
          toast.error(`Failed to update title: ${error.message}`);
        },
      }
    );
  };

  const handleDelete = () => {
    if (window.confirm(`Are you sure you want to delete subtask "${subtask.title}"?`)) {
      deleteTaskMutation.mutate({ id: subtask.id }, {
        onSuccess: () => {
          toast.success('Subtask deleted.');
          onSubtaskUpdate?.();
        },
        onError: (error) => {
          toast.error(`Failed to delete subtask: ${error.message}`);
        },
      });
    }
  };

  return (
    <div 
      ref={setNodeRef} 
      style={style} 
      className="flex items-center justify-between py-2 px-1 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-md touch-manipulation select-none"
    >
      <div className="flex items-center flex-grow">
        <button 
          {...attributes} 
          {...listeners} 
          aria-label="Drag to reorder subtask"
          className="p-1 mr-2 cursor-grab focus:outline-none focus:ring-1 focus:ring-indigo-500 rounded"
        >
          <DragHandleDots2Icon className="h-4 w-4 text-gray-400 dark:text-gray-500" />
        </button>
        <Checkbox
          id={`subtask-${subtask.id}`}
          checked={subtask.status === 'completed'}
          onCheckedChange={handleToggleComplete}
          className="mr-3"
          aria-label={`Mark subtask ${subtask.title} as complete`}
        />
        {isEditing ? (
          <Input
            type="text"
            value={editedTitle}
            onChange={handleTitleChange}
            onBlur={handleSaveTitle} // Save on blur
            onKeyDown={(e) => e.key === 'Enter' && handleSaveTitle()} // Save on Enter
            className="h-8 text-sm flex-grow mr-2"
            autoFocus
          />
        ) : (
          <span
            className={`text-sm flex-grow cursor-pointer ${subtask.status === 'completed' ? 'line-through text-gray-500 dark:text-gray-400' : ''}`}
            onClick={() => setIsEditing(true)} // Click text to edit
            onKeyDown={(e) => e.key === 'Enter' && setIsEditing(true)}
            role="button"
            tabIndex={0}
          >
            {subtask.title}
          </span>
        )}
      </div>
      <div className="flex items-center space-x-1 ml-2 flex-shrink-0">
        {isEditing ? (
          <>
            <Button onClick={handleSaveTitle} aria-label="Save title">
              <CheckIcon className="h-4 w-4" />
            </Button>
            <Button onClick={() => { setIsEditing(false); setEditedTitle(subtask.title); }} aria-label="Cancel editing title">
              <Cross1Icon className="h-4 w-4" />
            </Button>
          </>
        ) : (
          <Button onClick={() => setIsEditing(true)} aria-label="Edit title">
            <Pencil1Icon className="h-4 w-4" />
          </Button>
        )}
        <Button onClick={handleDelete} aria-label="Delete subtask">
          <TrashIcon className="h-4 w-4 text-red-500" />
        </Button>
      </div>
    </div>
  );
}; 