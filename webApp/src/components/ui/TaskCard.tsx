import React, { useState, useEffect } from 'react';
import clsx from 'clsx';
import { Card } from '@radix-ui/themes';
import { Checkbox } from './Checkbox';
import { Button } from './Button';
import { IconButton } from './IconButton';
import { Badge } from './Badge';
import { Task } from '@/api/types';
import SubtaskList from '../features/TaskDetail/SubtaskList';
import { getFocusClasses, getFocusRing } from '@/utils/focusStates';

import {
  DragHandleDots2Icon,
  CheckCircledIcon,
  TrashIcon,
  PlayIcon,
  ChevronDownIcon,
  ChevronRightIcon,
  Pencil2Icon,
  DotsHorizontalIcon,
} from '@radix-ui/react-icons';
import * as DropdownMenu from '@radix-ui/react-dropdown-menu';

import { CSS } from '@dnd-kit/utilities';
import { useSortable } from '@dnd-kit/sortable';

export interface TaskCardProps extends Omit<Task, 'subtasks'> {
  onStartTask: (id: string) => void;
  onEdit?: () => void;
  onStartFocus?: (id: string) => void;
  isSelected?: boolean;
  onSelectTask?: (id: string, selected: boolean) => void;
  onMarkComplete?: (id: string) => void;
  onDeleteTask?: (id: string) => void;
  onFocus?: (id: string) => void;
  subtasks?: Task[];
  className?: string;
  isFocused?: boolean;
}

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
  onFocus,
  isFocused,
  className,
  subtasks: initialSubtasksProp,
}) => {
  const { attributes, listeners, setNodeRef, transform, transition, isDragging } = useSortable({ id });

  const [isSubtasksExpanded, setIsSubtasksExpanded] = useState(false);
  const [cardElement, setCardElement] = useState<HTMLDivElement | null>(null);

  // Synchronize keyboard navigation focus with DOM focus
  useEffect(() => {
    if (isFocused && cardElement) {
      // When keyboard navigation focuses this card, also set DOM focus
      cardElement.focus();
    }
  }, [isFocused, cardElement]);

  const handleFocus = () => {
    // When DOM focus happens, notify the keyboard navigation system
    if (onFocus) {
      onFocus(id);
    }
  };

  const handleBlur = () => {
    // Handle DOM blur if needed
  };

  // Combined ref callback for both DnD and focus management
  const setRefs = (node: HTMLDivElement | null) => {
    setNodeRef(node);
    setCardElement(node);
  };

  const style = {
    transform: CSS.Transform.toString(transform),
    transition: isDragging ? transition : 'all 0.3s cubic-bezier(0.4, 0, 0.2, 1)',
    zIndex: isDragging ? 100 : 'auto',
    boxShadow: isDragging ? '0 25px 50px -12px rgba(139, 92, 246, 0.25), 0 0 30px rgba(139, 92, 246, 0.3)' : 'none',
  };

  const handleCardClick = (e: React.MouseEvent<HTMLDivElement>) => {
    const target = e.target as HTMLElement;
    if (
      target.closest('input[type="checkbox"]') ||
      target.closest('[role="button"]') ||
      target.closest('button') ||
      target.closest('.subtask-item-container') ||
      target.closest('.subtask-drag-context')
    ) {
      return;
    }

    // Focus this task when clicked
    if (onFocus) {
      onFocus(id);
    }

    if (onEdit) {
      onEdit();
    }
  };

  // Determine card variant based on status
  const getCardVariant = () => {
    if (completed || status === 'completed') return 'ghost';
    if (status === 'in_progress') return 'surface';
    return 'surface';
  };

  return (
    <div
      ref={setRefs}
      style={style}
      {...attributes}
      className={clsx(
        'task-card-wrapper',
        isDragging && 'opacity-50',
        // Suppress browser's default focus ring - we use our custom focus system instead
        'outline-none focus:outline-none focus-visible:outline-none',
      )}
      tabIndex={0}
      onFocus={handleFocus}
      onBlur={handleBlur}
    >
      <Card
        asChild={!!onEdit}
        variant={getCardVariant()}
        size="2"
        className={clsx(
          'task-card relative cursor-pointer',
          '[&]:focus-within:outline-none [&]:focus:outline-none [&]:focus-visible:outline-none',
          getFocusClasses(),
          isFocused && getFocusRing('focused'),
          isSelected && !completed && 'ring-2 ring-brand-primary/50',
          isSelected && completed && 'ring-2 ring-ui-border/50',
          completed && 'opacity-70',
          status === 'in_progress' && 'border-brand-primary',
          className,
        )}
        onClick={onEdit ? handleCardClick : undefined}
      >
        <div className="flex items-center gap-3 p-4">
          {/* Priority indicator */}
          {priority && (
            <div
              className={clsx(
                'w-2 h-2 rounded-full flex-shrink-0',
                priority === 3 && 'bg-danger-bg',
                priority === 2 && 'bg-warning-strong',
                priority === 1 && 'bg-info-electric',
                completed && 'bg-text-disabled opacity-50',
              )}
            />
          )}

          {/* Drag handle */}
          <IconButton
            {...listeners}
            variant="ghost"
            size="1"
            aria-label="Drag to reorder task"
            className={clsx('cursor-grab active:cursor-grabbing', completed && 'opacity-50')}
          >
            <DragHandleDots2Icon />
          </IconButton>

          {/* Selection checkbox */}
          <Checkbox
            id={`task-checkbox-${id}`}
            checked={!!isSelected}
            onCheckedChange={(checked) => onSelectTask && onSelectTask(id, !!checked)}
            aria-label={`Select task ${title} for prioritization`}
          />

          {/* Task title */}
          <div className="flex-grow min-w-0">
            <p
              className={clsx(
                'text-sm font-medium break-words leading-tight',
                completed && 'line-through text-text-muted',
                !completed && 'text-text-primary',
              )}
            >
              {title}
            </p>
          </div>

          {/* Subtask toggle */}
          {initialSubtasksProp && initialSubtasksProp.length > 0 && (
            <IconButton
              onClick={(e) => {
                e.stopPropagation();
                setIsSubtasksExpanded(!isSubtasksExpanded);
              }}
              variant="ghost"
              size="1"
              aria-label={isSubtasksExpanded ? 'Collapse subtasks' : 'Expand subtasks'}
            >
              {isSubtasksExpanded ? <ChevronDownIcon /> : <ChevronRightIcon />}
            </IconButton>
          )}

          {/* Status indicator or Start button */}
          {status === 'in_progress' && (
            <Badge variant="soft" color="blue" size="1">
              In Progress
            </Badge>
          )}

          {status !== 'in_progress' && status !== 'completed' && !completed && (
            <Button
              variant="soft"
              size="1"
              onClick={(e) => {
                e.stopPropagation();
                onStartTask(id);
              }}
            >
              Start
            </Button>
          )}

          {/* Actions Dropdown Menu */}
          <DropdownMenu.Root>
            <DropdownMenu.Trigger asChild>
              <IconButton variant="ghost" size="1" aria-label="Task actions" onClick={(e) => e.stopPropagation()}>
                <DotsHorizontalIcon />
              </IconButton>
            </DropdownMenu.Trigger>

            <DropdownMenu.Portal>
              <DropdownMenu.Content
                className="min-w-[160px] bg-ui-element-bg rounded-lg border border-ui-border shadow-lg p-1 z-50"
                sideOffset={5}
                onClick={(e) => e.stopPropagation()}
              >
                {onEdit && (
                  <DropdownMenu.Item
                    className="flex items-center gap-2 px-3 py-2 text-sm rounded-md text-text-primary hover:bg-ui-interactive-bg-hover cursor-pointer outline-none focus:bg-ui-interactive-bg-hover"
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
                    className="flex items-center gap-2 px-3 py-2 text-sm rounded-md text-brand-primary hover:bg-ui-interactive-bg-hover cursor-pointer outline-none focus:bg-ui-interactive-bg-hover"
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
                    className="flex items-center gap-2 px-3 py-2 text-sm rounded-md text-success-strong hover:bg-ui-interactive-bg-hover cursor-pointer outline-none focus:bg-ui-interactive-bg-hover"
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
                      className="flex items-center gap-2 px-3 py-2 text-sm rounded-md text-destructive hover:bg-ui-interactive-bg-hover cursor-pointer outline-none focus:bg-ui-interactive-bg-hover"
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
      </Card>

      {isSubtasksExpanded && initialSubtasksProp && initialSubtasksProp.length > 0 && (
        <div
          className={clsx(
            'pl-8 pr-4 pb-3 pt-2 mt-2',
            'bg-ui-element-bg/60 rounded-b-xl border border-ui-border/50',
            completed && 'opacity-70',
          )}
        >
          <SubtaskList parentTaskId={id} showAddSubtask={false} compact={true} className="space-y-1" />
        </div>
      )}
    </div>
  );
};
