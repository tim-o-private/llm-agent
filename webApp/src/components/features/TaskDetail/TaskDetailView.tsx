import React, { useState, useEffect, useRef, useCallback } from 'react';
import * as RadixDialog from '@radix-ui/react-dialog';
import { Cross2Icon, TrashIcon } from '@radix-ui/react-icons';
import { z } from 'zod';
import { useFetchTaskById, useUpdateTask, useFetchSubtasks, useCreateTask, useUpdateSubtaskOrder } from '@/api/hooks/useTaskHooks';
import { Task, UpdateTaskData, TaskStatus, TaskPriority, NewTaskData } from '@/api/types';
import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/Input';
import { Textarea } from '@/components/ui/Textarea';
import { Label } from '@/components/ui/Label';
import { Spinner } from '@/components/ui/Spinner';
import { toast } from '@/components/ui/toast';
import { SubtaskItem } from './SubtaskItem';
import { useObjectEditManager, ObjectEditManagerOptions } from '@/hooks/useObjectEditManager';
import { useReorderableList, ReorderableListOptions } from '@/hooks/useReorderableList';
import { Controller } from 'react-hook-form';
import { UseMutationResult as ReactQueryUseMutationResult } from '@tanstack/react-query';

// Dnd-kit imports
import {
  DndContext,
  closestCenter,
  UniqueIdentifier,
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

// --- Transformation Functions for useObjectEditManager ---
const transformDataToFormData = (task: Task | null): TaskFormData => {
  if (!task) { // Handle null case, return default form data
    return {
      title: '',
      description: '',
      notes: '',
      category: '',
      due_date: '',
      status: 'pending',
      priority: 0,
    };
  }
  return {
    title: task.title || '',
    description: task.description || '',
    notes: task.notes || '',
    category: task.category || '',
    due_date: task.due_date ? task.due_date.split('T')[0] : '',
    status: task.status || 'pending',
    priority: task.priority || 0,
  };
};

const transformFormDataToUpdateData = (formData: TaskFormData, originalTask: Task | null): UpdateTaskData => {
  const updates: UpdateTaskData = {};
  if (!originalTask) return updates; // Should not happen in an update scenario

  if (formData.title !== originalTask.title) updates.title = formData.title;
  if (formData.description !== (originalTask.description || '')) updates.description = formData.description;
  if (formData.notes !== (originalTask.notes || '')) updates.notes = formData.notes;
  if (formData.category !== (originalTask.category || '')) updates.category = formData.category;
  
  const formDueDateString = formData.due_date ? formData.due_date : null;
  const taskDueDateString = originalTask.due_date ? originalTask.due_date.split('T')[0] : null;
  if (formDueDateString !== taskDueDateString) {
    updates.due_date = formDueDateString ? new Date(formDueDateString).toISOString() : null;
  }

  if (formData.status !== originalTask.status) updates.status = formData.status;
  if (formData.priority !== originalTask.priority) updates.priority = formData.priority;
  
  return updates;
};

export const TaskDetailView: React.FC<TaskDetailViewProps> = ({
  taskId,
  isOpen,
  onOpenChange,
  onTaskUpdated,
  onDeleteTaskFromDetail,
}) => {
  console.log(`[TaskDetailView] Render. taskId: ${taskId}, isOpen: ${isOpen}`);

  const objectManagerOptions: ObjectEditManagerOptions<Task, TaskFormData, UpdateTaskData> = {
    objectType: 'Task',
    objectId: taskId,
    fetchQueryHook: useFetchTaskById as (id: string | null) => import('@tanstack/react-query').UseQueryResult<Task | null, Error>,
    updateMutationHook: useUpdateTask,
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
    transformDataToFormData,
    transformFormDataToUpdateData,
    onSaveSuccess: (_savedTask, _isNew) => {
      toast.default(
        'Task Updated',
        'Your task has been successfully updated.',
      );
      if (onTaskUpdated) onTaskUpdated();
      onOpenChange(false);
    },
    onClose: () => onOpenChange(false),
    onLoadError: (error) => {
        toast.error('Error Loading Task', error.message);
    }
  };

  const {
    formMethods,
    originalData: task,
    isLoading: isLoadingTaskData,
    isFetching: isFetchingTask,
    isSaving: isSavingTask,
    error: taskError,
    handleSave: handleSaveTask,
    handleCancel: handleCancelEdit,
    isDirty: isTaskFormDirty,
    canSubmit: canSubmitTask,
  } = useObjectEditManager(objectManagerOptions);

  const { register, control, formState: { errors } } = formMethods;

  const wrappedOnOpenChange = useCallback((open: boolean) => {
    console.log(`[TaskDetailView] wrappedOnOpenChange called with: ${open}. Current isOpen prop: ${isOpen}`);
    if (!open && isTaskFormDirty) {
        handleCancelEdit();
    } else {
        onOpenChange(open);
    }
  }, [onOpenChange, isOpen, isTaskFormDirty, handleCancelEdit]);

  // --- Subtask Management with useReorderableList ---
  const subtasksWereModifiedInThisSessionRef = useRef(false);

  const adaptedUpdateSubtaskOrderHook = useCallback(() => {
    const originalMutation = useUpdateSubtaskOrder();
    return {
      ...originalMutation,
      mutate: (variables: { parentId: string | null; orderedItems: Array<{ id: UniqueIdentifier; position: number } & Partial<Task>> }, 
               options?: import('@tanstack/react-query').MutateOptions<Task[], Error, { parentTaskId: string; orderedSubtasks: { id: string; subtask_position: number; }[] }, { previousTasks?: Task[]; }>) => {
        if (!variables.parentId) {
          console.error("Parent ID is null for subtask order update.");
          if (options?.onError) options.onError(new Error("Parent ID is null"), { parentTaskId: '', orderedSubtasks: [] }, undefined /* context */);
          return;
        }
        const actualPayload = {
          parentTaskId: variables.parentId,
          orderedSubtasks: variables.orderedItems.map(item => ({ id: item.id as string, subtask_position: item.position })),
        };
        originalMutation.mutate(actualPayload, options);
      },
      mutateAsync: async (variables: { parentId: string | null; orderedItems: Array<{ id: UniqueIdentifier; position: number } & Partial<Task>> }, 
                          options?: import('@tanstack/react-query').MutateOptions<Task[], Error, { parentTaskId: string; orderedSubtasks: { id: string; subtask_position: number; }[] }, { previousTasks?: Task[]; }>) => {
        if (!variables.parentId) {
          return Promise.reject(new Error("Parent ID is null for subtask order update."));
        }
        const actualPayload = {
          parentTaskId: variables.parentId,
          orderedSubtasks: variables.orderedItems.map(item => ({ id: item.id as string, subtask_position: item.position })),
        };
        return originalMutation.mutateAsync(actualPayload, options);
      },
    } as ReactQueryUseMutationResult<Task[], Error, { parentId: string | null; orderedItems: Array<{ id: UniqueIdentifier; position: number } & Partial<Task>> }, unknown>;
  }, []);

  const adaptedCreateSubtaskHook = useCallback(() => {
    const originalMutation = useCreateTask();
    return {
      ...originalMutation,
      mutate: (variables: { parentId: string | null; newItem: Omit<NewTaskData, "user_id">; position?: number },
               options?: import('@tanstack/react-query').MutateOptions<Task, Error, Omit<NewTaskData, "user_id">, unknown>) => {
        const { parentId, newItem, position } = variables;
        const actualPayload: Omit<NewTaskData, "user_id"> = { ...newItem, parent_task_id: parentId, subtask_position: position };
        originalMutation.mutate(actualPayload, options);
      },
      mutateAsync: async (variables: { parentId: string | null; newItem: Omit<NewTaskData, "user_id">; position?: number },
                          options?: import('@tanstack/react-query').MutateOptions<Task, Error, Omit<NewTaskData, "user_id">, unknown>) => {
        const { parentId, newItem, position } = variables;
        const actualPayload: Omit<NewTaskData, "user_id"> = { ...newItem, parent_task_id: parentId, subtask_position: position };
        return originalMutation.mutateAsync(actualPayload, options);
      },
    } as ReactQueryUseMutationResult<Task, Error, { parentId: string | null; newItem: Omit<NewTaskData, "user_id">; position?: number }, unknown>;
  }, []);

  const sublistOptions: ReorderableListOptions<Task, Omit<NewTaskData, 'user_id'>> = {
    listName: 'Subtasks',
    parentObjectId: task?.id || null,
    fetchListQueryHook: useFetchSubtasks,
    updateOrderMutationHook: adaptedUpdateSubtaskOrderHook,
    createItemMutationHook: adaptedCreateSubtaskHook,
    getItemId: (item: Task) => item.id,
    getItemPosition: (item: Task) => item.subtask_position || 0,
    getNewItemPosition: (items: Task[], _newItemData: Omit<NewTaskData, 'user_id'>) => items.length + 1,
    onReorderCommit: (_reorderedItems) => {
      toast.default('Subtask order saved!');
      subtasksWereModifiedInThisSessionRef.current = true;
    },
    onItemAdded: (_newItem) => {
      toast.default('Subtask Added!');
      subtasksWereModifiedInThisSessionRef.current = true;
      setNewSubtaskTitle('');
    },
    onFetchError: (error) => {
      toast.error('Error loading subtasks', error.message);
    },
  };

  const {
    items: subtasks,
    isLoading: isLoadingSubtasks,
    isAddingItem: isAddingSubtask,
    error: subtasksError,
    dndSensors: subtaskDndSensors,
    handleDragStart: handleSubtaskDragStart,
    handleDragEnd: handleSubtaskDragEnd,
    handleAddItem: handleAddSubtaskOptimistic,
    refetchList: refetchSubtasks,
  } = useReorderableList<Task, Omit<NewTaskData, 'user_id'>>(sublistOptions);

  const [newSubtaskTitle, setNewSubtaskTitle] = useState('');

  useEffect(() => {
    if (isOpen && taskId) {
      subtasksWereModifiedInThisSessionRef.current = false;
    }
  }, [isOpen, taskId]);

  const handleDeleteClick = () => {
    if (taskId && onDeleteTaskFromDetail) {
        if (window.confirm('Are you sure you want to delete this task?')) {
            onDeleteTaskFromDetail(taskId);
        }
    }
  };

  const handleInitiateAddSubtask = async () => {
    if (!newSubtaskTitle.trim() || !task || !handleAddSubtaskOptimistic) return;

    const newSubtaskData: Omit<NewTaskData, 'user_id'> = {
      title: newSubtaskTitle.trim(),
      status: 'pending', 
      priority: task.priority || 0, 
    };

    try {
      await handleAddSubtaskOptimistic(newSubtaskData);
    } catch (err) {
      toast.error('Failed to add subtask', (err instanceof Error) ? err.message : 'Unknown error');
      console.error("[TaskDetailView] Failed to add subtask via hook:", err);
    }
  };

  if (!isOpen) return null;

  const isSaveButtonDisabled = !canSubmitTask || isSavingTask;
  const displayTaskTitle = task ? 'Edit Task' : isLoadingTaskData ? 'Loading...' : 'Task Details';

  return (
    <RadixDialog.Root open={isOpen} onOpenChange={wrappedOnOpenChange}>
      <RadixDialog.Portal>
        <RadixDialog.Overlay className="fixed inset-0 bg-black/50 data-[state=open]:animate-overlayShow" />
        <RadixDialog.Content className="fixed top-1/2 left-1/2 w-[90vw] max-w-lg max-h-[85vh] -translate-x-1/2 -translate-y-1/2 rounded-lg bg-white dark:bg-gray-800 p-6 shadow-lg data-[state=open]:animate-contentShow focus:outline-none flex flex-col">
          <RadixDialog.Title className="text-xl font-semibold text-gray-900 dark:text-white mb-1">
            {displayTaskTitle}
          </RadixDialog.Title>
          <RadixDialog.Description className="text-sm text-gray-500 dark:text-gray-400 mb-4">
            View and edit task information.
          </RadixDialog.Description>

          {isFetchingTask && (
            <div className="flex items-center justify-center h-40">
              <Spinner size={32} />
              <p className="ml-2">Loading task details...</p>
            </div>
          )}

          {taskError && !isFetchingTask && (
            <div className="text-red-500">
              Error: {taskError.message}
            </div>
          )}
          
          {!taskId && isOpen && !isLoadingTaskData && (
             <div className="text-gray-500 dark:text-gray-400 p-4">
                No task selected or task ID is missing.
            </div>
          )}

          {!isLoadingTaskData && !taskError && task && taskId && (
            <>
              <form onSubmit={handleSaveTask} className="flex-grow overflow-y-auto pr-2 space-y-4 custom-scrollbar">
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
                  {isLoadingSubtasks && (
                    <div className="flex items-center text-sm text-gray-500">
                      <Spinner size={16} /> 
                      <span className="ml-2">Loading subtasks...</span>
                    </div>
                  )}
                  {subtasksError && <p className='text-red-500 text-sm'>Error loading subtasks: {subtasksError.message}</p>}
                  {!isLoadingSubtasks && !subtasksError && (
                    <DndContext
                      sensors={subtaskDndSensors}
                      collisionDetection={closestCenter}
                      onDragStart={handleSubtaskDragStart}
                      onDragEnd={handleSubtaskDragEnd}
                    >
                      <SortableContext 
                        items={(subtasks || []).map(s => s.id)} 
                        strategy={verticalListSortingStrategy}
                      >
                        <div className="space-y-1 mb-3">
                          {(subtasks || []).length > 0 ? (
                            (subtasks || []).map(subtask => (
                              <SubtaskItem 
                                key={subtask.id} 
                                subtask={subtask} 
                                parentTaskId={task?.id || ''}
                                onSubtaskUpdate={() => {
                                  refetchSubtasks();
                                  subtasksWereModifiedInThisSessionRef.current = true;
                                }}
                              />
                            ))
                          ) : (
                            <p className="text-sm text-gray-500 dark:text-gray-400">No subtasks yet.</p>
                          )}
                        </div>
                      </SortableContext>
                    </DndContext>
                  )}
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
                          handleInitiateAddSubtask();
                        }
                      }}
                    />
                    <Button 
                      type="button" 
                      onClick={handleInitiateAddSubtask} 
                      disabled={!newSubtaskTitle.trim() || isAddingSubtask}
                    >
                      {isAddingSubtask ? <Spinner size={16} /> : 'Add'}
                    </Button>
                  </div>
                </div>
              </form>

              <div className="mt-6 flex justify-between items-center pt-4 border-t border-gray-200 dark:border-gray-700">
                <div className="flex space-x-2 ml-auto">
                  <Button variant="secondary" type="button" onClick={handleCancelEdit}>Cancel</Button>
                  <Button 
                    type="button"
                    onClick={handleSaveTask}
                    className="bg-blue-500 hover:bg-blue-600 text-white"
                    disabled={isSaveButtonDisabled}
                  >
                    {isSavingTask ? <Spinner size={16} className="mr-2" /> : null}
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

          {!isLoadingTaskData && !taskError && !task && taskId && (
             <div className="text-center text-gray-500 dark:text-gray-400 p-4">
                Task not found. It may have been deleted.
            </div>
          )}

          <RadixDialog.Close asChild>
            <button
              className="absolute top-3.5 right-3.5 inline-flex h-6 w-6 appearance-none items-center justify-center rounded-full text-gray-500 hover:bg-gray-100 dark:text-gray-400 dark:hover:bg-gray-700 focus:outline-none focus:ring-2 focus:ring-gray-400"
              aria-label="Close"
              type="button"
              onClick={() => wrappedOnOpenChange(false)}
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