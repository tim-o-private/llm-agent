import React, { useState, useEffect } from 'react';
import { useSortable } from '@dnd-kit/sortable';
import { CSS } from '@dnd-kit/utilities';
// import { Card } from './Card'; // Assuming Card is a styled div or similar - Unused import
import { Checkbox } from './Checkbox';
import { Button } from './Button'; // Assuming a Button component exists
import clsx from 'clsx';
import { Task, TaskPriority, TaskStatus } from '@/api/types'; // Import full Task type and enums

// Radix icons for priority and actions
import { 
  ChevronUpIcon, 
  DoubleArrowUpIcon, // For ChevronsUp
  TriangleUpIcon, // For FlameIcon (High Priority)
  DragHandleDots2Icon, // For GripVertical
  CheckCircledIcon, // For CheckCircleIcon
  TrashIcon, // For Trash2Icon
  PlayIcon, 
  ChevronDownIcon, 
  ChevronRightIcon,
  Pencil2Icon // Already present
} from '@radix-ui/react-icons';

// Import SubtaskItem
import { SubtaskItem } from '../features/TaskDetail/SubtaskItem'; // Adjust path as needed

// Dnd-kit imports for subtask reordering
import {
  DndContext as SubtaskDndContext, // Alias to avoid conflict if main card is also in a DndContext
  closestCenter as subtaskClosestCenter,
  KeyboardSensor as SubtaskKeyboardSensor,
  PointerSensor as SubtaskPointerSensor,
  useSensor as useSubtaskSensor,
  useSensors as useSubtaskSensors,
  DragEndEvent as SubtaskDragEndEvent,
} from '@dnd-kit/core';
import {
  arrayMove as subtaskArrayMove,
  SortableContext as SubtaskSortableContext,
  sortableKeyboardCoordinates as subtaskSortableKeyboardCoordinates,
  verticalListSortingStrategy as subtaskVerticalListSortingStrategy,
} from '@dnd-kit/sortable';

// Hook for updating subtask order
import { useUpdateSubtaskOrder } from '@/api/hooks/useTaskHooks'; 
import { toast } from 'react-hot-toast'; // For toasts on reorder

export interface TaskCardProps extends Omit<Task, 'subtasks'> { // Omit subtasks from Task, define it separately
  // id, title, completed, etc. are inherited from Task
  // onToggleComplete: (id: string, completed: boolean) => void; // Replaced by onMarkComplete and onSelectTask
  onStartTask: (id: string) => void; // Callback to handle starting a task
  onEdit?: () => void; // Callback to open detail view for editing
  onStartFocus?: (id: string) => void; // Added for Prioritize View Modal trigger
  
  isSelected?: boolean; // For selection in prioritization view
  onSelectTask?: (id: string, selected: boolean) => void; // Callback for selection change
  onMarkComplete?: (id: string) => void; // Callback to mark task as complete
  onDeleteTask?: (id: string) => void; // Callback to delete a task

  subtasks?: Task[]; // Changed from TaskCardProps[] to Task[]

  className?: string;
  isFocused?: boolean; // Added isFocused prop
}

