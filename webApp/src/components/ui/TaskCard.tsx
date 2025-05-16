import React from 'react';
import { useSortable } from '@dnd-kit/sortable';
import { CSS } from '@dnd-kit/utilities';
// import { Card } from './Card'; // Assuming Card is a styled div or similar - Unused import
import { Checkbox } from './Checkbox';
import { Button } from './Button'; // Assuming a Button component exists
import clsx from 'clsx';
import { Task, TaskPriority, TaskStatus } from '@/api/types'; // Import full Task type and enums

// Lucide icons for priority and actions
import { ChevronUp, ChevronsUp, Flame, GripVertical, CheckCircleIcon, Trash2Icon, PlayIcon } from 'lucide-react';
import { Pencil2Icon } from '@radix-ui/react-icons';

export interface TaskCardProps extends Task { // TaskCardProps now extends the full Task type
  // id, title, completed, etc. are inherited from Task
  // onToggleComplete: (id: string, completed: boolean) => void; // Replaced by onMarkComplete and onSelectTask
  onStartTask: (id: string) => void; // Callback to handle starting a task
  onEdit?: () => void; // Callback to open detail view for editing
  onStartFocus?: (id: string) => void; // Added for Prioritize View Modal trigger
  
  isSelected?: boolean; // For selection in prioritization view
  onSelectTask?: (id: string, selected: boolean) => void; // Callback for selection change
  onMarkComplete?: (id: string) => void; // Callback to mark task as complete
  onDeleteTask?: (id: string) => void; // Callback to delete a task

  className?: string;
  isFocused?: boolean; // Added isFocused prop
}

const priorityIcons: Record<TaskPriority, React.ReactNode | null> = {
  0: null, // None
  1: <ChevronUp size={16} className="text-gray-400 dark:text-gray-500" />, // Low
  2: <ChevronsUp size={16} className="text-yellow-500" />, // Medium
  3: <Flame size={16} className="text-red-500" />, // High
};

const getStatusStyles = (status: TaskStatus, completed: boolean) => {
  if (completed || status === 'completed') return 'opacity-60 line-through';
  if (status === 'in_progress') return 'border-blue-500 dark:border-blue-400 shadow-md';
  if (status === 'planning') return 'border-green-500 dark:border-green-400';
  return 'border-gray-200 dark:border-gray-700';
};

