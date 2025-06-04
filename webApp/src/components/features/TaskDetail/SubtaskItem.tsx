import React, { useState, useRef, useEffect } from 'react';
import { useSortable } from '@dnd-kit/sortable';
import { CSS } from '@dnd-kit/utilities';
import { Card } from '@radix-ui/themes';
import { DragHandleDots2Icon, Cross2Icon, Pencil1Icon, CheckIcon } from '@radix-ui/react-icons';
import { Task } from '@/api/types';
import { Input } from '@/components/ui/Input';
import { Checkbox } from '@/components/ui/Checkbox';
import { 
  getStatusContainerStyles, 
  getStatusTextStyles, 
  getStatusButtonStyles 
} from '@/utils/statusStyles';
import clsx from 'clsx';
// import { useTaskStore } from '@/stores/useTaskStore'; // Remove direct store usage

interface SubtaskItemProps {
  subtask: Task;
  // parentTaskId?: string; // Remove
  // onSubtaskUpdate?: () => void; // Remove
  onUpdate: (id: string, updates: Partial<Task>) => void; // Add
  onRemove: (id: string) => void; // Add
}

export const SubtaskItem: React.FC<SubtaskItemProps> = ({ subtask, onUpdate, onRemove }) => {
  const [isEditing, setIsEditing] = useState(false);
  const [editValue, setEditValue] = useState(subtask.title);
  const inputRef = useRef<HTMLInputElement>(null);
  
  // Get actions from the task store - REMOVE
  // const { updateTask, deleteTask } = useTaskStore(state => ({
  //   updateTask: state.updateTask,
  //   deleteTask: state.deleteTask
  // }));

  const {
    attributes,
    listeners,
    setNodeRef,
    transform,
    transition,
    isDragging
  } = useSortable({ id: subtask.id });

  const style = {
    transform: CSS.Transform.toString(transform),
    transition,
    opacity: isDragging ? 0.4 : 1,
  };

  useEffect(() => {
    if (isEditing && inputRef.current) {
      inputRef.current.focus();
    }
  }, [isEditing]);

  const handleToggleComplete = () => {
    const newStatus = subtask.status === 'completed' ? 'pending' : 'completed';
    // updateTask(subtask.id, { 
    //   status: newStatus,
    //   completed: newStatus === 'completed'
    // });
    onUpdate(subtask.id, { 
      status: newStatus,
      completed: newStatus === 'completed',
      completed_at: newStatus === 'completed' ? new Date().toISOString() : null 
    });
    
    // if (onSubtaskUpdate) { // Remove
    //   onSubtaskUpdate();
    // }
  };

  const handleDelete = () => {
    // deleteTask(subtask.id); // Remove
    onRemove(subtask.id);
    
    // if (onSubtaskUpdate) { // Remove
    //   onSubtaskUpdate();
    // }
  };

  const startEditing = () => {
    setEditValue(subtask.title);
    setIsEditing(true);
  };

  const saveEdit = () => {
    if (editValue.trim() !== subtask.title) {
      // updateTask(subtask.id, { title: editValue.trim() }); // Remove
      onUpdate(subtask.id, { title: editValue.trim() });
      
      // if (onSubtaskUpdate) { // Remove
      //   onSubtaskUpdate();
      // }
    }
    setIsEditing(false);
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter') {
      saveEdit();
    } else if (e.key === 'Escape') {
      setIsEditing(false);
      setEditValue(subtask.title);
    }
  };

  // Determine card variant based on status
  const getCardVariant = () => {
    if (subtask.status === 'completed') return 'ghost';
    return 'surface';
  };

  return (
    <div 
      ref={setNodeRef}
      style={style}
      className="subtask-item-container"
    >
      <Card
        variant={getCardVariant()}
        size="1"
        className={clsx(
          'mb-2',
          // Override Radix focus styles with our global focus system
          '[&]:focus-within:outline-none [&]:focus:outline-none [&]:focus-visible:outline-none',
          // Apply our status-based styling on top of Radix base
          getStatusContainerStyles({
            completed: subtask.status === 'completed',
            status: subtask.status,
            variant: 'item'
          })
        )}
      >
        <div className="flex items-center p-2">
          <button
            {...listeners}
            {...attributes}
            className={clsx(
              getStatusButtonStyles({ completed: subtask.status === 'completed' }),
              "mr-2 cursor-grab active:cursor-grabbing"
            )}
            aria-label="Drag to reorder"
          >
            <DragHandleDots2Icon />
          </button>
          
          <Checkbox
            checked={subtask.status === 'completed'}
            onCheckedChange={handleToggleComplete}
            className="mr-3"
          />
          
          {isEditing ? (
            <Input
              ref={inputRef}
              type="text"
              value={editValue}
              onChange={(e) => setEditValue(e.target.value)}
              onBlur={saveEdit}
              onKeyDown={handleKeyDown}
              className="flex-grow"
            />
          ) : (
            <span 
              className={clsx(
                'flex-grow',
                getStatusTextStyles({ completed: subtask.status === 'completed' })
              )}
            >
              {subtask.title}
            </span>
          )}
          
          <div className="flex space-x-1 ml-2">
            {isEditing ? (
              <button
                onClick={saveEdit}
                className="p-1 rounded-md hover:bg-success-subtle text-success-strong"
                aria-label="Save changes"
              >
                <CheckIcon />
              </button>
            ) : (
              <button
                onClick={startEditing}
                className="p-1 rounded-md hover:bg-accent-subtle text-brand-primary"
                aria-label="Edit subtask"
              >
                <Pencil1Icon />
              </button>
            )}
            
            <button
              onClick={handleDelete}
              className="p-1 rounded-md hover:bg-destructive-subtle text-destructive"
              aria-label="Delete subtask"
            >
              <Cross2Icon />
            </button>
          </div>
        </div>
      </Card>
    </div>
  );
}; 