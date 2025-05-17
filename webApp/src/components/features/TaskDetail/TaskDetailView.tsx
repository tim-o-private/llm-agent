import React, { useState, useEffect, ChangeEvent, FormEvent, useRef, useMemo } from 'react';
import * as RadixDialog from '@radix-ui/react-dialog';
import { Cross2Icon, TrashIcon } from '@radix-ui/react-icons';
import { useFetchTaskById, useUpdateTask, useFetchSubtasks, useCreateTask, useUpdateSubtaskOrder } from '@/api/hooks/useTaskHooks';
import { Task, UpdateTaskData, TaskStatus, TaskPriority, NewTaskData } from '@/api/types';
import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/Input';
import { Textarea } from '@/components/ui/Textarea';
import { Label } from '@/components/ui/Label';
import { Spinner } from '@/components/ui/Spinner';
import { toast } from '@/components/ui/toast';
import { SubtaskItem } from './SubtaskItem';

// Dnd-kit imports
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
} from '@dnd-kit/sortable';

interface TaskDetailViewProps {
  taskId: string | null;
  isOpen: boolean;
  onOpenChange: (isOpen: boolean) => void;
  onTaskUpdated: () => void;
  onTaskDeleted: () => void;
  onDeleteTaskFromDetail?: (taskId: string) => void;
}

const ALL_STATUSES: TaskStatus[] = ['pending', 'planning', 'in_progress', 'completed', 'skipped', 'deferred'];
const ALL_PRIORITIES: { label: string; value: TaskPriority }[] = [
  { label: 'None', value: 0 },
  { label: 'Low', value: 1 },
  { label: 'Medium', value: 2 },
  { label: 'High', value: 3 },
];

const initialFormState: Partial<Task> = {
  title: '',
  description: '',
  notes: '',
  category: '',
  due_date: '',
  status: 'pending',
  priority: 0,
};