export const TaskCard: React.FC<TaskCardProps> = ({
  id,
  title,
  // category, // Unused prop
  // notes,    // Unused prop
  completed,
  status,
  priority,
  // onToggleComplete, // Removed
  onStartTask,
  onEdit,
  onStartFocus,
  isSelected,
  onSelectTask,
  onMarkComplete,
  onDeleteTask,
  isFocused,
  className,
  // ...restTaskProps // Unused prop
}) => {
  const { 
    attributes, 
    listeners, 
    setNodeRef, 
    transform, 
    transition, 
    isDragging 
  } = useSortable({ id });

  const style = {
    transform: CSS.Transform.toString(transform),
    transition,
    zIndex: isDragging ? 100 : 'auto',
    boxShadow: isDragging ? '0 10px 15px -3px rgba(0, 0, 0, 0.1), 0 4px 6px -2px rgba(0, 0, 0, 0.05)' : 'none',
  };

  const statusCardStyles = getStatusStyles(status, completed);

  const handleCardClick = (e: React.MouseEvent<HTMLDivElement>) => {
    // Ensure the click is not on an interactive element like checkbox, drag handle, or start button
    const target = e.target as HTMLElement;
    if (target.closest('input[type="checkbox"]') || 
        target.closest('[role="button"]') || // This covers the drag handle and the Start button
        target.closest('button')) { 
      return;
    }
    if (onEdit) {
      onEdit();
    }
  };

  return (
    <div 
      ref={setNodeRef} 
      style={style} 
      {...attributes} // attributes for dnd-kit sortable, NOT for general card click
      className={clsx(
        'task-card bg-white dark:bg-gray-800 p-3 rounded-lg shadow-sm flex items-center space-x-3 group relative',
        'border', // Ensure border is always applied before status-specific one
        statusCardStyles,
        isFocused && 'ring-2 ring-blue-600 dark:ring-blue-500 shadow-xl bg-blue-50 dark:bg-slate-700', // Changed dark mode focused background to slate-700
        className,
        // onEdit ? 'cursor-pointer' : '' // Remove cursor-pointer from whole card if we have a dedicated edit button
      )}
      // onClick={handleCardClick} // Remove direct click handler from the main div if edit icon is primary
    >
      {/* Drag Handle Icon - listeners attached EXCLUSIVELY here */}
      <div 
        {...listeners} 
        className="p-1 cursor-grab touch-none group-hover:bg-gray-100 dark:group-hover:bg-gray-700 rounded"
        aria-label="Drag to reorder task"
        role="button"
        tabIndex={0} 
      >
        <GripVertical size={18} className="text-gray-400 dark:text-gray-500" />
      </div>

      {/* Checkbox for Selection */}
      <div className="flex items-center h-5">
        <Checkbox
          id={`task-checkbox-${id}`}
          checked={isSelected} // Use isSelected for checkbox state
          onCheckedChange={(checked) => onSelectTask && onSelectTask(id, !!checked)} // Pass boolean state
          aria-label={`Select task ${title} for prioritization`} // Updated aria-label
        />
      </div>

      {/* Task Info */}
      <div className="flex-grow min-w-0" onClick={onEdit ? handleCardClick : undefined} style={onEdit ? {cursor: 'pointer'} : {}} >
        <p className={clsx("text-sm font-medium text-gray-900 dark:text-white truncate", (completed || status === 'completed') && "line-through")}>
          {title}
        </p>
        {/* Optional: Display time or category if needed */}
        {/* {time && <p className="text-xs text-gray-500 dark:text-gray-400">{time}</p>} */}
        {/* {category && <p className="text-xs text-gray-500 dark:text-gray-400">{category}</p>} */}
      </div>
      
      {/* Priority Icon */}
      {priorityIcons[priority] && (
        <div className="ml-auto pl-2" title={`Priority: ${priority === 1 ? 'Low' : priority === 2 ? 'Medium' : 'High'}`}>
          {priorityIcons[priority]}
        </div>
      )}

      {/* Action Buttons Group */}
      <div className="ml-auto flex items-center space-x-1 pl-2">
        {onStartFocus && !completed && status !== 'completed' && (
          <button
            onClick={(e) => {
              e.stopPropagation();
              onStartFocus(id);
            }}
            aria-label="Prepare and Focus on task"
            title="Prepare & Focus"
            className="p-1.5 text-blue-500 dark:text-blue-400 hover:text-blue-700 dark:hover:text-blue-300 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 rounded-full hover:bg-gray-100 dark:hover:bg-gray-700"
          >
            <PlayIcon className="h-4 w-4" />
          </button>
        )}

        {onEdit && (
          <button
            onClick={(e) => {
              e.stopPropagation();
              onEdit();
            }}
            aria-label="Edit task"
            className="p-1.5 text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-200 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 rounded-full hover:bg-gray-100 dark:hover:bg-gray-700"
          >
            <Pencil2Icon className="h-4 w-4" />
          </button>
        )}

        {onMarkComplete && !completed && status !== 'completed' && (
          <button
            onClick={(e) => {
              e.stopPropagation();
              onMarkComplete(id);
            }}
            aria-label="Mark task complete"
            className="p-1.5 text-green-500 dark:text-green-400 hover:text-green-700 dark:hover:text-green-300 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-green-500 rounded-full hover:bg-gray-100 dark:hover:bg-gray-700"
          >
            <CheckCircleIcon className="h-4 w-4" />
          </button>
        )}

        {onDeleteTask && (
          <button
            onClick={(e) => {
              e.stopPropagation();
              onDeleteTask(id);
            }}
            aria-label="Delete task"
            className="p-1.5 text-red-500 dark:text-red-400 hover:text-red-700 dark:hover:text-red-300 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-red-500 rounded-full hover:bg-gray-100 dark:hover:bg-gray-700"
          >
            <Trash2Icon className="h-4 w-4" />
          </button>
        )}
      </div>

      {/* Start Button - Conditionally render based on status */}
      {status !== 'in_progress' && status !== 'completed' && !completed && (
        <Button 
          variant="secondary"
          onClick={(e) => { 
            e.stopPropagation(); // Prevent drag listeners from firing
            onStartTask(id); 
          }}
          className="ml-auto flex-shrink-0 px-2 py-1 text-xs"
        >
          Start
        </Button>
      )}
       {status === 'in_progress' && (
        <span className="ml-auto text-xs text-blue-600 dark:text-blue-400 font-semibold flex-shrink-0">In Progress</span>
      )}
    </div>
  );
}; 