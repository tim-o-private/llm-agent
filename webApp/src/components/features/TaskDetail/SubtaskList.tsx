import React, { useState } from 'react';
import {
  DndContext,
  closestCenter,
  KeyboardSensor,
  PointerSensor,
  useSensor,
  useSensors,
  DragEndEvent,
} from '@dnd-kit/core';
import {
  arrayMove,
  SortableContext,
  sortableKeyboardCoordinates,
  verticalListSortingStrategy,
  useSortable,
} from '@dnd-kit/sortable';
import { CSS } from '@dnd-kit/utilities';
import { useTaskStore } from '@/stores/useTaskStore';
import { Task } from '@/api/types';
import { Input } from '@/components/ui/Input';
import { Button } from '@/components/ui/Button';
import { TrashIcon, Pencil1Icon, DragHandleDots2Icon, PlusIcon } from '@radix-ui/react-icons'; // For delete/edit icons
import { 
  getStatusContainerStyles, 
  getStatusTextStyles, 
  getStatusButtonStyles 
} from '@/utils/statusStyles';
import clsx from 'clsx';

interface SubtaskListProps {
  parentTaskId: string;
  showAddSubtask?: boolean; // New prop to control add functionality
  className?: string; // New prop for custom styling
  compact?: boolean; // New prop for compact display in TaskCard
  // New callback props for change tracking
  onSubtaskChange?: () => void; // Called when any subtask change occurs
  onSubtaskReorder?: (subtasks: Task[]) => void; // Called when subtasks are reordered
  onSubtaskCreate?: (subtaskData: Partial<Task>) => void; // Called when a new subtask is created
  onSubtaskUpdate?: (id: string, updates: Partial<Task>) => void; // Called when a subtask is updated
  onSubtaskDelete?: (id: string) => void; // Called when a subtask is deleted
  // Optimistic state for immediate UI feedback
  optimisticSubtasks?: Task[] | null; // When provided, use this instead of store data
}

interface SubtaskListItemProps {
  subtask: Task;
  onUpdate: (id: string, updates: Partial<Task>) => void; // Placeholder for update functionality
  onRemove: (id: string) => void;
  compact?: boolean; // New prop for compact display
}

const SubtaskListItem: React.FC<SubtaskListItemProps> = ({ subtask, onUpdate, onRemove, compact }) => {
  const [isEditing, setIsEditing] = useState(false);
  const [editTitle, setEditTitle] = useState(subtask.title);

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
  };

  const handleUpdate = () => {
    if (editTitle.trim() !== subtask.title) {
      onUpdate(subtask.id, { title: editTitle.trim() });
    }
    setIsEditing(false);
  };

  return (
    <div 
      ref={setNodeRef} 
      style={style}
      className={clsx(
        'flex items-center justify-between hover:bg-ui-element-bg-hover',
        compact ? 'p-2' : 'p-3',
        getStatusContainerStyles({
          completed: subtask.status === 'completed',
          status: subtask.status,
          variant: compact ? 'compact' : 'item'
        })
      )}
    >
      <div className="flex items-center flex-grow">
        <button
          className={clsx(
            getStatusButtonStyles({ completed: subtask.status === 'completed' }),
            "cursor-grab active:cursor-grabbing",
            compact ? 'mr-1 p-0.5' : 'mr-2 p-1'
          )}
          {...attributes}
          {...listeners}
        >
          <DragHandleDots2Icon className={compact ? "w-3 h-3" : "w-4 h-4"} />
        </button>
        
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
            className={`flex-grow mr-2 text-sm ${compact ? 'h-6' : 'h-8'}`}
          />
        ) : (
          <span 
              className={clsx(
                'flex-grow cursor-pointer',
                compact ? 'text-sm' : '',
                getStatusTextStyles({ completed: subtask.status === 'completed' })
              )}
              onClick={() => setIsEditing(true)} // Click to edit title
          >
              {subtask.title}
          </span>
        )}
      </div>
      
      <div className={`flex items-center ml-2 ${compact ? 'space-x-0.5' : 'space-x-1'}`}>
        <Button 
          onClick={() => setIsEditing(!isEditing)} 
          aria-label="Edit subtask" 
          variant="outline"
          className={compact ? "p-0.5 h-6 w-6" : "p-1 h-8 w-8"}
        >
            <Pencil1Icon className={compact ? "w-3 h-3" : "w-4 h-4"} />
        </Button>
        <Button 
          onClick={() => onRemove(subtask.id)} 
          aria-label="Remove subtask" 
          variant="outline"
          className={`text-destructive hover:text-destructive ${compact ? "p-0.5 h-6 w-6" : "p-1 h-8 w-8"}`}
        >
            <TrashIcon className={compact ? "w-3 h-3" : "w-4 h-4"} />
        </Button>
      </div>
    </div>
  );
};

