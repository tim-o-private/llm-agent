import React, { useState, useEffect } from 'react';
import clsx from 'clsx';
import { Checkbox } from './Checkbox';
import { Button } from './Button';
import { Task, TaskPriority, TaskStatus } from '@/api/types';
import { SubtaskItem } from '../features/TaskDetail/SubtaskItem';
import { useUpdateSubtaskOrder } from '@/api/hooks/useTaskHooks';

import {
  DragHandleDots2Icon,
  CheckCircledIcon,
  TrashIcon,
  PlayIcon,
  ChevronDownIcon,
  ChevronRightIcon,
  Pencil2Icon,
  DotsHorizontalIcon
} from '@radix-ui/react-icons';
import * as DropdownMenu from '@radix-ui/react-dropdown-menu';

import { CSS } from '@dnd-kit/utilities';
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
  useSortable,
  arrayMove as subtaskArrayMove,
  SortableContext as SubtaskSortableContext,
  sortableKeyboardCoordinates as subtaskSortableKeyboardCoordinates,
  verticalListSortingStrategy as subtaskVerticalListSortingStrategy,
} from '@dnd-kit/sortable';


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
  1: null,
  2: null,
  3: null,
};

const getStatusStyles = (status: TaskStatus, completed: boolean) => {
  if (completed || status === 'completed') return 'opacity-70 border-ui-border bg-ui-element-bg/60';
  if (status === 'in_progress') return 'border-brand-primary bg-ui-element-bg/80';
  if (status === 'planning') return 'border-brand-primary bg-ui-element-bg/80';
  return 'border-ui-border bg-ui-element-bg/80 hover:border-ui-border-hover';
};

