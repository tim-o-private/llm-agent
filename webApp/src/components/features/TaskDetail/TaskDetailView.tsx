import React, { useState, useEffect, useCallback, useRef } from 'react';
import * as RadixDialog from '@radix-ui/react-dialog';
import { Cross2Icon, TrashIcon } from '@radix-ui/react-icons';
import { z } from 'zod';
import { useTaskStore, useInitializeTaskStore } from '@/stores/useTaskStore';
import { Task, TaskStatus, TaskPriority } from '@/api/types';
import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/Input';
import { Textarea } from '@/components/ui/Textarea';
import { Label } from '@/components/ui/Label';
import { Spinner } from '@/components/ui/Spinner';
import { toast } from '@/components/ui/toast';
import { SubtaskItem } from './SubtaskItem';
import { useObjectEditManager } from '@/hooks/useObjectEditManager';
import { useReorderableList } from '@/hooks/useReorderableList';
import { Controller, DefaultValues } from 'react-hook-form';
import { cloneDeep } from 'lodash-es';
import { useTaskDetailStateManager } from '@/hooks/useTaskDetailStateManager';

// Dnd-kit imports - REINSTATE THESE
import {
  DndContext,
  closestCenter,
} from '@dnd-kit/core';
import {
  SortableContext,
  verticalListSortingStrategy,
} from '@dnd-kit/sortable';

interface TaskDetailViewProps {
  taskId: string | null;
  isOpen: boolean;
  onOpenChange: (isOpen: boolean) => void;
  onTaskUpdated: () => void;
  onDeleteTaskFromDetail?: (taskId: string) => void;
}

// Define the type for our form data
export type TaskFormData = {
  title: string;
  description?: string | null;
  notes?: string | null;
  category?: string | null;
  due_date?: string | null;
  status: TaskStatus;
  priority: TaskPriority;
};

// Define constants for enum values BEFORE using them in the schema
const ALL_STATUSES = ['pending', 'planning', 'in_progress', 'completed', 'skipped', 'deferred'] as const;
const ALL_PRIORITIES: { label: string; value: TaskPriority }[] = [
  { label: 'None', value: 0 },
  { label: 'Low', value: 1 },
  { label: 'Medium', value: 2 },
  { label: 'High', value: 3 },
];

// Optional: Define Zod schema for validation
const taskFormSchema = z.object({
  title: z.string().min(1, 'Title is required'),
  description: z.string().nullable().optional(),
  notes: z.string().nullable().optional(),
  category: z.string().nullable().optional(),
  due_date: z.string().nullable().optional(), 
  status: z.enum(ALL_STATUSES),
  priority: z.union([
    z.literal(0),
    z.literal(1),
    z.literal(2),
    z.literal(3),
  ]),
});