export const TaskDetailView: React.FC<TaskDetailViewProps> = ({
  taskId,
  isOpen,
  onOpenChange,
  onTaskUpdated,
  //onTaskDeleted, Unused, commented out.
  onDeleteTaskFromDetail,
}) => {
  const { data: task, isLoading, error, refetch } = useFetchTaskById(taskId);
  const updateTaskMutation = useUpdateTask();
  const createTaskMutation = useCreateTask();

  const [formData, setFormData] = useState<Partial<Task>>(initialFormState);
  const [newSubtaskTitle, setNewSubtaskTitle] = useState('');

  const subtasksWereModifiedInThisSessionRef = useRef(false);

  const { 
    data: subtasks,
    isLoading: isLoadingSubtasks,
    refetch: refetchSubtasks,
    error: subtasksError
  } = useFetchSubtasks(task?.id);

  const updateSubtaskOrderMutation = useUpdateSubtaskOrder();

  // State for optimistic UI updates during DND
  const [optimisticSubtasks, setOptimisticSubtasks] = useState<Task[] | undefined>(undefined);

  useEffect(() => {
    if (isOpen && taskId) {
      refetch();
      refetchSubtasks(); // Ensure subtasks are fresh when modal opens
      subtasksWereModifiedInThisSessionRef.current = false; // Reset flag
    }
  }, [isOpen, taskId, refetch, refetchSubtasks]);

  useEffect(() => {
    if (task) {
      setFormData({
        title: task.title || '',
        description: task.description || '',
        notes: task.notes || '',
        category: task.category || '',
        due_date: task.due_date ? task.due_date.split('T')[0] : '',
        status: task.status || 'pending',
        priority: task.priority || 0,
      });
    } else {
      setFormData(initialFormState);
    }
  }, [task]);

  useEffect(() => {
    if (subtasks) {
      setOptimisticSubtasks(subtasks);
      console.log('[TaskDetailView] useEffect setting optimisticSubtasks from subtasks prop:', JSON.stringify(subtasks?.map(st => ({id: st.id, title: st.title, pos: st.subtask_position}))));
    }
  }, [subtasks]);

  // Dnd-kit sensors
  const sensors = useSensors(
    useSensor(PointerSensor),
    useSensor(KeyboardSensor, {
      coordinateGetter: sortableKeyboardCoordinates,
    })
  );

  const handleChange = (e: ChangeEvent<HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement>) => {
    const { name, value } = e.target;
    setFormData(prev => ({
      ...prev,
      [name]: name === 'priority' ? parseInt(value, 10) as TaskPriority : value,
    }));
  };

  const parentTaskHasChanges = useMemo(() => {
    if (!task || !formData) return false;
    if (formData.title !== undefined && formData.title !== task.title) return true;
    if (formData.description !== undefined && formData.description !== (task.description || '')) return true;
    if (formData.notes !== undefined && formData.notes !== (task.notes || '')) return true;
    if (formData.category !== undefined && formData.category !== (task.category || '')) return true;
    const formDueDate = formData.due_date ? new Date(formData.due_date).toISOString() : null;
    const taskDueDate = task.due_date ? new Date(task.due_date).toISOString() : null;
    if (formDueDate !== taskDueDate) return true;
    if (formData.status !== undefined && formData.status !== task.status) return true;
    if (formData.priority !== undefined && formData.priority !== task.priority) return true;
    return false;
  }, [task, formData]);

  const handleSave = async () => {
    console.log('[TaskDetailView] handleSave triggered.');
    console.log('[TaskDetailView] Current state before save attempt:');
    console.log('  taskId:', taskId);
    console.log('  task available:', !!task);
    console.log('  formData:', JSON.stringify(formData));
    console.log('  original task data:', JSON.stringify(task));
    console.log('  isLoading (fetch task):', isLoading);
    console.log('  updateTaskMutation.isPending:', updateTaskMutation.isPending);
    console.log('  createTaskMutation.isPending:', createTaskMutation.isPending);
    console.log('  parentTaskHasChanges (memoized):', parentTaskHasChanges); 
    console.log('  subtasksWereModifiedInThisSessionRef.current:', subtasksWereModifiedInThisSessionRef.current);

    if (!taskId || !task) {
      console.warn('[TaskDetailView] handleSave: No taskId or task data. Aborting.');
      return;
    }

    // Recalculate updates for parent task
    const updates: UpdateTaskData = {};
    if (formData.title !== undefined && formData.title !== task.title) updates.title = formData.title;
    if (formData.description !== undefined && formData.description !== (task.description || '')) updates.description = formData.description;
    if (formData.notes !== undefined && formData.notes !== (task.notes || '')) updates.notes = formData.notes;
    if (formData.category !== undefined && formData.category !== (task.category || '')) updates.category = formData.category;
    const formDueDate = formData.due_date ? new Date(formData.due_date).toISOString() : null;
    const taskDueDate = task.due_date ? new Date(task.due_date).toISOString() : null;
    if (formDueDate !== taskDueDate) updates.due_date = formDueDate;
    if (formData.status !== undefined && formData.status !== task.status) updates.status = formData.status as TaskStatus;
    if (formData.priority !== undefined && formData.priority !== task.priority) updates.priority = formData.priority as TaskPriority;
    
    console.log('[TaskDetailView] Calculated updates object:', JSON.stringify(updates));
    const actualParentHasChanges = Object.keys(updates).length > 0;
    console.log('[TaskDetailView] actualParentHasChanges (calculated now):', actualParentHasChanges);

    if (!actualParentHasChanges) {
      console.log('[TaskDetailView] No actual parent task changes detected.');
      if (subtasksWereModifiedInThisSessionRef.current) {
        console.log('[TaskDetailView] Subtasks were modified. Closing modal.');
        onOpenChange(false); 
        subtasksWereModifiedInThisSessionRef.current = false; 
      } else {
        console.log('[TaskDetailView] No subtask changes either. Toasting "No changes to save." with new toast function');
        toast.default('No changes to save.', undefined, { duration: 3000 });
      }
      return;
    }

    console.log('[TaskDetailView] Parent task has changes. Attempting mutation.');
    try {
      console.log('[TaskDetailView] Calling updateTaskMutation.mutateAsync with id:', taskId, 'and updates:', JSON.stringify(updates));
      await updateTaskMutation.mutateAsync({ id: taskId, updates });
      console.log('[TaskDetailView] updateTaskMutation.mutateAsync Succeeded.');
      
      if (onTaskUpdated) {
        console.log('[TaskDetailView] Calling onTaskUpdated callback (moved before toast for testing).');
        onTaskUpdated();
      }
      
      console.log('[TaskDetailView] Attempting new toast function...');
      toast.default(
        'Task Updated',
        'Your task has been successfully updated.',
      );
      console.log('[TaskDetailView] new toast call completed.');

      subtasksWereModifiedInThisSessionRef.current = false; 
      onOpenChange(false);
      
    } catch (err) {
      console.error('[TaskDetailView] updateTaskMutation.mutateAsync FAILED. Error in handleSave catch block:', err);
      toast.error(
        'Error Updating Task',
        (err instanceof Error) ? err.message : 'An unexpected error occurred.',
      );
      if (err instanceof Error) {
        console.error('[TaskDetailView] Error name:', err.name);
        console.error('[TaskDetailView] Error message:', err.message);
        console.error('[TaskDetailView] Error stack:', err.stack);
      } else {
        console.error('[TaskDetailView] Caught error is not an instance of Error:', err);
      }
    }
  };
  
  const handleDeleteClick = () => {
    if (taskId && onDeleteTaskFromDetail) {
        if (window.confirm('Are you sure you want to delete this task?')) {
            onDeleteTaskFromDetail(taskId);
        }
    }
  };

  const handleAddSubtask = async () => {
    if (!newSubtaskTitle.trim() || !task) return;

    const newSubtaskData: Omit<NewTaskData, 'user_id'> = {
      title: newSubtaskTitle.trim(),
      parent_task_id: task.id,
      status: 'pending',
      priority: task.priority || 0,
      subtask_position: (optimisticSubtasks?.length || subtasks?.length || 0) + 1,
    };

    try {
      await createTaskMutation.mutateAsync(newSubtaskData);
      toast.default('Subtask Added!');
      setNewSubtaskTitle('');
      refetchSubtasks();
      subtasksWereModifiedInThisSessionRef.current = true;
    } catch (err) {
      toast.error('Failed to add subtask', (err instanceof Error) ? err.message : undefined);
      console.error("Failed to add subtask:", err);
    }
  };

  const handleDragEnd = (event: DragEndEvent) => {
    const { active, over } = event;
    console.log('[TaskDetailView] handleDragEnd. Active:', active.id, 'Over:', over?.id);
    console.log('[TaskDetailView] optimisticSubtasks at start of dragEnd:', JSON.stringify(optimisticSubtasks?.map(st => ({id: st.id, title: st.title, pos: st.subtask_position}))));

    if (active.id !== over?.id && optimisticSubtasks && task && over) {
      const currentSubtasksForReorder = optimisticSubtasks;
      const oldIndex = currentSubtasksForReorder.findIndex((item) => item.id === active.id);
      const newIndex = currentSubtasksForReorder.findIndex((item) => item.id === over.id);

      console.log('[TaskDetailView] oldIndex:', oldIndex, 'newIndex:', newIndex);
      if (oldIndex === -1 || newIndex === -1) {
        console.warn('[TaskDetailView] Aborting dragEnd: index not found.');
        return;
      }

      const newOrderedSubtasksForBackend = arrayMove(currentSubtasksForReorder, oldIndex, newIndex);
      console.log('[TaskDetailView] Calculated newOrderedSubtasksForBackend:', JSON.stringify(newOrderedSubtasksForBackend.map(st => ({id: st.id, title: st.title, pos: st.subtask_position}))));
      
      setOptimisticSubtasks(newOrderedSubtasksForBackend);
      console.log('[TaskDetailView] Optimistically set optimisticSubtasks.');

      const subtasksToUpdate = newOrderedSubtasksForBackend.map((sub, index) => ({
        id: sub.id,
        subtask_position: index + 1,
      }));
      console.log('[TaskDetailView] Calling updateSubtaskOrderMutation with parentTaskId:', task.id, 'payload:', JSON.stringify(subtasksToUpdate));

      updateSubtaskOrderMutation.mutate(
        { parentTaskId: task.id, orderedSubtasks: subtasksToUpdate },
        {
          onSuccess: (_updatedTasksFromServer) => {
            console.log('[TaskDetailView] updateSubtaskOrderMutation onSuccess. Server response:', JSON.stringify(_updatedTasksFromServer));
            toast.default('Subtask order saved!');
            console.log('[TaskDetailView] Calling refetchSubtasks after mutation success.');
            refetchSubtasks();
            subtasksWereModifiedInThisSessionRef.current = true;
          },
          onError: (error) => {
            console.error('[TaskDetailView] updateSubtaskOrderMutation onError. Error:', error.message);
            toast.error('Failed to save subtask order', error.message);
            console.log('[TaskDetailView] Reverting optimisticSubtasks due to error. Current server state of subtasks:', JSON.stringify(subtasks));
            setOptimisticSubtasks(subtasks);
            console.log('[TaskDetailView] Calling refetchSubtasks after mutation error to ensure consistency.');
            refetchSubtasks();
          },
        }
      );
    } else {
      console.log('[TaskDetailView] handleDragEnd: active.id === over?.id or optimisticSubtasks/task/over missing.');
    }
  };

  if (!isOpen) return null;

  return (
    <RadixDialog.Root open={isOpen} onOpenChange={onOpenChange}>
      <RadixDialog.Portal>
        <RadixDialog.Overlay className="fixed inset-0 bg-black/50 data-[state=open]:animate-overlayShow" />
        <RadixDialog.Content className="fixed top-1/2 left-1/2 w-[90vw] max-w-lg max-h-[85vh] -translate-x-1/2 -translate-y-1/2 rounded-lg bg-white dark:bg-gray-800 p-6 shadow-lg data-[state=open]:animate-contentShow focus:outline-none flex flex-col">
          <RadixDialog.Title className="text-xl font-semibold text-gray-900 dark:text-white mb-1">
            {task ? 'Edit Task' : isLoading? 'Loading...' : 'Task Details'}
          </RadixDialog.Title>
          <RadixDialog.Description className="text-sm text-gray-500 dark:text-gray-400 mb-4">
            View and edit task information.
          </RadixDialog.Description>

          {isLoading && (
            <div className="flex items-center justify-center h-40">
              <Spinner size={32} />
              <p className="ml-2">Loading task details...</p>
            </div>
          )}

          {error && !isLoading && (
            <div className="text-red-500">
              Error loading task: {error.message}
            </div>
          )}
          
          {!taskId && isOpen && !isLoading && (
             <div className="text-gray-500 dark:text-gray-400 p-4">
                No task selected or task ID is missing.
            </div>
          )}

          {!isLoading && !error && task && taskId && (
            <>
              <form onSubmit={(e: FormEvent) => { e.preventDefault(); handleSave(); }} className="flex-grow overflow-y-auto pr-2 space-y-4 custom-scrollbar">
                <div>
                  <Label htmlFor="title">Title</Label>
                  <Input 
                    id="title"
                    name="title"
                    value={formData.title || ''}
                    onChange={handleChange}
                    className="mt-1" 
                    required
                  />
                </div>
                <div>
                  <Label htmlFor="description">Description</Label>
                  <Textarea 
                    id="description"
                    name="description"
                    value={formData.description || ''}
                    onChange={handleChange}
                    className="mt-1" 
                    rows={3} 
                  />
                </div>
                <div>
                  <Label htmlFor="notes">Notes</Label>
                  <Textarea 
                    id="notes"
                    name="notes"
                    value={formData.notes || ''}
                    onChange={handleChange}
                    className="mt-1" 
                    rows={2} 
                  />
                </div>
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <Label htmlFor="status">Status</Label>
                    <select 
                        id="status"
                        name="status"
                        value={formData.status || 'pending'}
                        onChange={handleChange}
                        className="mt-1 block w-full rounded-md border-gray-300 dark:border-gray-600 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 sm:text-sm bg-white dark:bg-gray-700 text-gray-900 dark:text-white p-2"
                    >
                        {ALL_STATUSES.map(s => <option key={s} value={s}>{s.charAt(0).toUpperCase() + s.slice(1)}</option>)}
                    </select>
                  </div>
                  <div>
                    <Label htmlFor="priority">Priority</Label>
                    <select 
                        id="priority"
                        name="priority"
                        value={formData.priority || 0}
                        onChange={handleChange}
                        className="mt-1 block w-full rounded-md border-gray-300 dark:border-gray-600 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 sm:text-sm bg-white dark:bg-gray-700 text-gray-900 dark:text-white p-2"
                    >
                        {ALL_PRIORITIES.map(p => <option key={p.value} value={p.value}>{p.label}</option>)}
                    </select>
                  </div>
                </div>
                <div>
                  <Label htmlFor="category">Category</Label>
                  <Input 
                    id="category" 
                    name="category" 
                    value={formData.category || ''} 
                    onChange={handleChange} 
                    placeholder="e.g., Work, Personal" 
                    className="mt-1"
                  />
                </div>
                <div>
                  <Label htmlFor="due_date">Due Date</Label>
                  <Input 
                    id="due_date" 
                    name="due_date" 
                    type="date" 
                    value={formData.due_date || ''}
                    onChange={handleChange} 
                    className="mt-1"
                  />
                </div>
                <div className="pt-2">
                  <h3 className="text-sm font-medium text-gray-700 dark:text-gray-300">Subtasks</h3>
                  <div className="mt-2 p-2 border border-dashed border-gray-300 dark:border-gray-600 rounded-md min-h-[50px]">
                    <p className="text-xs text-gray-500 dark:text-gray-400">Subtask management will be here.</p>
                  </div>
                </div>

                {/* Subtasks Section */}
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
                      sensors={sensors}
                      collisionDetection={closestCenter}
                      onDragEnd={handleDragEnd}
                    >
                      <SortableContext 
                        items={(optimisticSubtasks || []).map(s => s.id)} 
                        strategy={verticalListSortingStrategy}
                      >
                        <div className="space-y-1 mb-3">
                          {(optimisticSubtasks || subtasks || []).length > 0 ? (
                            (optimisticSubtasks || subtasks || []).map(subtask => (
                              <SubtaskItem 
                                key={subtask.id} 
                                subtask={subtask} 
                                parentTaskId={task.id}
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
                      onKeyDown={(e) => e.key === 'Enter' && handleAddSubtask()}
                    />
                    <Button 
                      type="button" 
                      onClick={handleAddSubtask} 
                      disabled={!newSubtaskTitle.trim() || createTaskMutation.isPending}
                    >
                      {createTaskMutation.isPending ? <Spinner size={16} /> : 'Add'}
                    </Button>
                  </div>
                </div>
              </form>

              <div className="mt-6 flex justify-between items-center pt-4 border-t border-gray-200 dark:border-gray-700">
                {onDeleteTaskFromDetail && taskId && (
                  <Button 
                    variant="danger"
                    onClick={handleDeleteClick}
                    disabled={updateTaskMutation.isPending}
                  >
                    <TrashIcon className="mr-2 h-4 w-4" /> Delete
                  </Button>
                )}
                <div className="flex space-x-2 ml-auto">
                  <RadixDialog.Close asChild>
                    <Button variant="secondary" type="button">Cancel</Button>
                  </RadixDialog.Close>
                  <Button 
                    type="button"
                    onClick={handleSave}
                    disabled={(!parentTaskHasChanges && !subtasksWereModifiedInThisSessionRef.current && !createTaskMutation.isPending) || updateTaskMutation.isPending || isLoading }
                  >
                    {updateTaskMutation.isPending ? <span className="mr-2"><Spinner size={16} /></span> : null}
                    Save Changes
                  </Button>
                </div>
              </div>
            </>
          )}

          {!isLoading && !error && !task && taskId && (
             <div className="text-center text-gray-500 dark:text-gray-400 p-4">
                Task not found. It may have been deleted.
            </div>
          )}

          <RadixDialog.Close asChild>
            <button
              className="absolute top-3.5 right-3.5 inline-flex h-6 w-6 appearance-none items-center justify-center rounded-full text-gray-500 hover:bg-gray-100 dark:text-gray-400 dark:hover:bg-gray-700 focus:outline-none focus:ring-2 focus:ring-gray-400"
              aria-label="Close"
              type="button"
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