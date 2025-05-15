import React, { useState, useEffect, useRef, ChangeEvent, FormEvent } from 'react';
import { Input } from '../../ui/Input'; // Corrected path to Input
import { useCreateTask } from '../../../api/hooks/useTaskHooks';
import { parseTaskString } from '../../../utils/taskParser';
import { toast } from 'react-hot-toast';
import { NewTaskData, TaskPriority, TaskStatus, Task } from '../../../api/types';
import { useAuthStore } from '../../../features/auth/useAuthStore';

interface FastTaskInputProps {
  isFocused?: boolean; // Optional prop to control focus externally if needed
  onTaskCreated?: (createdTask: Task) => void;
}

export const FastTaskInput: React.FC<FastTaskInputProps> = ({ 
  isFocused,
  onTaskCreated 
}) => {
  const [inputValue, setInputValue] = useState('');
  const createTaskMutation = useCreateTask();
  const user = useAuthStore((state) => state.user);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (isFocused && inputRef.current) {
      inputRef.current.focus();
    }
  }, [isFocused]);

  const handleSubmit = async (e: FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    if (!inputValue.trim() || !user) return;

    const parsedProps = parseTaskString(inputValue.trim());

    if (!parsedProps.title) {
      toast.error('Task title cannot be empty.');
      return;
    }

    const newTaskPayload: Omit<NewTaskData, 'user_id'> = {
      title: parsedProps.title, // Already asserted as non-empty
      status: 'pending' as TaskStatus, // Default status
      priority: parsedProps.priority ?? (0 as TaskPriority), // Default priority if not parsed
      description: parsedProps.description ?? undefined,
      // Any other defaults or parsed properties can be added here
      // e.g. notes, category, due_date if parser supports them
    };

    try {
      const createdTask = await createTaskMutation.mutateAsync(newTaskPayload);
      toast.success(`Task "${createdTask.title}" created!`);
      setInputValue('');
      if (onTaskCreated) {
        onTaskCreated(createdTask);
      }
    } catch (error) {
      toast.error('Failed to create task. Please try again.');
      console.error('Error creating task:', error);
    }
  };

  return (
    <form onSubmit={handleSubmit} className="w-full">
      <Input
        ref={inputRef}
        type="text"
        placeholder="Type task title & press Enter (e.g., Buy groceries p1 d:milk, eggs)"
        value={inputValue}
        onChange={(e: ChangeEvent<HTMLInputElement>) => setInputValue(e.target.value)}
        className="w-full text-base py-3 px-4"
        // Consider adding a subtle leading icon if desired
      />
    </form>
  );
}; 