import React, { useState, useEffect, ChangeEvent, FormEvent } from 'react';
import * as RadixDialog from '@radix-ui/react-dialog';
import { Cross2Icon, TrashIcon } from '@radix-ui/react-icons';
import { useFetchTaskById, useUpdateTask } from '@/api/hooks/useTaskHooks';
import { Task, UpdateTaskData, TaskStatus, TaskPriority } from '@/api/types';
import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/Input';
import { Textarea } from '@/components/ui/Textarea';
import { Label } from '@/components/ui/Label';
import { Spinner } from '@/components/ui/Spinner';
import { toast } from 'react-hot-toast';

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

  const [formData, setFormData] = useState<Partial<Task>>(initialFormState);

  useEffect(() => {
    if (isOpen && taskId) {
      refetch();
    }
  }, [isOpen, taskId, refetch]);

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

  const handleChange = (e: ChangeEvent<HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement>) => {
    const { name, value } = e.target;
    setFormData(prev => ({
      ...prev,
      [name]: name === 'priority' ? parseInt(value, 10) as TaskPriority : value,
    }));
  };

  const handleSave = async () => {
    if (!taskId || !task) return;

    const updates: UpdateTaskData = {};
    let hasChanges = false;

    if (formData.title !== undefined && formData.title !== task.title) {
      updates.title = formData.title;
      hasChanges = true;
    }
    if (formData.description !== undefined && formData.description !== (task.description || '')) {
      updates.description = formData.description;
      hasChanges = true;
    }
    if (formData.notes !== undefined && formData.notes !== (task.notes || '')) {
      updates.notes = formData.notes;
      hasChanges = true;
    }
    if (formData.category !== undefined && formData.category !== (task.category || '')) {
      updates.category = formData.category;
      hasChanges = true;
    }
    const formDueDate = formData.due_date ? new Date(formData.due_date).toISOString() : null;
    const taskDueDate = task.due_date ? new Date(task.due_date).toISOString() : null;
    if (formDueDate !== taskDueDate) {
      updates.due_date = formDueDate;
      hasChanges = true;
    }
    if (formData.status !== undefined && formData.status !== task.status) {
      updates.status = formData.status as TaskStatus;
      hasChanges = true;
    }
    if (formData.priority !== undefined && formData.priority !== task.priority) {
      updates.priority = formData.priority as TaskPriority;
      hasChanges = true;
    }

    if (!hasChanges) {
      toast('No changes to save.');
      return;
    }

    try {
      await updateTaskMutation.mutateAsync({ id: taskId, updates });
      toast.success('Task updated successfully!');
      if (onTaskUpdated) onTaskUpdated();
    } catch (err) { 
      toast.error('Failed to update task.');
      console.error("Failed to update task:", err);
    }
  };
  
  const handleDeleteClick = () => {
    if (taskId && onDeleteTaskFromDetail) {
        if (window.confirm('Are you sure you want to delete this task?')) {
            onDeleteTaskFromDetail(taskId);
        }
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
                    disabled={updateTaskMutation.isPending || isLoading}
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