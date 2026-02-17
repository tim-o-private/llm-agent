import React from 'react';
import * as Form from '@radix-ui/react-form';
import { z } from 'zod';
import { Task, TaskPriority, TaskCreatePayload, TaskUpdatePayload } from '@/api/types';
import { useTaskStore } from '@/stores/useTaskStore';
import { useAuthStore } from '@/features/auth/useAuthStore';
import { Input } from '@/components/ui/Input';
import { Textarea } from '@/components/ui/Textarea';
import { Select, SelectItem } from '@/components/ui/Select';
import { useRadixForm } from '@/hooks/useRadixForm';
import { createComponentLogger } from '@/utils/logger';

const log = createComponentLogger('TaskForm');

// Form data type
interface TaskFormData {
  title: string;
  description: string;
  status: Task['status'];
  priority: TaskPriority;
  due_date: string;
}

// Validation schema
const taskFormSchema = z.object({
  title: z.string().min(1, 'Title is required'),
  description: z.string(),
  status: z.enum(['pending', 'planning', 'in_progress', 'completed', 'skipped', 'deferred']),
  priority: z.union([z.literal(0), z.literal(1), z.literal(2), z.literal(3)]) as z.ZodType<TaskPriority>,
  due_date: z.string(),
});

interface TaskFormProps {
  taskId: string | null | undefined;
  parentTaskId?: string | null;
  onSaveSuccess?: () => void;
  onCancel?: () => void;
  onDirtyStateChange?: (isDirty: boolean) => void;
  showSubtasks?: boolean;
}

// Ref interface for exposing methods
export interface TaskFormRef {
  save: () => Promise<void>;
}

const TaskForm = React.forwardRef<TaskFormRef, TaskFormProps>(
  ({ taskId, parentTaskId, onSaveSuccess, onCancel, onDirtyStateChange }, ref) => {
    log.debug('Render', { taskId });

    // useTaskStore.getState() accessed directly in callbacks below

    // Transform task to form data
    const transformToForm = React.useCallback(
      (task: Task | undefined): TaskFormData => ({
        title: task?.title || '',
        description: task?.description || '',
        status: task?.status || 'pending',
        priority: task?.priority || 0,
        due_date: task?.due_date ? task.due_date.split('T')[0] : '',
      }),
      [],
    );

    // Save entity function
    const saveEntity = React.useCallback(
      async (formData: TaskFormData, entityId: string | undefined, isCreating: boolean) => {
        const commonPayload = {
          title: formData.title,
          description: formData.description || null,
          status: formData.status,
          priority: formData.priority,
          due_date: formData.due_date || null,
        };

        if (isCreating) {
          // Create new task
          const currentUserId = useAuthStore.getState().user?.id;
          const userIdToSet =
            (parentTaskId && useTaskStore.getState().getTaskById(parentTaskId)?.user_id) || currentUserId;

          if (!userIdToSet) {
            throw new Error('User ID is missing for new task');
          }

          const createPayload: TaskCreatePayload = {
            ...commonPayload,
            parent_task_id: parentTaskId || null,
            user_id: userIdToSet,
          };
          await useTaskStore.getState().createTask(createPayload);
        } else {
          // Update existing task
          const updatePayload: TaskUpdatePayload = commonPayload;
          await useTaskStore.getState().updateTask(entityId!, updatePayload);
        }
      },
      [parentTaskId],
    );

    // Use the generic form hook
    const { formData, handleFieldChange, handleSave, saveError, isSaving } = useRadixForm<Task, TaskFormData>({
      entityId: taskId,
      getEntity: (id) => (id ? useTaskStore.getState().getTaskById(id) : undefined),
      transformToForm,
      schema: taskFormSchema,
      saveEntity,
      onSaveSuccess,
      onCancel,
      onDirtyStateChange,
    });

    // Expose save method through ref
    React.useImperativeHandle(
      ref,
      () => ({
        save: handleSave,
      }),
      [handleSave],
    );

    return (
      <div className="space-y-4">
        {/* Main Form */}
        <Form.Root
          onSubmit={(event: React.FormEvent) => {
            event.preventDefault();
            handleSave();
          }}
          className="space-y-4"
        >
          <Form.Field name="title">
            <div style={{ display: 'flex', alignItems: 'baseline', justifyContent: 'space-between' }}>
              <Form.Label className="block text-sm font-medium text-text-secondary">Title</Form.Label>
              <Form.Message className="text-sm text-destructive" match="valueMissing">
                Please enter a title
              </Form.Message>
            </div>
            <Form.Control asChild>
              <Input
                value={formData.title}
                onChange={(e) => handleFieldChange('title', e.target.value)}
                className="mt-1"
                autoComplete="off"
                required
              />
            </Form.Control>
          </Form.Field>

          <Form.Field name="description">
            <Form.Label className="block text-sm font-medium text-text-secondary">Description</Form.Label>
            <Form.Control asChild>
              <Textarea
                value={formData.description}
                onChange={(e) => handleFieldChange('description', e.target.value)}
                className="mt-1"
                rows={3}
              />
            </Form.Control>
          </Form.Field>

          <div className="grid grid-cols-2 gap-4">
            <Form.Field name="status">
              <Form.Label className="block text-sm font-medium text-text-secondary mb-1">Status</Form.Label>
              <Form.Control asChild>
                <Select
                  value={formData.status}
                  onValueChange={(value) => handleFieldChange('status', value)}
                  size="2"
                  placeholder="Select status"
                >
                  <SelectItem value="pending">Pending</SelectItem>
                  <SelectItem value="planning">Planning</SelectItem>
                  <SelectItem value="in_progress">In Progress</SelectItem>
                  <SelectItem value="completed">Completed</SelectItem>
                  <SelectItem value="skipped">Skipped</SelectItem>
                  <SelectItem value="deferred">Deferred</SelectItem>
                </Select>
              </Form.Control>
            </Form.Field>

            <Form.Field name="priority">
              <Form.Label className="block text-sm font-medium text-text-secondary mb-1">Priority</Form.Label>
              <Form.Control asChild>
                <Select
                  value={formData.priority.toString()}
                  onValueChange={(value) => handleFieldChange('priority', parseInt(value))}
                  size="2"
                  placeholder="Select priority"
                >
                  <SelectItem value="0">None</SelectItem>
                  <SelectItem value="1">Low</SelectItem>
                  <SelectItem value="2">Medium</SelectItem>
                  <SelectItem value="3">High</SelectItem>
                </Select>
              </Form.Control>
            </Form.Field>
          </div>

          <Form.Field name="due_date">
            <Form.Label className="block text-sm font-medium text-text-secondary">Due Date</Form.Label>
            <Form.Control asChild>
              <Input
                type="date"
                value={formData.due_date}
                onChange={(e) => handleFieldChange('due_date', e.target.value)}
                className="mt-1"
              />
            </Form.Control>
          </Form.Field>

          {saveError && <p className="mt-2 text-sm text-destructive">Save error: {saveError.message}</p>}

          {/* Hidden submit button for form submission */}
          <Form.Submit asChild>
            <button type="submit" style={{ display: 'none' }} disabled={isSaving} />
          </Form.Submit>
        </Form.Root>
      </div>
    );
  },
);

export default TaskForm;
