import React, { useState, useEffect, ChangeEvent } from 'react';
import * as RadixDialog from '@radix-ui/react-dialog';
import { Cross2Icon } from '@radix-ui/react-icons';
import { useQueryClient } from '@tanstack/react-query';
import { useFetchTaskById, useUpdateTask } from '@/api/hooks/useTaskHooks';
import { Task } from '@/api/types';
import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/Input';
import { Label } from '@/components/ui/Label';
import { Textarea } from '@/components/ui/Textarea';
import { Spinner } from '@/components/ui/Spinner';
import { toast } from '@/components/ui/toast';
import { useAuthStore } from '@/features/auth/useAuthStore';

interface PrioritizeViewModalProps {
  taskId: string | null;
  isOpen: boolean;
  onOpenChange: (isOpen: boolean) => void;
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  onStartFocusSession: (task: Task, sessionConfig: any) => void; 
}

const initialSessionConfig = {
  breakdown: '',
  timerDuration: 25 * 60, // Default 25 minutes in seconds
};

export const PrioritizeViewModal: React.FC<PrioritizeViewModalProps> = ({
  taskId,
  isOpen,
  onOpenChange,
  onStartFocusSession,
}) => {
  const queryClient = useQueryClient();
  const { data: task, isLoading, error, refetch } = useFetchTaskById(taskId);
  const updateTaskMutation = useUpdateTask();

  const [motivation, setMotivation] = useState('');
  const [completionNote, setCompletionNote] = useState('');
  const [sessionBreakdown, setSessionBreakdown] = useState('');
  const [timerDuration, setTimerDuration] = useState(initialSessionConfig.timerDuration); // in seconds

  useEffect(() => {
    if (isOpen && taskId) {
      refetch();
    }
  }, [isOpen, taskId, refetch]);

  useEffect(() => {
    if (task) {
      setMotivation(task.motivation || '');
      setCompletionNote(task.completion_note || '');
      setSessionBreakdown(''); // Reset session-specific breakdown
      setTimerDuration(initialSessionConfig.timerDuration);
    } else {
      setMotivation('');
      setCompletionNote('');
      setSessionBreakdown('');
      setTimerDuration(initialSessionConfig.timerDuration);
    }
  }, [task]);

  const handleSaveChangesAndStart = async () => {
    if (!task) {
      toast.error('Task data not loaded.');
      return;
    }

    const updates: Partial<Task> = {};
    let hasChanges = false;

    if (motivation !== (task.motivation || '')) {
      updates.motivation = motivation;
      hasChanges = true;
    }
    if (completionNote !== (task.completion_note || '')) {
      updates.completion_note = completionNote;
      hasChanges = true;
    }

    let currentTaskData = task;

    if (hasChanges) {
      try {
        const updatedTaskResult = await updateTaskMutation.mutateAsync({ id: task.id, updates });
        if (updatedTaskResult) {
            currentTaskData = updatedTaskResult; // Use the returned updated task
        }
        toast.success('Task details updated for focus session.');
        // Invalidate to ensure other views get the update, though we have currentTaskData
        queryClient.invalidateQueries({ queryKey: ['tasks', task.id] });
        queryClient.invalidateQueries({ queryKey: ['tasks', useAuthStore.getState().user?.id] }); // For the list view

      } catch (err) {
        toast.error('Failed to update task details.');
        console.error("Failed to update task for focus session:", err);
        return; 
      }
    }
    
    onStartFocusSession(currentTaskData, {
        breakdown: sessionBreakdown,
        timerDuration: timerDuration,
    });
    onOpenChange(false); // Close modal
  };

  if (!isOpen) return null;

  return (
    <RadixDialog.Root open={isOpen} onOpenChange={onOpenChange}>
      <RadixDialog.Portal>
        <RadixDialog.Overlay className="fixed inset-0 bg-black/50 data-[state=open]:animate-overlayShow" />
        <RadixDialog.Content className="fixed top-1/2 left-1/2 w-[90vw] max-w-lg max-h-[85vh] -translate-x-1/2 -translate-y-1/2 rounded-lg bg-ui-modal-bg p-6 shadow-lg data-[state=open]:animate-contentShow focus:outline-none flex flex-col">
          <RadixDialog.Title className="text-xl font-semibold text-text-primary mb-1">
            {isLoading ? 'Loading...' : task ? `Prepare: ${task.title}` : 'Prepare Task'}
          </RadixDialog.Title>
          <RadixDialog.Description className="text-sm text-text-muted mb-4">
            Focus your intent before starting this task.
          </RadixDialog.Description>

          {isLoading && (
            <div className="flex items-center justify-center h-40">
              <Spinner size={32} />
              <p className="ml-2">Loading task details...</p>
            </div>
          )}

          {error && !isLoading && (
            <div className="text-destructive">
              Error loading task: {error.message}
            </div>
          )}
          
          {!taskId && isOpen && !isLoading && (
             <div className="text-text-muted p-4">
                No task selected or task ID is missing.
            </div>
          )}

          {!isLoading && !error && task && taskId && (
            <>
              <div className="flex-grow overflow-y-auto pr-2 space-y-4 custom-scrollbar">
                <div>
                  <Label htmlFor="motivation">Why is this task important right now?</Label>
                  <Textarea 
                    id="motivation"
                    name="motivation"
                    value={motivation}
                    onChange={(e: ChangeEvent<HTMLTextAreaElement>) => setMotivation(e.target.value)}
                    className="mt-1" 
                    rows={3} 
                    placeholder="e.g., This will unblock the team for the next phase..."
                  />
                </div>
                <div>
                  <Label htmlFor="completion_note">What does 'done' look like for this session/task?</Label>
                  <Textarea 
                    id="completion_note"
                    name="completion_note"
                    value={completionNote}
                    onChange={(e: ChangeEvent<HTMLTextAreaElement>) => setCompletionNote(e.target.value)}
                    className="mt-1" 
                    rows={3} 
                    placeholder="e.g., Feature X is implemented and unit tests pass."
                  />
                </div>
                <div>
                  <Label htmlFor="session_breakdown">Key steps for this focus session:</Label>
                  <Textarea 
                    id="session_breakdown"
                    name="session_breakdown"
                    value={sessionBreakdown}
                    onChange={(e: ChangeEvent<HTMLTextAreaElement>) => setSessionBreakdown(e.target.value)}
                    className="mt-1" 
                    rows={2} 
                    placeholder="1. Outline function A. 2. Implement core logic. 3. Write test cases."
                  />
                </div>
                <div>
                  <Label htmlFor="timer_duration">Focus Session Duration:</Label>
                  <div className="mt-1 flex items-center space-x-2">
                    <Input 
                        type="number" 
                        id="timer_duration_minutes"
                        name="timer_duration_minutes"
                        value={timerDuration / 60}
                        onChange={(e) => setTimerDuration(parseInt(e.target.value) * 60)}
                        className="w-20"
                        min="5"
                        step="5"
                    />
                    <span>minutes</span>
                  </div>
                </div>
              </div>

              <div className="mt-6 flex justify-end items-center pt-4 border-t border-ui-border space-x-2">
                <RadixDialog.Close asChild>
                  <Button variant="soft" type="button">Cancel</Button>
                </RadixDialog.Close>
                <Button 
                  type="button"
                  onClick={handleSaveChangesAndStart} 
                  disabled={updateTaskMutation.isPending || isLoading}
                >
                  {updateTaskMutation.isPending || isLoading ? <span className="mr-2"><Spinner size={16} /></span> : null}
                  Start Focus Session
                </Button>
              </div>
            </>
          )}
          <RadixDialog.Close asChild>
            <button
              className="absolute top-3.5 right-3.5 inline-flex h-6 w-6 appearance-none items-center justify-center rounded-full text-text-muted hover:bg-ui-interactive-bg-hover"
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

export default PrioritizeViewModal; 