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
      className="flex items-center justify-between p-3 border border-ui-border rounded-md hover:bg-ui-element-bg-hover bg-ui-element-bg"
    >
      <div className="flex items-center flex-grow">
        <button
          className="mr-2 p-1 text-text-muted hover:text-text-primary cursor-grab active:cursor-grabbing"
          {...attributes}
          {...listeners}
        >
          <DragHandleDots2Icon className="w-4 h-4" />
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
      </div>
      
      <div className="flex items-center space-x-1 ml-2">
        <Button 
          onClick={() => setIsEditing(!isEditing)} 
          aria-label="Edit subtask" 
          variant="secondary"
          className="p-1 h-8 w-8"
        >
            <Pencil1Icon className="w-4 h-4" />
        </Button>
        <Button 
          onClick={() => onRemove(subtask.id)} 
          aria-label="Remove subtask" 
          variant="secondary"
          className="p-1 h-8 w-8 text-destructive hover:text-destructive"
        >
            <TrashIcon className="w-4 h-4" />
        </Button>
      </div>
    </div>
  );
};

const SubtaskList: React.FC<SubtaskListProps> = ({ parentTaskId }) => {
  const subtasks = useTaskStore((state) => state.getSubtasksByParentId(parentTaskId));
  const { createTask, updateTask, deleteTask } = useTaskStore.getState(); // Get actions
  const [newSubtaskTitle, setNewSubtaskTitle] = useState('');
  const [isAddingSubtask, setIsAddingSubtask] = useState(false);

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
      const oldIndex = subtasks.findIndex(subtask => subtask.id === active.id);
      const newIndex = subtasks.findIndex(subtask => subtask.id === over.id);

      if (oldIndex === -1 || newIndex === -1) {
        console.warn('[SubtaskList] handleDragEnd: Subtask not found in current list. Aborting.');
        return;
      }

      // Optimistically reorder subtasks
      const reorderedSubtasks = arrayMove(subtasks, oldIndex, newIndex);
      
      // Update positions in the store
      reorderedSubtasks.forEach((subtask, index) => {
        if (subtask.subtask_position !== index) {
          updateTask(subtask.id, { subtask_position: index });
        }
      });
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
      subtask_position: subtasks.length, // Add at the end
    } as Omit<Task, 'id' | 'created_at' | 'updated_at' | 'completed' | 'subtasks'>;

    try {
      await createTask(newSubtaskData);
      setNewSubtaskTitle('');
      setIsAddingSubtask(false);
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
    <div className="space-y-3">
      {/* Add Subtask Button/Input */}
      {!isAddingSubtask ? (
        <Button 
          type="button" 
          onClick={() => setIsAddingSubtask(true)}
          variant="secondary"
          className="w-full flex items-center justify-center py-2 border-2 border-dashed border-ui-border hover:border-ui-border-focus hover:bg-ui-element-bg-hover"
        >
          <PlusIcon className="w-4 h-4 mr-2" />
          Add Subtask
        </Button>
      ) : (
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
            variant="primary"
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
            variant="secondary"
            className="px-3"
          >
            Cancel
          </Button>
        </div>
      )}

      {/* Subtasks List */}
      {subtasks.length > 0 ? (
        <DndContext sensors={sensors} collisionDetection={closestCenter} onDragEnd={handleDragEnd}>
          <SortableContext items={subtasks.map(s => s.id)} strategy={verticalListSortingStrategy}>
            <div className="space-y-2">
              {subtasks.map(subtask => (
                <SubtaskListItem 
                  key={subtask.id} 
                  subtask={subtask} 
                  onUpdate={handleUpdateSubtask}
                  onRemove={handleRemoveSubtask}
                />
              ))}
            </div>
          </SortableContext>
        </DndContext>
      ) : (
        <p className="text-sm text-text-muted text-center py-4 italic">No subtasks yet. Add one above to get started.</p>
      )}
    </div>
  );
};

export default SubtaskList; 