const SubtaskList: React.FC<SubtaskListProps> = ({ 
  parentTaskId, 
  showAddSubtask = true, 
  className, 
  compact,
  onSubtaskChange,
  onSubtaskReorder,
  onSubtaskCreate,
  onSubtaskUpdate,
  onSubtaskDelete,
  optimisticSubtasks
}) => {
  const subtasks = useTaskStore((state) => state.getSubtasksByParentId(parentTaskId));
  const { createTask, updateTask, deleteTask } = useTaskStore.getState(); // Get actions
  const [newSubtaskTitle, setNewSubtaskTitle] = useState('');
  const [isAddingSubtask, setIsAddingSubtask] = useState(false);

  // Use optimistic subtasks if provided, otherwise use store data
  const displaySubtasks = optimisticSubtasks || subtasks;

  // DND functionality sensors
  const sensors = useSensors(
    useSensor(PointerSensor),
    useSensor(KeyboardSensor, {
      coordinateGetter: sortableKeyboardCoordinates,
    })
  );

  const handleDragEnd = (event: DragEndEvent) => {
    const { active, over } = event;

    if (active.id !== over?.id && over) {
      const oldIndex = displaySubtasks.findIndex(subtask => subtask.id === active.id);
      const newIndex = displaySubtasks.findIndex(subtask => subtask.id === over.id);

      if (oldIndex === -1 || newIndex === -1) {
        console.warn('[SubtaskList] handleDragEnd: Subtask not found in current list. Aborting.');
        return;
      }

      // Create the reordered array
      const reorderedSubtasks = arrayMove(displaySubtasks, oldIndex, newIndex);
      
      // If callbacks are provided, use them instead of directly updating store
      if (onSubtaskReorder) {
        onSubtaskReorder(reorderedSubtasks);
        onSubtaskChange?.();
      } else {
        // Fallback to direct store update for backward compatibility
        reorderedSubtasks.forEach((subtask, index) => {
          if (subtask.subtask_position !== index) {
            updateTask(subtask.id, { subtask_position: index });
          }
        });
      }
    }
  };

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
      subtask_position: displaySubtasks.length, // Add at the end
    } as Omit<Task, 'id' | 'created_at' | 'updated_at' | 'completed' | 'subtasks'>;

    try {
      if (onSubtaskCreate) {
        onSubtaskCreate(newSubtaskData);
        onSubtaskChange?.();
      } else {
        // Fallback to direct store update for backward compatibility
        await createTask(newSubtaskData);
      }
      setNewSubtaskTitle('');
      setIsAddingSubtask(false);
    } catch (error) {
      console.error("Failed to create subtask:", error);
      // Handle error (e.g., show toast)
    }
  };

  const handleUpdateSubtask = (id: string, updates: Partial<Task>) => {
    if (onSubtaskUpdate) {
      onSubtaskUpdate(id, updates);
      onSubtaskChange?.();
    } else {
      // Fallback to direct store update for backward compatibility
      updateTask(id, updates);
    }
  };

  const handleRemoveSubtask = (id: string) => {
    if (onSubtaskDelete) {
      onSubtaskDelete(id);
      onSubtaskChange?.();
    } else {
      // Fallback to direct store update for backward compatibility
      deleteTask(id);
    }
  };

  return (
    <div className={`space-y-3 ${className || ''}`}>
      {/* Add Subtask Button/Input */}
      {!isAddingSubtask && showAddSubtask && (
        <Button 
          type="button" 
          onClick={() => setIsAddingSubtask(true)}
          variant="outline"
          className="w-full flex items-center justify-center py-2 border-2 border-dashed border-ui-border hover:border-ui-border-focus hover:bg-ui-element-bg-hover"
        >
          <PlusIcon className="w-4 h-4 mr-2" />
          Add Subtask
        </Button>
      )}

      {isAddingSubtask && showAddSubtask && (
        <div className="flex items-center space-x-2 p-3 border-2 border-dashed border-ui-border-focus rounded-md bg-ui-element-bg">
          <Input 
            type="text"
            value={newSubtaskTitle}
            onChange={(e) => setNewSubtaskTitle(e.target.value)}
            placeholder="Enter subtask title..."
            className="flex-grow"
            autoFocus
            onKeyDown={(e) => {
              if (e.key === 'Enter') {
                e.preventDefault();
                handleAddSubtask();
              }
              if (e.key === 'Escape') {
                setNewSubtaskTitle('');
                setIsAddingSubtask(false);
              }
            }}
          />
          <Button 
            type="button" 
            onClick={handleAddSubtask}
            disabled={!newSubtaskTitle.trim()}
            variant="solid"
            className="px-3"
          >
            Add
          </Button>
          <Button 
            type="button" 
            onClick={() => {
              setNewSubtaskTitle('');
              setIsAddingSubtask(false);
            }}
            variant="outline"
            className="px-3"
          >
            Cancel
          </Button>
        </div>
      )}

      {/* Subtasks List */}
      {displaySubtasks.length > 0 ? (
        <DndContext sensors={sensors} collisionDetection={closestCenter} onDragEnd={handleDragEnd}>
          <SortableContext items={displaySubtasks.map(s => s.id)} strategy={verticalListSortingStrategy}>
            <div className={compact ? "space-y-1" : "space-y-2"}>
              {displaySubtasks.map(subtask => (
                <SubtaskListItem 
                  key={subtask.id} 
                  subtask={subtask} 
                  onUpdate={handleUpdateSubtask}
                  onRemove={handleRemoveSubtask}
                  compact={compact}
                />
              ))}
            </div>
          </SortableContext>
        </DndContext>
      ) : (
        !showAddSubtask && (
          <p className={`text-text-muted text-center py-4 italic ${compact ? 'text-xs py-2' : 'text-sm'}`}>
            No subtasks yet.
          </p>
        )
      )}
    </div>
  );
};

export default SubtaskList;