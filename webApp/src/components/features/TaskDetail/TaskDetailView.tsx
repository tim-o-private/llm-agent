import React, { useState, useEffect, ChangeEvent, FormEvent } from 'react';
import * as Dialog from '@radix-ui/react-dialog';
import { Cross2Icon } from '@radix-ui/react-icons';
import { useFetchTaskById, useUpdateTask, useDeleteTask } from '@/api/hooks/useTaskHooks';
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
  onTaskUpdated?: () => void;
  onTaskDeleted?: () => void;
}

const ALL_STATUSES: TaskStatus[] = ['pending', 'planning', 'in_progress', 'completed', 'skipped', 'deferred'];
const ALL_PRIORITIES: { label: string; value: TaskPriority }[] = [
  { label: 'None', value: 0 },
  { label: 'Low', value: 1 },
  { label: 'Medium', value: 2 },
  { label: 'High', value: 3 },
];

export const TaskDetailView: React.FC<TaskDetailViewProps> = ({
  taskId,
  isOpen,
  onOpenChange,
  onTaskUpdated,
  onTaskDeleted,
}) => {
  const { data: task, isLoading, error, refetch } = useFetchTaskById(taskId);
  const updateTaskMutation = useUpdateTask();

  // Form state
  const [currentTitle, setCurrentTitle] = useState('');
  const [currentDescription, setCurrentDescription] = useState('');
  const [currentNotes, setCurrentNotes] = useState('');
  const [currentStatus, setCurrentStatus] = useState<TaskStatus>('pending');
  const [currentPriority, setCurrentPriority] = useState<TaskPriority>(0);

  useEffect(() => {
    if (isOpen && taskId) {
      refetch();
    }
  }, [isOpen, taskId, refetch]);

  useEffect(() => {
    if (task) {
      setCurrentTitle(task.title || '');
      setCurrentDescription(task.description || '');
      setCurrentNotes(task.notes || '');
      setCurrentStatus(task.status || 'pending');
      setCurrentPriority(task.priority || 0);
    }
  }, [task]);

  const handleSave = async () => {
    if (!taskId || !task) return;

    const updates: UpdateTaskData = {
      title: currentTitle,
      description: currentDescription,
      notes: currentNotes,
      status: currentStatus,
      priority: currentPriority,
    };

    if (
      currentTitle === task.title &&
      currentDescription === (task.description || '') &&
      currentNotes === (task.notes || '') &&
      currentStatus === task.status &&
      currentPriority === task.priority
    ) {
      toast.success('No changes to save.');
      onOpenChange(false);
      return;
    }

    try {
      await updateTaskMutation.mutateAsync({ id: taskId, updates });
      toast.success('Task updated successfully!');
      if (onTaskUpdated) {
        onTaskUpdated();
      }
      onOpenChange(false);
    } catch (err) {
      toast.error('Failed to update task.');
      console.error('Error updating task:', err);
    }
  };

  if (!taskId && isOpen) {
    return (
        <Dialog.Root open={isOpen} onOpenChange={onOpenChange}>
            <Dialog.Portal>
                <Dialog.Overlay className="fixed inset-0 bg-black/50 data-[state=open]:animate-overlayShow" />
                <Dialog.Content className="fixed top-1/2 left-1/2 w-[90vw] max-w-md max-h-[85vh] -translate-x-1/2 -translate-y-1/2 rounded-lg bg-white dark:bg-gray-800 p-6 shadow-lg data-[state=open]:animate-contentShow focus:outline-none">
                    <Dialog.Title className="text-lg font-medium text-gray-900 dark:text-white mb-4">
                        Error
                    </Dialog.Title>
                    <Dialog.Description className="text-sm text-gray-600 dark:text-gray-300 mb-4">
                        No task ID provided.
                    </Dialog.Description>
                    <Dialog.Close asChild>
                        <button
                            className="absolute top-3 right-3 inline-flex h-6 w-6 appearance-none items-center justify-center rounded-full text-gray-500 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-700 focus:outline-none focus:ring-2 focus:ring-gray-400 dark:focus:ring-gray-600"
                            aria-label="Close"
                        >
                            <Cross2Icon />
                        </button>
                    </Dialog.Close>
                </Dialog.Content>
            </Dialog.Portal>
        </Dialog.Root>
    );
  }

  return (
    <Dialog.Root open={isOpen} onOpenChange={onOpenChange}>
      <Dialog.Portal>
        <Dialog.Overlay className="fixed inset-0 bg-black/50 data-[state=open]:animate-overlayShow" />
        <Dialog.Content className="fixed top-1/2 left-1/2 w-[90vw] max-w-lg max-h-[85vh] -translate-x-1/2 -translate-y-1/2 rounded-lg bg-white dark:bg-gray-800 p-6 shadow-lg data-[state=open]:animate-contentShow focus:outline-none flex flex-col">
          <Dialog.Title className="text-xl font-semibold text-gray-900 dark:text-white mb-1">
            Task Details
          </Dialog.Title>
          <Dialog.Description className="text-sm text-gray-500 dark:text-gray-400 mb-4">
            View and edit task information.
          </Dialog.Description>

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

          {!isLoading && !error && task && (
            <form onSubmit={(e: FormEvent) => { e.preventDefault(); handleSave(); }} className="flex-grow overflow-y-auto pr-2 space-y-4">
              <div>
                <Label htmlFor="task-title">Title</Label>
                <Input 
                  id="task-title" 
                  value={currentTitle}
                  onChange={(e: ChangeEvent<HTMLInputElement>) => setCurrentTitle(e.target.value)}
                  className="mt-1" 
                  required
                />
              </div>
              <div>
                <Label htmlFor="task-description">Description</Label>
                <Textarea 
                  id="task-description" 
                  value={currentDescription}
                  onChange={(e: ChangeEvent<HTMLTextAreaElement>) => setCurrentDescription(e.target.value)}
                  className="mt-1" 
                  rows={3} 
                />
              </div>
              <div>
                <Label htmlFor="task-notes">Notes</Label>
                <Textarea 
                  id="task-notes" 
                  value={currentNotes}
                  onChange={(e: ChangeEvent<HTMLTextAreaElement>) => setCurrentNotes(e.target.value)}
                  className="mt-1" 
                  rows={2} 
                />
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div>
                    <Label htmlFor="task-status">Status</Label>
                    <select 
                        id="task-status"
                        value={currentStatus}
                        onChange={(e: ChangeEvent<HTMLSelectElement>) => setCurrentStatus(e.target.value as TaskStatus)}
                        className="mt-1 block w-full rounded-md border-gray-300 dark:border-gray-600 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 sm:text-sm bg-white dark:bg-gray-700 text-gray-900 dark:text-white p-2"
                    >
                        {ALL_STATUSES.map(s => <option key={s} value={s}>{s.charAt(0).toUpperCase() + s.slice(1)}</option>)}
                    </select>
                </div>
                <div>
                    <Label htmlFor="task-priority">Priority</Label>
                    <select 
                        id="task-priority"
                        value={currentPriority}
                        onChange={(e: ChangeEvent<HTMLSelectElement>) => setCurrentPriority(Number(e.target.value) as TaskPriority)}
                        className="mt-1 block w-full rounded-md border-gray-300 dark:border-gray-600 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 sm:text-sm bg-white dark:bg-gray-700 text-gray-900 dark:text-white p-2"
                    >
                        {ALL_PRIORITIES.map(p => <option key={p.value} value={p.value}>{p.label}</option>)}
                    </select>
                </div>
              </div>
            </form>
          )}

          {!isLoading && !error && !task && taskId && (
             <div className="text-gray-500 dark:text-gray-400">
                Task not found or you may not have permission to view it.
            </div>
          )}

          <div className="mt-6 flex justify-end space-x-2 pt-4 border-t border-gray-200 dark:border-gray-700">
            <Dialog.Close asChild>
              <Button variant="secondary" type="button">Cancel</Button>
            </Dialog.Close>
            <Button 
              type="button"
              onClick={handleSave} 
              disabled={updateTaskMutation.isPending || isLoading}
            >
              {updateTaskMutation.isPending ? <span className="mr-2"><Spinner size={16} /></span> : null}
              Save Changes
            </Button>
          </div>

          <Dialog.Close asChild>
            <button
              className="absolute top-3 right-3 inline-flex h-6 w-6 appearance-none items-center justify-center rounded-full text-gray-500 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-700 focus:outline-none focus:ring-2 focus:ring-gray-400 dark:focus:ring-gray-600"
              aria-label="Close"
              type="button"
            >
              <Cross2Icon />
            </button>
          </Dialog.Close>
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  );
}; 