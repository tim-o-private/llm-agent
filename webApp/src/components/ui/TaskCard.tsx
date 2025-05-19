import React, { useState, useEffect } from 'react';
import { useSortable } from '@dnd-kit/sortable';
import { CSS } from '@dnd-kit/utilities';
import { Checkbox } from './Checkbox';
import { Button } from './Button';
import clsx from 'clsx';
import { Task, TaskPriority, TaskStatus } from '@/api/types';

import {
  ChevronUpIcon,
  DoubleArrowUpIcon,
  TriangleUpIcon,
  DragHandleDots2Icon,
  CheckCircledIcon,
  TrashIcon,
  PlayIcon,
  ChevronDownIcon,
  ChevronRightIcon,
  Pencil2Icon
} from '@radix-ui/react-icons';

import { SubtaskItem } from '../features/TaskDetail/SubtaskItem';

import {
  DndContext as SubtaskDndContext,
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

import { useUpdateSubtaskOrder } from '@/api/hooks/useTaskHooks';

export interface TaskCardProps extends Omit<Task, 'subtasks'> {
  onStartTask: (id: string) => void;
  onEdit?: () => void;
  onStartFocus?: (id: string) => void;
  isSelected?: boolean;
  onSelectTask?: (id: string, selected: boolean) => void;
  onMarkComplete?: (id: string) => void;
  onDeleteTask?: (id: string) => void;
  subtasks?: Task[];
  className?: string;
  isFocused?: boolean;
}

const priorityIcons: Record<TaskPriority, React.ReactNode | null> = {
  0: null,
  1: <ChevronUpIcon className="h-4 w-4 text-gray-400 dark:text-gray-500" />,
  2: <DoubleArrowUpIcon className="h-4 w-4 text-yellow-500" />,
  3: <TriangleUpIcon className="h-4 w-4 text-red-500" />,
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
  completed,
  status,
  priority,
  onStartTask,
  onEdit,
  onStartFocus,
  isSelected,
  onSelectTask,
  onMarkComplete,
  onDeleteTask,
  isFocused,
  className,
  subtasks: initialSubtasksProp,
}) => {
  const {
    attributes,
    listeners,
    setNodeRef,
    transform,
    transition,
    isDragging
  } = useSortable({ id });

  const [isSubtasksExpanded, setIsSubtasksExpanded] = useState(false);
  const [displayedSubtasks, setDisplayedSubtasks] = useState<Task[] | undefined>(initialSubtasksProp);

  useEffect(() => {
    setDisplayedSubtasks(initialSubtasksProp);
  }, [initialSubtasksProp]);

  const updateSubtaskOrderMutation = useUpdateSubtaskOrder();

  const subtaskSensors = useSubtaskSensors(
    useSubtaskSensor(SubtaskPointerSensor),
    useSubtaskSensor(SubtaskKeyboardSensor, {
      coordinateGetter: subtaskSortableKeyboardCoordinates,
    })
  );

  const handleSubtaskDragEnd = (event: SubtaskDragEndEvent) => {
    const { active, over } = event;

    if (active.id !== over?.id && displayedSubtasks && over) {
      const oldIndex = displayedSubtasks.findIndex((item: Task) => item.id === active.id);
      const newIndex = displayedSubtasks.findIndex((item: Task) => item.id === over.id);

      if (oldIndex === -1 || newIndex === -1) {
        return;
      }

      const reorderedSubtasks = subtaskArrayMove(displayedSubtasks, oldIndex, newIndex);
      setDisplayedSubtasks(reorderedSubtasks);

      const subtasksToUpdate = reorderedSubtasks.map((sub: Task, index: number) => ({
        id: sub.id,
        subtask_position: index + 1,
      }));

      updateSubtaskOrderMutation.mutate(
        { parentTaskId: id, orderedSubtasks: subtasksToUpdate },
        {
          onSuccess: () => {
            // console.log(`[TaskCard ${id}] updateSubtaskOrderMutation onSuccess`);
          },
          onError: (error) => {
            console.error(`[TaskCard ${id}] updateSubtaskOrderMutation onError:`, error.message);
            // Potentially revert optimistic update if backend fails
            // setDisplayedSubtasks(initialSubtasksProp); // Or more robustly, the state before this drag
          },
        }
      );
    }
  };
  
  const handleSubtaskUpdate = (subtaskId: string, updates: Partial<Task>) => {
    console.warn(`[TaskCard ${id}] Subtask update requested for ${subtaskId} with`, updates, '. Handler not fully implemented.');
    // Placeholder: This would involve calling a mutation for updating the subtask
    // For optimistic UI, you might update `displayedSubtasks` here:
    // setDisplayedSubtasks(prev => prev?.map(st => st.id === subtaskId ? {...st, ...updates} : st));
  };

  const handleSubtaskRemove = (subtaskId: string) => {
    console.warn(`[TaskCard ${id}] Subtask removal requested for ${subtaskId}. Handler not fully implemented.`);
    // Placeholder: This would involve calling a mutation for deleting the subtask
    // For optimistic UI, you might update `displayedSubtasks` here:
    // setDisplayedSubtasks(prev => prev?.filter(st => st.id !== subtaskId));
  };

  const style = {
    transform: CSS.Transform.toString(transform),
    transition,
    zIndex: isDragging ? 100 : 'auto',
    boxShadow: isDragging ? '0 10px 15px -3px rgba(0, 0, 0, 0.1), 0 4px 6px -2px rgba(0, 0, 0, 0.05)' : 'none',
  };

  const statusCardStyles = getStatusStyles(status, completed);

  const handleCardClick = (e: React.MouseEvent<HTMLDivElement>) => {
    const target = e.target as HTMLElement;
    if (target.closest('input[type="checkbox"]') ||
        target.closest('[role="button"]') ||
        target.closest('button') ||
        target.closest('.subtask-item-container') ||
        target.closest('.subtask-drag-context')) {
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
          'border',
          statusCardStyles,
          isFocused && 'ring-4 ring-blue-500 dark:ring-blue-400 shadow-xl bg-blue-100 dark:bg-slate-700',
          className,
        )}
      >
        <div
          {...listeners}
          className="p-1 cursor-grab touch-none group-hover:bg-gray-100 dark:group-hover:bg-gray-700 rounded"
          aria-label="Drag to reorder task"
          role="button"
          tabIndex={0}
        >
          <DragHandleDots2Icon className="h-5 w-5 text-gray-400 dark:text-gray-500" />
        </div>

        <div className="flex items-center h-5">
          <Checkbox
            id={`task-checkbox-${id}`}
            checked={!!isSelected}
            onCheckedChange={(checked) => onSelectTask && onSelectTask(id, !!checked)}
            aria-label={`Select task ${title} for prioritization`}
          />
        </div>

        <div className="flex-grow min-w-0" onClick={onEdit ? handleCardClick : undefined} style={onEdit ? {cursor: 'pointer'} : {}} >
          <p className={clsx("text-sm font-medium text-gray-900 dark:text-white truncate", (completed || status === 'completed') && "line-through")}>
            {title}
          </p>
        </div>

        {priorityIcons[priority] && (
          <div className="ml-auto pl-2" title={`Priority: ${priority === 1 ? 'Low' : priority === 2 ? 'Medium' : 'High'}`}>
            {priorityIcons[priority]}
          </div>
        )}

        {displayedSubtasks && displayedSubtasks.length > 0 && (
          <button
            onClick={(e) => { e.stopPropagation(); setIsSubtasksExpanded(!isSubtasksExpanded); }}
            className="p-1 ml-2 text-gray-400 hover:text-gray-600 dark:text-gray-500 dark:hover:text-gray-300 rounded focus:outline-none"
            aria-label={isSubtasksExpanded ? "Collapse subtasks" : "Expand subtasks"}
          >
            {isSubtasksExpanded ? <ChevronDownIcon className="h-4 w-4" /> : <ChevronRightIcon className="h-4 w-4" />}
          </button>
        )}

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

        {status !== 'in_progress' && status !== 'completed' && !completed && (
          <Button
            variant="secondary"
            onClick={(e) => {
              e.stopPropagation();
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

      {isSubtasksExpanded && displayedSubtasks && displayedSubtasks.length > 0 && (
        <SubtaskDndContext
          sensors={subtaskSensors}
          collisionDetection={subtaskClosestCenter}
          onDragEnd={handleSubtaskDragEnd}
          onDragStart={(e) => e.activatorEvent.stopPropagation()}
          onDragOver={(e) => e.activatorEvent.stopPropagation()}
          onDragMove={(e) => e.activatorEvent.stopPropagation()}
        >
          <SubtaskSortableContext
            items={displayedSubtasks.map((s: Task) => s.id)}
            strategy={subtaskVerticalListSortingStrategy}
          >
            <div className="subtask-item-container subtask-drag-context pl-8 pr-2 pb-2 pt-1 bg-gray-50 dark:bg-gray-800/50 rounded-b-lg border-t border-gray-200 dark:border-gray-700 space-y-1">
              {displayedSubtasks.map((subtask: Task) => (
                <SubtaskItem
                  key={subtask.id}
                  subtask={subtask}
                  onUpdate={handleSubtaskUpdate}
                  onRemove={handleSubtaskRemove}
                />
              ))}
            </div>
          </SubtaskSortableContext>
        </SubtaskDndContext>
      )}
    </div>
  );
};