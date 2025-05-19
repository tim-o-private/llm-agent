import React, { useState, useEffect, useCallback, useMemo, useRef } from 'react';
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
import { Controller } from 'react-hook-form';
import { isEqual } from 'lodash-es';

// Dnd-kit imports - REINSTATE THESE
import { DndContext } from '@dnd-kit/core';
import { SortableContext, verticalListSortingStrategy } from '@dnd-kit/sortable';

// IMPORT NEW HOOK
import { useEditableEntity, EntityTypeConfig } from '@/hooks/useEditableEntity';

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
const ALL_STATUSES_INTERNAL = ['pending', 'planning', 'in_progress', 'completed', 'skipped', 'deferred'] as const;
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
  status: z.enum(ALL_STATUSES_INTERNAL),
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
  console.log('[TaskDetailView] TOP LEVEL - COMPONENT FUNCTION CALLED/RE-RENDERED. Props taskId:', taskId, 'isOpen:', isOpen);
  const recentlyDraggedRef = useRef(false); // Changed ref name for clarity

  // Early return if the modal is not open, BEFORE any hook calls.
  if (!isOpen) {
    return null;
  }

  console.log('[TaskDetailView] re-rendering. taskId:', taskId, 'isOpen:', isOpen);
  useInitializeTaskStore();

  const storeActions = useTaskStore.getState();

  // DEFINE EntityTypeConfig
  const taskEntityTypeConfig: EntityTypeConfig<Task, TaskFormData, Task> = useMemo(() => ({
    entityId: taskId,
    queryHook: (currentId: string | null | undefined) => {
      // IMPORTANT: This queryHook is called by useEditableEntity.
      // It should not call React hooks directly if useEditableEntity itself is a hook.
      // Instead, it should use storeActions (getState()) or be structured so useEditableEntity manages the hook call.
      // For now, using getState() which is non-reactive for the hook's internal useEffect.
      // This means if task data changes in store, this queryHook won't automatically update useEditableEntity
      // unless the entityId prop itself changes.
      // A better pattern for queryHook would be for useEditableEntity to take a hook that it calls,
      // or for queryHook to return parameters for a query that useEditableEntity executes.
      // Given useEditableEntity's current design, this is a limitation.
      const taskData = currentId ? storeActions.getTaskById(currentId) : undefined;
      return {
        data: taskData,
        isLoading: !!currentId && !taskData, // Simplistic
        isFetching: false,
        error: null,
      };
    },
    transformDataToForm: (entityData?: Task): TaskFormData => ({
      title: entityData?.title || '',
      description: entityData?.description || null,
      notes: entityData?.notes || null,
      category: entityData?.category || null,
      due_date: entityData?.due_date ? entityData.due_date.split('T')[0] : '',
      status: entityData?.status || 'pending',
      priority: entityData?.priority || 0,
    }),
    formSchema: taskFormSchema,
    transformSubCollectionToList: (dataForSubList: any): Task[] => {
      console.log('[[[ENTERING TaskDetailView.transformSubCollectionToList]]] Received dataForSubList:', dataForSubList);
      
      const parentEntityData = dataForSubList as (Task | undefined);
      if (!parentEntityData || 
          typeof parentEntityData !== 'object' || 
          !parentEntityData.id || 
          typeof parentEntityData.id !== 'string') { 
        console.log('[[[TaskDetailView.transformSubCollectionToList]]] Invalid or missing parentEntityData.id, returning []. ParentData:', parentEntityData);
        return [];
      }
      const subtasksFromStore = storeActions.getSubtasksByParentId(parentEntityData.id);
      console.log('[[[TaskDetailView.transformSubCollectionToList]]] For parent ID:', parentEntityData.id, 'Found subtasksFromStore:', subtasksFromStore);
      return subtasksFromStore;
    },
    subEntityListItemIdField: 'id',
    createEmptySubEntityListItem: (): Task => {
      const currentParentTask = taskId ? storeActions.getTaskById(taskId) : undefined;
      const currentSubtaskList = taskId ? storeActions.getSubtasksByParentId(taskId) : [];
      return {
        id: `temp_sub_${Date.now()}`,
        user_id: currentParentTask?.user_id || '', 
        title: 'New Subtask',
        status: 'pending',
        priority: currentParentTask?.priority || 0,
        parent_task_id: taskId!,
        subtask_position: currentSubtaskList.length + 1,
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
        description: null, notes: null, category: null, due_date: null, completed_at: null, completed: false,
      };
    },
    saveHandler: async (originalEntity, currentFormData, currentSubEntityList) => {
      console.log('%%% MEGA LOG 3: ENTERING TaskDetailView.saveHandler %%%'); // Unique Log
      console.log('[TaskDetailView/taskEntityTypeConfig.saveHandler] CALLED.');
      console.log('[TaskDetailView/taskEntityTypeConfig.saveHandler] Original Entity:', JSON.parse(JSON.stringify(originalEntity)));
      console.log('[TaskDetailView/taskEntityTypeConfig.saveHandler] Parent Changes:', JSON.parse(JSON.stringify(currentFormData)));
      console.log('[TaskDetailView/taskEntityTypeConfig.saveHandler] Subtask Changes:', JSON.parse(JSON.stringify(currentSubEntityList)));

      const parentId = originalEntity?.id || taskId; // Prefer originalEntity.id if available
      if (!parentId) {
        toast.error("Cannot save, parent task ID is missing.");
        return Promise.reject(new Error("Parent task ID is missing."));
      }

      const parentTaskChanges: Partial<Task> = {};
      let parentDirty = false;

      if (originalEntity) {
        // Iterate over keys of TaskFormData to ensure all form fields are checked
        (Object.keys(currentFormData) as Array<keyof TaskFormData>).forEach(key => {
          const formValue = currentFormData[key];
          const originalValue = originalEntity[key as keyof Task]; // originalEntity is Task, currentFormData is TaskFormData

          if (key === 'title') { // Non-nullable string
            if (formValue !== originalValue) {
              parentTaskChanges.title = formValue as string;
              parentDirty = true;
            }
          } else if (key === 'status') { // Non-nullable TaskStatus (string enum)
            if (formValue !== originalValue) {
              parentTaskChanges.status = formValue as TaskStatus;
              parentDirty = true;
            }
          } else if (key === 'priority') { // Non-nullable TaskPriority (number enum)
            // Ensure formValue is treated as a number for comparison and assignment
            const numericFormValue = Number(formValue);
            if (numericFormValue !== originalValue) {
              parentTaskChanges.priority = numericFormValue as TaskPriority;
              parentDirty = true;
            }
          } else { // Nullable string fields: description, notes, category, due_date
            const currentValForComparison = (formValue === undefined || formValue === '') ? null : formValue;
            let originalValForComparison = originalValue;

            if (key === 'due_date' && originalValue) {
              // Ensure original due_date (if exists) is also in YYYY-MM-DD for fair comparison if needed
              // However, originalValue from Task is already string | null | undefined
              originalValForComparison = (originalValue as string | null)?.split('T')[0] ?? null;
            }
            
            if (currentValForComparison !== originalValForComparison) {
              parentTaskChanges[key as keyof Task] = currentValForComparison as any; // Cast to any for these flexible fields
              parentDirty = true;
            }
          }
        });

        if (parentDirty) {
          await storeActions.updateTask(parentId, parentTaskChanges);
        }
      }
      
      const originalStoreSubtasks = originalEntity ? storeActions.getSubtasksByParentId(originalEntity.id) : [];
      const currentList = currentSubEntityList || [];

      originalStoreSubtasks.forEach(origSub => {
        if (!currentList.find(currSub => currSub.id === origSub.id)) {
          storeActions.deleteTask(origSub.id);
        }
      });

      for (let i = 0; i < currentList.length; i++) {
        const currSub = currentList[i];
        const origSub = originalStoreSubtasks.find(os => os.id === currSub.id);
        const newPosition = i + 1;

        if (currSub.id.startsWith('temp_sub_')) {
          // eslint-disable-next-line @typescript-eslint/no-unused-vars
          const { id, ...subtaskToCreate } = currSub;
          await storeActions.createTask({
            ...subtaskToCreate,
            parent_task_id: parentId,
            subtask_position: newPosition,
            user_id: originalEntity?.user_id || '', // Ensure user_id
          } as Omit<Task, 'id' | 'created_at' | 'updated_at'>); // Adjusted type
        } else if (origSub) {
          const subChanges: Partial<Task> = {};
          let subDirty = false;
          (Object.keys(currSub) as Array<keyof Task>).forEach(key => {
            if (key !== 'subtask_position' && !isEqual(currSub[key], origSub[key])) {
              subChanges[key] = currSub[key] as any;
              subDirty = true;
            }
          });
          if (origSub.subtask_position !== newPosition) {
            subChanges.subtask_position = newPosition;
            subDirty = true;
          }
          if (subDirty) {
            await storeActions.updateTask(currSub.id, subChanges);
          }
        }
      }
      return parentId ? storeActions.getTaskById(parentId) : Promise.resolve(undefined);
    },
    onSaveSuccess: (savedEntity?: Task) => {
      // Log the isDirty state from useEditableEntity hook, available in TaskDetailView's scope
      console.log(`[TaskDetailView/onSaveSuccess] CALLED. Current isDirty state from hook: ${isDirty}`); 
      toast.success(`Task ${savedEntity ? `"${savedEntity.title}"` : ''} saved successfully!`);
      onTaskUpdated();
      wrappedOnOpenChange(false);
    },
    onSaveError: (error: any) => {
      console.error("Save error:", error);
      toast.error("Failed to save task. " + (error.message || ''));
    },
    onCancel: () => {
      // Modal closing is handled by wrappedOnOpenChange, 
      // but if cancel is called programmatically, ensure wrapped is used.
      wrappedOnOpenChange(false);
    },
    enableSubEntityReordering: true,
    // cloneData and isDataEqual use defaults from useEditableEntity (lodash-es)
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }), [taskId, storeActions, onTaskUpdated, onOpenChange, taskFormSchema]); // storeActions is stable

  const {
    originalEntity: loadedParentTask,
    isLoading,
    error,
    formMethods,
    // isMainFormDirty, // Can be derived from formMethods.formState.isDirty
    subEntityList,
    // isSubEntityListDirty, // Can be derived or rely on combined isDirty
    addSubItem,
    updateSubItem,
    removeSubItem,
    isDirty,
    isSaving,
    handleSave,
    handleCancel,
    // resetState: resetEntityState, // For explicit resets if needed
    dndContextProps,
    getSortableListProps,
  } = useEditableEntity<Task, TaskFormData, Task>(taskEntityTypeConfig);

  const { register, control, formState: { errors: formErrors } } = formMethods;

  // Log subEntityList received from the hook
  useEffect(() => {
    console.log('[TaskDetailView] subEntityList from useEditableEntity:', subEntityList);
  }, [subEntityList]);

  const wrappedOnOpenChange = useCallback((open: boolean) => {
    // ADDING LOG HERE
    console.log(`[TaskDetailView] wrappedOnOpenChange called. Requested open state: ${open}. Current isDirty: ${isDirty}`);
    
    if (!open) {
      if (isDirty) {
        console.log('[TaskDetailView] Modal about to close AND isDirty is true. Showing confirm dialog.');
        if (window.confirm("You have unsaved changes. Are you sure you want to discard them?")) {
          console.log('[TaskDetailView] User CONFIRMED discard. Calling handleCancel and onOpenChange(false).');
          handleCancel(); 
          onOpenChange(false);
        } else {
          console.log('[TaskDetailView] User CANCELLED discard. Modal should remain open.');
          return; // Important to prevent onOpenChange(false) if user cancels discard
        }
      } else {
        console.log('[TaskDetailView] Modal about to close and isDirty is false. Calling onOpenChange(false).');
        onOpenChange(false);
      }
    } else {
      console.log('[TaskDetailView] Modal about to open. Calling onOpenChange(true).');
      onOpenChange(true);
    }
  }, [isDirty, handleCancel, onOpenChange]);

  const [newSubtaskTitle, setNewSubtaskTitle] = useState('');

  const handleDeleteClick = () => {
    if (taskId) { // originalEntity might be null if still loading or error
        const taskToDelete = loadedParentTask || storeActions.getTaskById(taskId);
        if (taskToDelete) {
        if (window.confirm('Are you sure you want to delete this parent task and all its subtasks?')) {
                // Use subEntityList from the hook as it's the current working list
                subEntityList.forEach(sub => storeActions.deleteTask(sub.id));
                storeActions.deleteTask(taskToDelete.id); // Use the ID from the task object
                if (onDeleteTaskFromDetail) onDeleteTaskFromDetail(taskToDelete.id);
            onOpenChange(false);
            toast.success("Task and subtasks deleted.");
            }
        } else {
            toast.error("Could not find task to delete.");
        }
    }
  };

  const handleInitiateLocalAddSubtask = () => {
    if (!newSubtaskTitle.trim() || !taskId) return;
    // createEmptySubEntityListItem is part of config now
    const newSubtaskObject = taskEntityTypeConfig.createEmptySubEntityListItem!();
    newSubtaskObject.title = newSubtaskTitle.trim();
    addSubItem(newSubtaskObject as Task);
    setNewSubtaskTitle('');
  };
  
  const isSaveButtonDisabled = !isDirty || isSaving;
  // Determine display title based on hook's loading state and data
  const displayTaskTitle = isLoading ? 'Loading...' : loadedParentTask ? 'Edit Task' : taskId ? 'Loading...' : 'Task Details';

  const originalDndKitOnDragEnd = dndContextProps?.onDragEnd;

  const customOnDragEnd = (event: any) => {
    console.log('[TaskDetailView] Custom DND Drag End triggered');
    recentlyDraggedRef.current = true; // Flag that a drag just ended
    console.log('[TaskDetailView] recentlyDraggedRef.current set to true');

    if (originalDndKitOnDragEnd) {
      originalDndKitOnDragEnd(event); // Call the hook's onDragEnd
    }
    // No timeout needed here now, onSubmit will reset the flag if it consumes it.
  };

  // Create augmented DndContextProps
  const finalDndContextProps = dndContextProps
    ? {
        ...dndContextProps,
        // onDragStart: handleDragStart, // Not using for now
        onDragEnd: customOnDragEnd, // Our new onDragEnd
      }
    : undefined;

  return (
    <RadixDialog.Root open={isOpen} onOpenChange={wrappedOnOpenChange}>
      <RadixDialog.Portal>
        <RadixDialog.Overlay className="fixed inset-0 bg-black/50 data-[state=open]:animate-overlayShow" />
        <RadixDialog.Content 
          className="fixed top-1/2 left-1/2 w-[90vw] max-w-lg max-h-[85vh] -translate-x-1/2 -translate-y-1/2 rounded-lg bg-white dark:bg-gray-800 p-6 shadow-lg data-[state=open]:animate-contentShow focus:outline-none flex flex-col"
          onPointerDownOutside={(event) => {
            console.log('[TaskDetailView] RadixDialog.Content onPointerDownOutside triggered.');
            // Prevent default behavior which might lead to closing the dialog.
            // This is often used to allow interactions with elements outside the modal 
            // (e.g. custom popovers) without closing the modal. In our DND case,
            // we want to ensure internal re-renders don't get misinterpreted as outside interactions.
            event.preventDefault(); 
          }}
        >
          <RadixDialog.Title className="text-xl font-semibold text-gray-900 dark:text-white mb-1">
            {displayTaskTitle}
          </RadixDialog.Title>
          <RadixDialog.Description className="text-sm text-gray-500 dark:text-gray-400 mb-4">
            View and edit task information. Changes are saved to local store.
          </RadixDialog.Description>

          {isLoading && (
            <div className="flex items-center justify-center h-40">
              <Spinner size={32} />
              <p className="ml-2">Loading task details...</p>
            </div>
          )}
          
          {!isLoading && error && (
            <div className="text-red-500 dark:text-red-400 p-4">
              Error loading task: {typeof error === 'string' ? error : (error as Error)?.message || 'Unknown error'}
            </div>
          )}

          {!isLoading && !error && !loadedParentTask && taskId && (
             <div className="text-gray-500 dark:text-gray-400 p-4">
                Task with ID '{taskId}' not found.
            </div>
          )}
          
          {!taskId && isOpen && !isLoading && !error && ( // Handles create mode or no task selected scenario
             <div className="text-gray-500 dark:text-gray-400 p-4">
                No task selected or task ID is missing.
            </div>
          )}

          {!isLoading && !error && loadedParentTask && ( // Only render form if task is loaded
            <>
              <form onSubmit={(e) => { 
                e.preventDefault(); 
                console.log('%%% FORM ONSUBMIT TRIGGERED %%%'); 
                if (recentlyDraggedRef.current) {
                  console.log('%%% FORM ONSUBMIT IGNORED: recentlyDraggedRef was true %%%');
                  recentlyDraggedRef.current = false; // Consume the flag
                  console.log('[TaskDetailView] recentlyDraggedRef.current reset to false by onSubmit');
                  return;
                }
                // If we reach here, it was not a DND-triggered submit
                // console.log('Form submit allowed, not DND related or flag already consumed.');
                handleSave(); // Re-enable this line
              }} className="flex-grow overflow-y-auto pr-2 space-y-4 custom-scrollbar">
                <div>
                  <Label htmlFor="title">Title</Label>
                  <Input 
                    id="title"
                    {...register('title')}
                    className="mt-1" 
                  />
                  {formErrors.title && <p className="text-red-500 text-sm mt-1">{formErrors.title.message}</p>}
                </div>
                <div>
                  <Label htmlFor="description">Description</Label>
                  <Textarea 
                    id="description"
                    {...register('description')}
                    className="mt-1" 
                  />
                  {formErrors.description && <p className="text-red-500 text-sm mt-1">{formErrors.description.message}</p>}
                </div>
                <div>
                  <Label htmlFor="notes">Notes</Label>
                  <Textarea 
                    id="notes"
                    {...register('notes')}
                    className="mt-1" 
                  />
                  {formErrors.notes && <p className="text-red-500 text-sm mt-1">{formErrors.notes.message}</p>}
                </div>
                <div>
                  <Label htmlFor="category">Category</Label>
                  <Input 
                    id="category"
                    {...register('category')}
                    className="mt-1" 
                  />
                  {formErrors.category && <p className="text-red-500 text-sm mt-1">{formErrors.category.message}</p>}
                </div>
                <div>
                  <Label htmlFor="due_date">Due Date</Label>
                  <Input 
                    id="due_date" 
                    type="date" 
                    {...register('due_date')}
                    className="mt-1"
                  />
                  {formErrors.due_date && <p className="text-red-500 text-sm mt-1">{formErrors.due_date.message}</p>}
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
                          {ALL_STATUSES_INTERNAL.map(s => <option key={s} value={s}>{s.replace('_', ' ').replace(/\b\w/g, l => l.toUpperCase())}</option>)}
                        </select>
                      )}
                    />
                    {formErrors.status && <p className="text-red-500 text-sm mt-1">{formErrors.status.message}</p>}
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
                    {formErrors.priority && <p className="text-red-500 text-sm mt-1">{formErrors.priority.message}</p>}
                  </div>
                </div>

                <div className="mt-4 pt-4 border-t border-gray-200 dark:border-gray-700">
                  <h3 className="text-md font-semibold text-gray-800 dark:text-gray-100 mb-2">Subtasks</h3>
                  {dndContextProps && ( // Conditionally render DND context
                    (() => {
                      console.log('[TaskDetailView] DndContext IS BEING RENDERED because dndContextProps is truthy.');
                      return (
                        <DndContext {...finalDndContextProps} >
                    <SortableContext 
                            items={(getSortableListProps().items || []).map(s => s.id)} 
                      strategy={verticalListSortingStrategy}
                    >
                      <div className="space-y-1 mb-3">
                              {(subEntityList || []).length > 0 ? (
                                (subEntityList || []).map(subtask => (
                                  <SubtaskItem 
                                    key={subtask.id} 
                                    subtask={subtask} 
                                    onUpdate={(id, updates) => updateSubItem(id, updates)}
                                    onRemove={(id) => removeSubItem(id)}
                                  />
                                ))
                              ) : (
                                <p className="text-sm text-gray-500 dark:text-gray-400">No subtasks yet.</p>
                              )}
                            </div>
                          </SortableContext>
                        </DndContext>
                      );
                    })()
                  )}
                  {!dndContextProps && ( // Render non-DND list if DND is not enabled
                     <div className="space-y-1 mb-3">
                        {(subEntityList || []).length > 0 ? (
                          (subEntityList || []).map(subtask => (
                            <SubtaskItem 
                              key={subtask.id} 
                              subtask={subtask} 
                              onUpdate={(id, updates) => updateSubItem(id, updates)}
                              onRemove={(id) => removeSubItem(id)}
                            />
                          ))
                        ) : (
                          <p className="text-sm text-gray-500 dark:text-gray-400">No subtasks yet.</p>
                        )}
                      </div>
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
                  <Button variant="secondary" type="button" onClick={() => wrappedOnOpenChange(false)}>Cancel</Button>
                  <Button 
                    type="button"
                    onClick={handleSave}
                    className="bg-blue-500 hover:bg-blue-600 text-white"
                    disabled={isSaveButtonDisabled}
                  >
                    {isSaving ? <Spinner size={16} className="mr-2" /> : null}
                    {isSaving ? 'Saving...' : 'Save Changes'}
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