const priorityIcons: Record<TaskPriority, React.ReactNode | null> = {
  0: null, // None
  1: <ChevronUpIcon className="h-4 w-4 text-gray-400 dark:text-gray-500" />, // Low
  2: <DoubleArrowUpIcon className="h-4 w-4 text-yellow-500" />, // Medium
  3: <TriangleUpIcon className="h-4 w-4 text-red-500" />, // High (Replaced FlameIcon)
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
  subtasks: initialSubtasks, // Prop received from TodayView
  // ...restTaskProps // Unused prop
}) => {
  console.log(`[TaskCard ${id}] Render/Prop Change. Title: ${title}. InitialSubtasks:`, JSON.stringify(initialSubtasks?.map(st => ({id: st.id, title: st.title, pos: st.subtask_position}))));
  const { 
    attributes, 
    listeners, 
    setNodeRef, 
    transform, 
    transition, 
    isDragging 
  } = useSortable({ id });

  const [isSubtasksExpanded, setIsSubtasksExpanded] = useState(false);
  // Remove optimisticSubtasks state. Render directly from `initialSubtasks` prop.

  const updateSubtaskOrderMutation = useUpdateSubtaskOrder();

  // Dnd-kit sensors for subtasks
  const subtaskSensors = useSubtaskSensors(
    useSubtaskSensor(SubtaskPointerSensor),
    useSubtaskSensor(SubtaskKeyboardSensor, {
      coordinateGetter: subtaskSortableKeyboardCoordinates,
    })
  );

  const handleSubtaskDragEnd = (event: SubtaskDragEndEvent) => {
    const { active, over } = event;
    console.log(`[TaskCard ${id}] handleSubtaskDragEnd. Active:`, active.id, 'Over:', over?.id);
    console.log(`[TaskCard ${id}] initialSubtasks at start of dragEnd:`, JSON.stringify(initialSubtasks?.map(st => ({id: st.id, title: st.title, pos: st.subtask_position}))));

    // Use `initialSubtasks` prop directly for calculating new order
    if (active.id !== over?.id && initialSubtasks && over) { // Ensure over is not null
      const oldIndex = initialSubtasks.findIndex((item) => item.id === active.id);
      const newIndex = initialSubtasks.findIndex((item) => item.id === over.id); // Use over.id
      
      console.log(`[TaskCard ${id}] oldIndex:`, oldIndex, 'newIndex:', newIndex);
      if (oldIndex === -1 || newIndex === -1) {
        console.warn(`[TaskCard ${id}] Aborting dragEnd: index not found.`);
        return;
      }

      const newOrderedSubtasksForBackend = subtaskArrayMove(initialSubtasks, oldIndex, newIndex);
      console.log(`[TaskCard ${id}] Calculated newOrderedSubtasksForBackend:`, JSON.stringify(newOrderedSubtasksForBackend.map(st => ({id: st.id, title: st.title, pos: st.subtask_position}))));
      
      const subtasksToUpdate = newOrderedSubtasksForBackend.map((sub, index) => ({
        id: sub.id,
        subtask_position: index + 1, 
      }));
      console.log(`[TaskCard ${id}] Calling updateSubtaskOrderMutation with parentTaskId: ${id}, payload:`, JSON.stringify(subtasksToUpdate));

      updateSubtaskOrderMutation.mutate(
        { parentTaskId: id, orderedSubtasks: subtasksToUpdate }, 
        {
          onSuccess: () => {
            console.log(`[TaskCard ${id}] updateSubtaskOrderMutation onSuccess callback hit.`);
            // Toast is handled by the hook now. TodayView will refetch and re-render TaskCard with new subtasks prop.
            // No need to set local state here.
          },
          onError: (error) => {
            console.error(`[TaskCard ${id}] updateSubtaskOrderMutation onError callback hit. Error:`, error.message);
            // Toast is handled by the hook.
          },
        }
      );
    } else {
      console.log(`[TaskCard ${id}] handleSubtaskDragEnd: active.id === over?.id or initialSubtasks missing or over missing.`);
    }
  };

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
        target.closest('button') ||
        target.closest('.subtask-item-container') || // Prevent if from subtask area
        target.closest('.subtask-drag-context')) { // Prevent if from subtask DND context area
      return;
    }
    if (onEdit) {
      onEdit();
    }
  };

  return (
    <div ref={setNodeRef} style={style} {...attributes} className={clsx('task-card-wrapper', isDragging && 'dragging-shadow')} >
      <div 
        className={clsx(
          'task-card bg-white dark:bg-gray-800 p-3 rounded-lg shadow-sm flex items-center space-x-3 group relative',
          'border', // Ensure border is always applied before status-specific one
          statusCardStyles,
          isFocused && 'ring-4 ring-blue-500 dark:ring-blue-400 shadow-xl bg-blue-100 dark:bg-slate-700', // More prominent ring
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
          <DragHandleDots2Icon className="h-5 w-5 text-gray-400 dark:text-gray-500" />
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

        {/* Expand/Collapse for Subtasks */} 
        {initialSubtasks && initialSubtasks.length > 0 && (
          <button 
            onClick={(e) => { e.stopPropagation(); setIsSubtasksExpanded(!isSubtasksExpanded); }}
            className="p-1 ml-2 text-gray-400 hover:text-gray-600 dark:text-gray-500 dark:hover:text-gray-300 rounded focus:outline-none"
            aria-label={isSubtasksExpanded ? "Collapse subtasks" : "Expand subtasks"}
          >
            {isSubtasksExpanded ? <ChevronDownIcon className="h-4 w-4" /> : <ChevronRightIcon className="h-4 w-4" />}
          </button>
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
              <CheckCircledIcon className="h-4 w-4" />
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
              <TrashIcon className="h-4 w-4" />
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

      {/* Subtasks Container with DND Context */} 
      {isSubtasksExpanded && initialSubtasks && initialSubtasks.length > 0 && (
        <SubtaskDndContext
          sensors={subtaskSensors}
          collisionDetection={subtaskClosestCenter}
          onDragEnd={handleSubtaskDragEnd} 
          onDragStart={(e) => e.activatorEvent.stopPropagation()}
          onDragOver={(e) => e.activatorEvent.stopPropagation()}
          onDragMove={(e) => e.activatorEvent.stopPropagation()}
        >
          <SubtaskSortableContext 
            items={initialSubtasks.map(s => s.id)} // Use initialSubtasks from props
            strategy={subtaskVerticalListSortingStrategy}
          >
            <div className="subtask-item-container subtask-drag-context pl-8 pr-2 pb-2 pt-1 bg-gray-50 dark:bg-gray-800/50 rounded-b-lg border-t border-gray-200 dark:border-gray-700 space-y-1">
              {initialSubtasks.map(subtask => ( // Use initialSubtasks from props
                <SubtaskItem 
                  key={subtask.id} 
                  subtask={subtask} 
                />
              ))}
            </div>
          </SubtaskSortableContext>
        </SubtaskDndContext>
      )}
    </div>
  );
}; 