import React, { useState, useRef, useEffect } from 'react';
import { useSortable } from '@dnd-kit/sortable';
import { CSS } from '@dnd-kit/utilities';
import { DragHandleDots2Icon, Cross2Icon, Pencil1Icon, CheckIcon } from '@radix-ui/react-icons';
import { Task } from '@/api/types';
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

  return (
    <div 
      ref={setNodeRef}
      style={style}
      className={`flex items-center p-2 border rounded-md mb-2 bg-white dark:bg-gray-800 shadow-sm
                ${subtask.status === 'completed' ? 'border-green-200 dark:border-green-900' : 'border-gray-200 dark:border-gray-700'}`}
    >
      <button
        {...listeners}
        {...attributes}
        className="mr-2 cursor-grab active:cursor-grabbing p-1 rounded-md hover:bg-gray-100 dark:hover:bg-gray-700 text-gray-500 dark:text-gray-400"
        aria-label="Drag to reorder"
      >
        <DragHandleDots2Icon />
      </button>
      
      <input
        type="checkbox"
        checked={subtask.status === 'completed'}
        onChange={handleToggleComplete}
        className="mr-3 h-4 w-4 rounded border-gray-300 text-blue-600 focus:ring-blue-500 cursor-pointer"
      />
      
      {isEditing ? (
        <input
          ref={inputRef}
          type="text"
          value={editValue}
          onChange={(e) => setEditValue(e.target.value)}
          onBlur={saveEdit}
          onKeyDown={handleKeyDown}
          className="flex-grow p-1 rounded border border-gray-300 dark:border-gray-600 focus:outline-none focus:ring-2 focus:ring-blue-500 dark:bg-gray-700 dark:text-white"
        />
      ) : (
        <span 
          className={`flex-grow ${subtask.status === 'completed' ? 'line-through text-gray-500 dark:text-gray-400' : 'text-gray-900 dark:text-white'}`}
        >
          {subtask.title}
        </span>
      )}
      
      <div className="flex space-x-1 ml-2">
        {isEditing ? (
          <button
            onClick={saveEdit}
            className="p-1 rounded-md hover:bg-green-100 dark:hover:bg-green-900 text-green-600 dark:text-green-400"
            aria-label="Save changes"
          >
            <CheckIcon />
          </button>
        ) : (
          <button
            onClick={startEditing}
            className="p-1 rounded-md hover:bg-blue-100 dark:hover:bg-blue-900 text-blue-600 dark:text-blue-400"
            aria-label="Edit subtask"
          >
            <Pencil1Icon />
          </button>
        )}
        
        <button
          onClick={handleDelete}
          className="p-1 rounded-md hover:bg-red-100 dark:hover:bg-red-900 text-red-600 dark:text-red-400"
          aria-label="Delete subtask"
        >
          <Cross2Icon />
        </button>
      </div>
    </div>
  );
}; 