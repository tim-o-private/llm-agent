import React, { useState, useEffect, useRef, ChangeEvent, forwardRef, KeyboardEvent } from 'react';
import { Input } from '@/components/ui/Input';
import { parseTaskString } from '@/utils/taskParser';
import { toast } from '@/components/ui/toast';
import { NewTaskData } from '@/api/types';
import { useTaskStore } from '@/stores/useTaskStore';

interface FastTaskInputProps {
  isFocused: boolean;
  onTaskCreated: (taskId: string) => void;
  onBlurred: () => void;
  onFocused?: () => void;
}

export const FastTaskInput = forwardRef<HTMLInputElement, FastTaskInputProps>((
  { isFocused, onTaskCreated, onBlurred, onFocused }, 
  ref
) => {
  const [inputValue, setInputValue] = useState('');
  const createTask = useTaskStore(state => state.createTask);
  const internalInputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (isFocused && internalInputRef.current) {
      internalInputRef.current.focus();
    }
  }, [isFocused]);

  const handleSubmit = async (e?: React.FormEvent<HTMLFormElement>) => {
    e?.preventDefault();
    if (!inputValue.trim()) return;

    const parsedResult = parseTaskString(inputValue);

    const title = parsedResult.title?.trim();

    if (!title) {
      toast.error("Task title cannot be empty.");
      return;
    }

    const newTaskData: Omit<NewTaskData, 'user_id'> = {
      title: title as string,
      description: parsedResult.description || '',
      notes: parsedResult.notes ?? null,
      status: parsedResult.status ?? 'pending',
      priority: parsedResult.priority ?? 0,
      category: parsedResult.category ?? null,
      due_date: parsedResult.due_date ?? null,
      completed_at: parsedResult.completed_at ?? null,
    };
    
    try {
      const taskId = createTask(newTaskData);
      setInputValue('');
      
      if (internalInputRef.current) {
        internalInputRef.current.blur();
      }
      
      onTaskCreated(taskId);
    } catch (error) {
      console.error("Error creating task:", error);
      toast.error('Failed to create task.', error instanceof Error ? error.message : 'Please try again.');
    }
  };

  const handleInputChange = (e: ChangeEvent<HTMLInputElement>) => {
    setInputValue(e.target.value);
  };

  const handleFocus = () => {
    if (onFocused) {
      onFocused();
    }
  };

  const handleBlur = () => {
    setTimeout(() => {
        if (document.activeElement !== internalInputRef.current) {
            if (onBlurred) {
                onBlurred();
            }
        }
    }, 0);
  };

  const handleKeyDown = (event: KeyboardEvent<HTMLInputElement>) => {
    if (event.key === 'Escape') {
      event.preventDefault();
      setInputValue('');
      if (internalInputRef.current) {
        internalInputRef.current.blur();
      }
    }
  };

  return (
    <form onSubmit={handleSubmit} className="w-full">
      <Input
        ref={element => {
            if (typeof ref === 'function') {
              ref(element);
            }
            (internalInputRef as React.MutableRefObject<HTMLInputElement | null>).current = element;
          }}
        type="text"
        placeholder="Type task title & press Enter (e.g., Buy groceries p1 d:milk, eggs)"
        value={inputValue}
        onChange={handleInputChange}
        onFocus={handleFocus}
        onBlur={handleBlur}
        onKeyDown={handleKeyDown}
        className="w-full text-base py-3 px-4"
      />
    </form>
  );
});

FastTaskInput.displayName = 'FastTaskInput'; 