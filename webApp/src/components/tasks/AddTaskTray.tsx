import React from 'react';
import { Input, Button, Modal, ErrorMessage } from '@/components/ui'; // Added ErrorMessage
import { useCreateTask } from '../../api/hooks/useTaskHooks';
import { useForm, SubmitHandler } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import * as z from 'zod';

const taskSchema = z.object({
  title: z.string().min(1, { message: 'Title is required' }),
});

type TaskFormData = z.infer<typeof taskSchema>;

interface AddTaskTrayProps {
  isOpen: boolean;
  onClose: () => void;
}

const AddTaskTray: React.FC<AddTaskTrayProps> = ({ isOpen, onClose }) => {
  const { mutate: createTask, isPending: isCreatingTask } = useCreateTask();
  
  const {
    register,
    handleSubmit,
    reset,
    formState: { errors, isSubmitting },
  } = useForm<TaskFormData>({
    resolver: zodResolver(taskSchema),
    defaultValues: { title: '' }
  });

  const isLoading = isCreatingTask || isSubmitting;

  const onSubmit: SubmitHandler<TaskFormData> = (data) => {
    createTask(
      { title: data.title, status: 'pending', priority: 0 }, 
      {
        onSuccess: () => {
          reset();
          onClose();
        },
      }
    );
  };

  const handleModalClose = (open: boolean) => {
    if (!open) {
      reset();
      onClose();
    }
  };

  return (
    <Modal
      open={isOpen}
      onOpenChange={handleModalClose}
      title="Add New Task"
    >
      <form onSubmit={handleSubmit(onSubmit)}>
        <div className="mt-4">
          <Input
            type="text"
            placeholder="Enter task title..."
            {...register('title')}
            className="w-full"
            aria-label="Task title"
            aria-invalid={errors.title ? "true" : "false"}
            aria-describedby={errors.title ? "title-error" : undefined} // For screen readers
            disabled={isLoading}
          />
          {errors.title && (
            <ErrorMessage id="title-error">{errors.title.message}</ErrorMessage>
          )}
        </div>
        <div className="mt-5 sm:mt-6 sm:grid sm:grid-flow-row-dense sm:grid-cols-2 sm:gap-3">
          <Button
            variant="primary"
            type="submit"
            className="w-full justify-center sm:col-start-2"
            disabled={isLoading}
          >
            {isLoading ? 'Adding...' : 'Add Task'}
          </Button>
          <Button
            variant="secondary"
            onClick={onClose} 
            className="mt-3 w-full justify-center sm:col-start-1 sm:mt-0"
            disabled={isLoading}
            type="button"
          >
            Cancel
          </Button>
        </div>
      </form>
    </Modal>
  );
};

export default AddTaskTray; 