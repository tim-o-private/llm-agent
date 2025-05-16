import React, { useState, useEffect, useRef, ChangeEvent } from 'react';
import { Input } from '@/components/ui/Input';
import { useCreateTask } from '@/api/hooks/useTaskHooks';
import { parseTaskString } from '@/utils/taskParser';
import { toast } from 'react-hot-toast';
import { NewTaskData, Task } from '@/api/types';

interface FastTaskInputProps {
  isFocused: boolean;
  onTaskCreated: (createdTask: Task) => void;
  onBlurred: () => void;
}

export const FastTaskInput: React.FC<FastTaskInputProps> = ({ isFocused, onTaskCreated, onBlurred }) => {
  const [inputValue, setInputValue] = useState('');
  const createTaskMutation = useCreateTask();
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (isFocused && inputRef.current) {
      inputRef.current.focus();
    } else if (isFocused && !inputRef.current) {
    }
  }, [isFocused]);

  const handleSubmit = async (e?: React.FormEvent<HTMLFormElement>) => {
    e?.preventDefault();
    if (!inputValue.trim()) return;

    const parsedResult = parseTaskString(inputValue);

    if (!parsedResult.title || parsedResult.title.trim() === '') {
      toast.error("Task title cannot be empty.");
      return;
    }

    const taskPayload: Omit<NewTaskData, 'user_id'> = {
      title: parsedResult.title,
      description: parsedResult.description ?? null,
      notes: parsedResult.notes ?? null,
      status: parsedResult.status ?? 'pending',
      priority: parsedResult.priority ?? 0,
      category: parsedResult.category ?? null,
      due_date: parsedResult.due_date ?? null,
      completed: parsedResult.completed ?? false,
      parent_task_id: parsedResult.parent_task_id ?? null,
      subtask_position: parsedResult.subtask_position ?? null,
    };
    
    try {
      const createdTask = await createTaskMutation.mutateAsync(taskPayload);
      toast.success('Task created!');
      setInputValue('');
      if (inputRef.current) {
        inputRef.current.blur();
      }
      onTaskCreated(createdTask);
      onBlurred();
    } catch (error) {
      toast.error('Failed to create task. Please try again.');
      console.error('Error creating task:', error);
    }
  };

  const handleInputChange = (e: ChangeEvent<HTMLInputElement>) => {
    setInputValue(e.target.value);
  };

  return (
    <form onSubmit={handleSubmit} className="w-full">
      <Input
        ref={inputRef}
        type="text"
        placeholder="Type task title & press Enter (e.g., Buy groceries p1 d:milk, eggs)"
        value={inputValue}
        onChange={handleInputChange}
        onBlur={() => {
          onBlurred();
        }}
        className="w-full text-base py-3 px-4"
      />
    </form>
  );
}; 