const getPriorityGlow = (priority: TaskPriority, completed: boolean) => {
  if (completed) return '';
  
  switch (priority) {
    case 3: return 'shadow-lg shadow-danger/30';
    case 2: return 'shadow-md shadow-warning/20';
    case 1: return 'shadow-sm';
    default: return '';
  }
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
  const [isHovered, setIsHovered] = useState(false);

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
    transition: isDragging ? transition : 'all 0.3s cubic-bezier(0.4, 0, 0.2, 1)',
    zIndex: isDragging ? 100 : 'auto',
    boxShadow: isDragging ? '0 25px 50px -12px rgba(139, 92, 246, 0.25), 0 0 30px rgba(139, 92, 246, 0.3)' : 'none',
  };

  const statusCardStyles = getStatusStyles(status, completed);
  const priorityGlow = getPriorityGlow(priority, completed);

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
    <div 
      ref={setNodeRef} 
      style={style} 
      {...attributes} 
      className={clsx('task-card-wrapper', isDragging && 'dragging-shadow')}
      onMouseEnter={() => setIsHovered(true)}
      onMouseLeave={() => setIsHovered(false)}
    >
      <div
        className={clsx(
          'task-card relative overflow-hidden',
          'backdrop-blur-sm',
          'p-4 rounded-xl shadow-elevated',
          'flex items-center space-x-3 group',
          'border-2 transition-all duration-300 ease-out',
          'min-h-[3.5rem]',
          
          // Interaction states - different for completed vs active tasks
          !completed && !isDragging && 'hover:shadow-lg hover:scale-[1.02] hover:-translate-y-1',
          completed && !isDragging && 'hover:shadow-md hover:scale-[1.01] hover:-translate-y-0.5',
          
          statusCardStyles,
          priorityGlow,
          
          // Focus ring follows keyboard selection regardless of status
          isFocused && 'ring-4 ring-blue-500/50 shadow-xl transform -translate-y-1 scale-[1.02]',
          
          // Selected state
          isSelected && !completed && 'ring-2 ring-brand-primary/50',
          isSelected && completed && 'ring-2 ring-ui-border/50',
          
          // In-progress glow (more subtle)
          status === 'in_progress' && isFocused && 'shadow-brand-primary/20 animate-pulse',
          
          className,
        )}
      >
        {/* Glassy overlay for extra depth */}
        <div className="absolute inset-0 rounded-xl bg-gradient-to-br from-ui-surface/10 to-transparent pointer-events-none" />
        
        {/* Animated background gradient for active states - only for non-completed */}
        {(status === 'in_progress' || isFocused) && !completed && (
          <div className="absolute inset-0 bg-gradient-to-r from-brand-primary/5 via-brand-secondary/5 to-brand-primary/5 animate-gradient-shift opacity-50 rounded-xl" />
        )}
        
        {/* Priority indicator - corner dot instead of bar, muted for completed */}
        {priority > 0 && (
          <div 
            className={clsx(
              'absolute top-2 right-2 w-2 h-2 rounded-full z-10',
              !completed && priority === 3 && 'bg-red-500',
              !completed && priority === 2 && 'bg-amber-500',
              !completed && priority === 1 && 'bg-blue-500',
              completed && 'bg-gray-400 opacity-50'
            )}
          />
        )}

        <div
          {...listeners}
          className={clsx(
            'p-2 cursor-grab touch-none rounded-lg transition-all duration-200 relative z-10',
            !completed && 'hover:bg-ui-interactive-bg-hover backdrop-blur-sm hover:shadow-lg',
            completed && 'hover:bg-ui-interactive-bg-hover/60 backdrop-blur-sm',
            'active:scale-95'
          )}
          aria-label="Drag to reorder task"
          role="button"
          tabIndex={0}
        >
          <DragHandleDots2Icon className={clsx(
            "h-5 w-5 transition-colors duration-200",
            !completed && "text-text-muted group-hover:text-text-secondary",
            completed && "text-text-muted/60"
          )} />
        </div>

        <div className="flex items-center h-5 relative z-10">
          <Checkbox
            id={`task-checkbox-${id}`}
            checked={!!isSelected}
            onCheckedChange={(checked) => onSelectTask && onSelectTask(id, !!checked)}
            aria-label={`Select task ${title} for prioritization`}
            className="transition-all duration-200 hover:scale-110"
          />
        </div>

        <div 
          className="flex-grow min-w-0 cursor-pointer relative z-10" 
          onClick={onEdit ? handleCardClick : undefined}
        >
          <p className={clsx(
            "text-sm font-medium transition-all duration-200 relative z-10",
            "break-words leading-tight",
            "overflow-hidden",
            !completed && "group-hover:text-brand-primary text-text-primary",
            completed && "line-through text-text-muted"
          )}>
            {title}
          </p>
          
          {/* Subtle shimmer effect on hover - only for non-completed */}
          {isHovered && !completed && (
            <div className="absolute inset-0 bg-gradient-to-r from-transparent via-ui-surface/5 to-transparent animate-shimmer pointer-events-none" />
          )}
        </div>

        {displayedSubtasks && displayedSubtasks.length > 0 && (
          <button
            onClick={(e) => { e.stopPropagation(); setIsSubtasksExpanded(!isSubtasksExpanded); }}
            className={clsx(
              "p-2 ml-2 rounded-lg transition-all duration-200 relative z-10",
              !completed && "text-text-muted hover:text-text-secondary",
              !completed && "hover:bg-ui-interactive-bg-hover backdrop-blur-sm",
              completed && "text-text-muted/60 hover:text-text-muted",
              completed && "hover:bg-ui-interactive-bg-hover/60 backdrop-blur-sm",
              "focus:outline-none focus:ring-2 focus:ring-ui-border-focus",
              isSubtasksExpanded && !completed && "bg-ui-interactive-bg-active text-text-secondary",
              isSubtasksExpanded && completed && "bg-ui-interactive-bg-active/60 text-text-muted"
            )}
            aria-label={isSubtasksExpanded ? "Collapse subtasks" : "Expand subtasks"}
          >
            {isSubtasksExpanded ? 
              <ChevronDownIcon className="h-4 w-4 transition-transform duration-200" /> : 
              <ChevronRightIcon className="h-4 w-4 transition-transform duration-200" />
            }
          </button>
        )}

        <div className="ml-auto flex items-center space-x-2 pl-2 relative z-10">
          {/* Status indicator or Start button */}
          {status === 'in_progress' && (
            <span className={clsx(
              "text-xs font-semibold flex-shrink-0 px-2 py-1 rounded-full",
              "bg-brand-surface backdrop-blur-sm",
              "text-brand-primary border border-brand-primary/30",
              !completed && "animate-pulse"
            )}>
              In Progress
            </span>
          )}
          
          {status !== 'in_progress' && status !== 'completed' && !completed && (
            <Button
              variant="secondary"
              onClick={(e) => {
                e.stopPropagation();
                onStartTask(id);
              }}
              className={clsx(
                "flex-shrink-0 px-3 py-1.5 text-xs font-medium",
                "transition-all duration-200 hover:shadow-lg hover:scale-105",
                "bg-ui-interactive-bg backdrop-blur-sm",
                "hover:bg-ui-interactive-bg-hover",
                "border border-ui-border"
              )}
            >
              Start
            </Button>
          )}

          {/* Actions Dropdown Menu */}
          <DropdownMenu.Root>
            <DropdownMenu.Trigger asChild>
              <button
                className={clsx(
                  "p-2 rounded-full transition-all duration-200 relative z-10",
                  !completed && "text-text-secondary hover:text-text-primary",
                  !completed && "hover:bg-ui-interactive-bg-hover backdrop-blur-sm",
                  completed && "text-text-muted/60 hover:text-text-muted",
                  completed && "hover:bg-ui-interactive-bg-hover/60 backdrop-blur-sm",
                  "hover:scale-110 active:scale-95",
                  "focus:outline-none focus:ring-2 focus:ring-ui-border-focus"
                )}
                aria-label="Task actions"
                onClick={(e) => e.stopPropagation()}
              >
                <DotsHorizontalIcon className="h-4 w-4" />
              </button>
            </DropdownMenu.Trigger>

            <DropdownMenu.Portal>
              <DropdownMenu.Content
                className={clsx(
                  "min-w-[160px] bg-ui-element-bg backdrop-blur-md",
                  "rounded-lg border border-ui-border shadow-lg",
                  "p-1 z-50"
                )}
                sideOffset={5}
                onClick={(e) => e.stopPropagation()}
              >
                {onEdit && (
                  <DropdownMenu.Item
                    className={clsx(
                      "flex items-center space-x-2 px-3 py-2 text-sm rounded-md",
                      "text-text-primary hover:bg-ui-interactive-bg-hover",
                      "cursor-pointer outline-none",
                      "focus:bg-ui-interactive-bg-hover"
                    )}
                    onClick={(e) => {
                      e.stopPropagation();
                      onEdit();
                    }}
                  >
                    <Pencil2Icon className="h-4 w-4" />
                    <span>Edit Task</span>
                  </DropdownMenu.Item>
                )}

                {onStartFocus && !completed && status !== 'completed' && (
                  <DropdownMenu.Item
                    className={clsx(
                      "flex items-center space-x-2 px-3 py-2 text-sm rounded-md",
                      "text-brand-primary hover:bg-ui-interactive-bg-hover",
                      "cursor-pointer outline-none",
                      "focus:bg-ui-interactive-bg-hover"
                    )}
                    onClick={(e) => {
                      e.stopPropagation();
                      onStartFocus(id);
                    }}
                  >
                    <PlayIcon className="h-4 w-4" />
                    <span>Focus on Task</span>
                  </DropdownMenu.Item>
                )}

                {onMarkComplete && !completed && status !== 'completed' && (
                  <DropdownMenu.Item
                    className={clsx(
                      "flex items-center space-x-2 px-3 py-2 text-sm rounded-md",
                      "text-success-strong hover:bg-ui-interactive-bg-hover",
                      "cursor-pointer outline-none",
                      "focus:bg-ui-interactive-bg-hover"
                    )}
                    onClick={(e) => {
                      e.stopPropagation();
                      onMarkComplete(id);
                    }}
                  >
                    <CheckCircledIcon className="h-4 w-4" />
                    <span>Mark Complete</span>
                  </DropdownMenu.Item>
                )}

                {onDeleteTask && (
                  <>
                    <DropdownMenu.Separator className="h-px bg-ui-border my-1" />
                    <DropdownMenu.Item
                      className={clsx(
                        "flex items-center space-x-2 px-3 py-2 text-sm rounded-md",
                        "text-destructive hover:bg-ui-interactive-bg-hover",
                        "cursor-pointer outline-none",
                        "focus:bg-ui-interactive-bg-hover"
                      )}
                      onClick={(e) => {
                        e.stopPropagation();
                        onDeleteTask(id);
                      }}
                    >
                      <TrashIcon className="h-4 w-4" />
                      <span>Delete Task</span>
                    </DropdownMenu.Item>
                  </>
                )}
              </DropdownMenu.Content>
            </DropdownMenu.Portal>
          </DropdownMenu.Root>
        </div>
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
            <div className={clsx(
              "subtask-item-container subtask-drag-context",
              "pl-8 pr-4 pb-3 pt-2 mt-2",
              "backdrop-blur-sm bg-ui-element-bg/60",
              "rounded-b-xl border-t border-ui-border/50",
              "space-y-2 animate-slide-down",
              completed && "opacity-70"
            )}>
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