export const TaskDetailView: React.FC<TaskDetailViewProps> = ({
  taskId,
  isOpen,
  onOpenChange,
  onTaskUpdated,
  onDeleteTaskFromDetail,
}) => {
  useInitializeTaskStore();

  const storeParentTask = useTaskStore(state => taskId ? state.getTaskById(taskId) : undefined);
  const storeSubtasks = useTaskStore(state => taskId ? state.getSubtasksByParentId(taskId) : []);
  const storeActionsFromHook = useTaskStore.getState();

  const {
    formMethods,
    resetForm: resetParentForm,
  } = useObjectEditManager<TaskFormData>({
    zodSchema: taskFormSchema,
    defaultValues: {
      title: '',
      description: '',
      notes: '',
      category: '',
      due_date: '',
      status: 'pending',
      priority: 0,
    },
  });
  const { register, control, formState: { errors }, getValues: getParentFormValues } = formMethods;

  const {
    items: localSubtasks,
    setItems: setLocalSubtasks,
    dndSensors: subtaskDndSensors,
    handleDragStart: handleSubtaskDragStart,
    handleDragEnd: handleSubtaskDragEnd,
    handleLocalAddItem: handleLocalAddSubtask,
  } = useReorderableList<Task>({
    listName: 'Subtasks',
    initialItems: [],
    getItemId: (item) => item.id,
  });
  
  const {
    isModalDirty,
    initializeState,
    resetState,
    handleSaveChanges,
  } = useTaskDetailStateManager({
    taskId,
    storeParentTask,
    getParentFormValues,
    localSubtasks,
    storeActions: {
      updateTask: storeActionsFromHook.updateTask,
      deleteTask: storeActionsFromHook.deleteTask,
      createTask: storeActionsFromHook.createTask,
    },
    onSaveComplete: () => {
      onTaskUpdated();
      onOpenChange(false);
    },
  });
  
  // Keep track of previous taskId and isOpen state to control re-initialization
  const prevTaskIdRef = useRef<string | null>();
  const prevIsOpenRef = useRef<boolean>();
  
  useEffect(() => {
    // Only re-initialize if:
    // 1. The modal is opening (isOpen becomes true)
    // 2. The taskId changes while the modal is already open
    const hasTaskIdChanged = taskId !== prevTaskIdRef.current;
    const isOpening = isOpen && !prevIsOpenRef.current;

    if (isOpen && (isOpening || hasTaskIdChanged)) {
      if (taskId && storeParentTask) {
        console.log('[TaskDetailView] Initializing form and snapshots for taskId:', taskId, 'isOpening:', isOpening, 'hasTaskIdChanged:', hasTaskIdChanged);
        const parentDataForForm: TaskFormData = {
          title: storeParentTask.title || '',
          description: storeParentTask.description || '',
          notes: storeParentTask.notes || '',
          category: storeParentTask.category || '',
          due_date: storeParentTask.due_date ? storeParentTask.due_date.split('T')[0] : '',
          status: storeParentTask.status || 'pending',
          priority: storeParentTask.priority || 0,
        };
        resetParentForm(parentDataForForm as DefaultValues<TaskFormData>);
        initializeState(parentDataForForm, cloneDeep(storeSubtasks));
        setLocalSubtasks(cloneDeep(storeSubtasks));
      } else if (!taskId) {
        // If modal opens without a taskId (e.g. create new task flow, not currently supported by this modal directly)
        // Or if taskId becomes null while open (should ideally not happen without closing)
        resetParentForm({ title: '', description: '', notes: '', category: '', due_date: '', status: 'pending', priority: 0 });
        resetState();
        setLocalSubtasks([]);
      }
    } else if (!isOpen && prevIsOpenRef.current) {
      // Modal is closing
      console.log('[TaskDetailView] Modal closing, resetting snapshots.');
      resetState();
    }

    // Update refs for next render
    prevTaskIdRef.current = taskId;
    prevIsOpenRef.current = isOpen;
    // Note: storeParentTask and storeSubtasks are not in the dependency array to prevent
    // re-running this effect just because their reference changed but the modal opening condition isn't met.
    // The logic inside already uses the latest versions of these from the outer scope.
  }, [isOpen, taskId, resetParentForm, initializeState, resetState, setLocalSubtasks, storeParentTask, storeSubtasks]); // CORRECTED dependency array

  const handleModalCancelOrClose = useCallback((open: boolean) => {
    if (!open) {
      if (isModalDirty) {
        if (window.confirm("You have unsaved changes. Are you sure you want to discard them?")) {
          onOpenChange(false);
        } else {
          return; 
        }
      } else {
        onOpenChange(false);
      }
    } else {
      onOpenChange(true);
    }
  }, [isModalDirty, onOpenChange]);

  const [newSubtaskTitle, setNewSubtaskTitle] = useState('');

  const handleDeleteClick = () => {
    if (taskId && onDeleteTaskFromDetail) {
        if (window.confirm('Are you sure you want to delete this parent task and all its subtasks?')) {
            localSubtasks.forEach(sub => storeActionsFromHook.deleteTask(sub.id));
            storeActionsFromHook.deleteTask(taskId);
            onDeleteTaskFromDetail(taskId);
            onOpenChange(false);
            toast.success("Task and subtasks deleted.");
        }
    }
  };

  const handleInitiateLocalAddSubtask = () => {
    if (!newSubtaskTitle.trim() || !taskId) return;

    const tempId = `temp_sub_${Date.now()}`;
    const newSubtaskObject: Task = {
      id: tempId,
      user_id: storeParentTask?.user_id || '',
      title: newSubtaskTitle.trim(),
      status: 'pending',
      priority: storeParentTask?.priority || 0,
      parent_task_id: taskId,
      subtask_position: localSubtasks.length + 1,
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
      description: null,
      notes: null,
      category: null,
      due_date: null,
      completed: false,
    };
    handleLocalAddSubtask(newSubtaskObject);
    setNewSubtaskTitle('');
  };
  
  const handleSubtaskInteraction = () => {
    console.log("[TaskDetailView] Subtask interaction occurred. Store will reflect changes.");
  };

  const handleSubtaskReorder = (reordered: Task[]) => {
    console.log("[TaskDetailView] Subtasks reordered locally", reordered);
  };

  if (!isOpen) return null;

  const isSaveButtonDisabled = !isModalDirty;
  const displayTaskTitle = storeParentTask ? 'Edit Task' : taskId ? 'Loading...' : 'Task Details';

  const isLoadingView = taskId && !storeParentTask && isOpen;

  return (
    <RadixDialog.Root open={isOpen} onOpenChange={handleModalCancelOrClose}>
      <RadixDialog.Portal>
        <RadixDialog.Overlay className="fixed inset-0 bg-black/50 data-[state=open]:animate-overlayShow" />
        <RadixDialog.Content className="fixed top-1/2 left-1/2 w-[90vw] max-w-lg max-h-[85vh] -translate-x-1/2 -translate-y-1/2 rounded-lg bg-white dark:bg-gray-800 p-6 shadow-lg data-[state=open]:animate-contentShow focus:outline-none flex flex-col">
          <RadixDialog.Title className="text-xl font-semibold text-gray-900 dark:text-white mb-1">
            {displayTaskTitle}
          </RadixDialog.Title>
          <RadixDialog.Description className="text-sm text-gray-500 dark:text-gray-400 mb-4">
            View and edit task information. Changes are saved to local store.
          </RadixDialog.Description>

          {isLoadingView && (
            <div className="flex items-center justify-center h-40">
              <Spinner size={32} />
              <p className="ml-2">Loading task details...</p>
            </div>
          )}
          
          {!taskId && isOpen && (
             <div className="text-gray-500 dark:text-gray-400 p-4">
                No task selected or task ID is missing.
            </div>
          )}

          {storeParentTask && taskId && (
            <>
              <form onSubmit={(e) => { e.preventDefault(); handleSaveChanges(); }} className="flex-grow overflow-y-auto pr-2 space-y-4 custom-scrollbar">
                <div>
                  <Label htmlFor="title">Title</Label>
                  <Input 
                    id="title"
                    {...register('title')}
                    className="mt-1" 
                  />
                  {errors.title && <p className="text-red-500 text-sm mt-1">{errors.title.message}</p>}
                </div>
                <div>
                  <Label htmlFor="description">Description</Label>
                  <Textarea 
                    id="description"
                    {...register('description')}
                    className="mt-1" 
                  />
                  {errors.description && <p className="text-red-500 text-sm mt-1">{errors.description.message}</p>}
                </div>
                <div>
                  <Label htmlFor="notes">Notes</Label>
                  <Textarea 
                    id="notes"
                    {...register('notes')}
                    className="mt-1" 
                  />
                  {errors.notes && <p className="text-red-500 text-sm mt-1">{errors.notes.message}</p>}
                </div>
                <div>
                  <Label htmlFor="category">Category</Label>
                  <Input 
                    id="category"
                    {...register('category')}
                    className="mt-1" 
                  />
                  {errors.category && <p className="text-red-500 text-sm mt-1">{errors.category.message}</p>}
                </div>
                <div>
                  <Label htmlFor="due_date">Due Date</Label>
                  <Input 
                    id="due_date" 
                    type="date" 
                    {...register('due_date')}
                    className="mt-1"
                  />
                  {errors.due_date && <p className="text-red-500 text-sm mt-1">{errors.due_date.message}</p>}
                </div>
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <Label htmlFor="status">Status</Label>
                    <Controller
                      name="status"
                      control={control}
                      render={({ field }) => (
                        <select 
                          {...field} 
                          id="status" 
                          className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 dark:bg-gray-700 dark:border-gray-600 dark:text-white sm:text-sm p-2"
                        >
                          {ALL_STATUSES.map(s => <option key={s} value={s}>{s.replace('_', ' ').replace(/\b\w/g, l => l.toUpperCase())}</option>)}
                        </select>
                      )}
                    />
                    {errors.status && <p className="text-red-500 text-sm mt-1">{errors.status.message}</p>}
                  </div>
                  <div>
                    <Label htmlFor="priority">Priority</Label>
                    <Controller
                      name="priority"
                      control={control}
                      render={({ field }) => (
                        <select 
                          {...field} 
                          id="priority" 
                          className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 dark:bg-gray-700 dark:border-gray-600 dark:text-white sm:text-sm p-2"
                          onChange={e => field.onChange(parseInt(e.target.value, 10) as TaskPriority)}
                        >
                          {ALL_PRIORITIES.map(p => <option key={p.value} value={p.value}>{p.label}</option>)}
                        </select>
                      )}
                    />
                    {errors.priority && <p className="text-red-500 text-sm mt-1">{errors.priority.message}</p>}
                  </div>
                </div>

                <div className="mt-4 pt-4 border-t border-gray-200 dark:border-gray-700">
                  <h3 className="text-md font-semibold text-gray-800 dark:text-gray-100 mb-2">Subtasks</h3>
                  <DndContext
                    sensors={subtaskDndSensors}
                    collisionDetection={closestCenter}
                    onDragStart={handleSubtaskDragStart}
                    onDragEnd={(event) => handleSubtaskDragEnd(event, handleSubtaskReorder)}
                  >
                    <SortableContext 
                      items={(localSubtasks || []).map(s => s.id)} 
                      strategy={verticalListSortingStrategy}
                    >
                      <div className="space-y-1 mb-3">
                        {(localSubtasks || []).length > 0 ? (
                          (localSubtasks || []).map(subtask => (
                            <SubtaskItem 
                              key={subtask.id} 
                              subtask={subtask} 
                              parentTaskId={storeParentTask?.id || ''}
                              onSubtaskUpdate={handleSubtaskInteraction}
                            />
                          ))
                        ) : (
                          <p className="text-sm text-gray-500 dark:text-gray-400">No subtasks yet.</p>
                        )}
                      </div>
                    </SortableContext>
                  </DndContext>
                  <div className="flex items-center mt-2">
                    <Input 
                      type="text"
                      value={newSubtaskTitle}
                      onChange={(e) => setNewSubtaskTitle(e.target.value)}
                      placeholder="Add new subtask..."
                      className="h-9 text-sm flex-grow mr-2"
                      onKeyDown={(e) => {
                        if (e.key === 'Enter') {
                          e.preventDefault();
                          handleInitiateLocalAddSubtask();
                        }
                      }}
                    />
                    <Button 
                      type="button" 
                      onClick={handleInitiateLocalAddSubtask}
                      disabled={!newSubtaskTitle.trim()}
                    >
                      Add
                    </Button>
                  </div>
                </div>
              </form>

              <div className="mt-6 flex justify-between items-center pt-4 border-t border-gray-200 dark:border-gray-700">
                <div className="flex space-x-2 ml-auto">
                  <Button variant="secondary" type="button" onClick={() => handleModalCancelOrClose(false)}>Cancel</Button>
                  <Button 
                    type="button"
                    onClick={handleSaveChanges}
                    className="bg-blue-500 hover:bg-blue-600 text-white"
                    disabled={isSaveButtonDisabled}
                  >
                    Save Changes
                  </Button>
                </div>
                <div className="flex-shrink-0">
                   {taskId && onDeleteTaskFromDetail && (
                      <Button 
                          variant="danger" 
                          onClick={handleDeleteClick} 
                          className="ml-auto"
                          aria-label="Delete task"
                      >
                          <TrashIcon className="w-4 h-4 mr-2" />
                          Delete
                      </Button>
                  )}
                </div>
              </div>
            </>
          )}

          {!isLoadingView && !taskId && (
             <div className="text-center text-gray-500 dark:text-gray-400 p-4">
                Task not found. It may have been deleted.
            </div>
          )}

          <RadixDialog.Close asChild>
            <button
              className="absolute top-3.5 right-3.5 inline-flex h-6 w-6 appearance-none items-center justify-center rounded-full text-gray-500 hover:bg-gray-100 dark:text-gray-400 dark:hover:bg-gray-700 focus:outline-none focus:ring-2 focus:ring-gray-400"
              aria-label="Close"
              type="button"
              onClick={() => handleModalCancelOrClose(false)}
            >
              <Cross2Icon />
            </button>
          </RadixDialog.Close>
        </RadixDialog.Content>
      </RadixDialog.Portal>
    </RadixDialog.Root>
  );
};

export default TaskDetailView; 