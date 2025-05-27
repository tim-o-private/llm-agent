import React from 'react';
import { FormProvider } from 'react-hook-form'; // useForm is part of useEditableEntity
import { z } from 'zod';
import { useEditableEntity } from '@/hooks/useEditableEntity';
import { Task, TaskPriority, TaskCreatePayload, TaskUpdatePayload } from '@/api/types'; // Re-add Task, TaskStatus might be unused from TaskFormData
import { TaskFormData, UseEditableEntityConfig } from '@/types/editableEntityTypes';
import { useTaskStore } from '@/stores/useTaskStore'; // Import the store
import { useAuthStore } from '@/features/auth/useAuthStore'; // Import auth store for user ID
// import * as Form from '@radix-ui/react-form'; // Placeholder for Radix Form
// import { Button, TextField, TextArea, Select, Checkbox } from '@/components/ui'; // Assuming common UI components

// Schema for Task form validation
const taskFormSchema = z.object({
  title: z.string().min(1, 'Title is required'),
  description: z.string()
    .transform(val => (val === '' ? null : val))
    .nullable(), // Input: string | null; Output: string | null. Matches TaskFormData.description.
  status: z.enum(['pending', 'planning', 'in_progress', 'completed', 'skipped', 'deferred']), // TaskStatus from api/types is string union, z.enum creates the type
  priority: z.union([z.literal(0), z.literal(1), z.literal(2), z.literal(3)]) as z.ZodType<TaskPriority>, // Expects number, matches TaskPriority
  due_date: z.string()
    .transform(val => (val === '' ? null : val)) // Input: string; Output: string | null
    .nullable() // Input: string | null; Output: string | null
    .optional(), // Input: string | null | undefined; Output: string | null | undefined. Matches TaskFormData.due_date.
});

interface TaskFormProps {
  taskId: string | null | undefined; // null or undefined for creating a new task
  parentTaskId?: string | null;
  onSaveSuccess?: (savedTaskOrVoid: Task | void) => void; // Adjusted to Task | void
  onCancel?: () => void;
  // Callback to inform parent about dirty state changes
  onDirtyStateChange?: (isDirty: boolean) => void; 
}

const TaskForm: React.FC<TaskFormProps> = ({ 
  taskId, 
  parentTaskId, 
  onSaveSuccess,
  onCancel,
  onDirtyStateChange 
}) => {
  const store = useTaskStore.getState(); // Get store instance for actions/selectors

  const transformDataToForm = (task?: Task): TaskFormData => {
    return {
      title: task?.title || '',
      description: task?.description || null,
      status: task?.status || 'pending',
      priority: task?.priority || 0,
      due_date: task?.due_date ? task.due_date.split('T')[0] : null,
    };
  };
  
  const getEntityDataFn = (id: string | undefined): Task | undefined => {
    if (!id) return undefined;
    return store.getTaskById(id);
  };

  const saveEntityFn = async (
    formData: TaskFormData, 
    originalEntityData?: Task,
    entityIdToSave?: string
  ): Promise<void> => { // Strictly return Promise<void>
    const commonPayload = {
      title: formData.title,
      description: formData.description,
      status: formData.status,
      priority: formData.priority,
      due_date: formData.due_date || null,
    };

    if (entityIdToSave) {
      const updatePayload: TaskUpdatePayload = commonPayload;
      await store.updateTask(entityIdToSave, updatePayload);
      return;
    } else {
      // Get user ID from useAuthStore
      const currentUserId = useAuthStore.getState().user?.id;
      
      const userIdToSet = originalEntityData?.user_id || 
                        (parentTaskId && store.getTaskById(parentTaskId)?.user_id) || 
                        currentUserId;

      if (!userIdToSet) {
        console.error("User ID is missing, cannot create task.");
        throw new Error("User ID is missing for new task. Ensure current user is available or task context provides it.");
      }

      const createPayload: TaskCreatePayload = {
        ...commonPayload,
        parent_task_id: parentTaskId || null,
        user_id: userIdToSet,
      };
      await store.createTask(createPayload);
      return;
    }
  };

  const entityConfig: UseEditableEntityConfig<Task, TaskFormData> = {
    entityId: taskId,
    getEntityDataFn,
    saveEntityFn,
    transformDataToForm,
    formSchema: taskFormSchema,
    defaultFormValues: transformDataToForm(undefined), // For creating new tasks
    entityName: 'Task',
    isCreatable: taskId === null || taskId === undefined,
    onSaveSuccess: (savedDataOrVoid) => {
      // savedDataOrVoid is now consistently void from saveEntityFn
      onSaveSuccess?.(savedDataOrVoid); 
    },
    // onSaveError: (error, _formVals) => { /* Already has console.error in placeholder */ },
  };

  const {
    formMethods,
    isSaving,
    saveError,
    canSave,
    handleSave,
    resetFormToInitial,
    // initialData, // Can get from store if needed for display outside form
    isCreating,
  } = useEditableEntity<Task, TaskFormData>(entityConfig);

  // Inform parent about dirty state changes
  React.useEffect(() => {
    onDirtyStateChange?.(formMethods.formState.isDirty);
  }, [formMethods.formState.isDirty, onDirtyStateChange]);

  const onSubmit = formMethods.handleSubmit(() => {
    handleSave();
  });

  const effectiveOnCancel = () => {
    resetFormToInitial(); // Reset RHF state first
    onCancel?.(); // Then call parent's onCancel
  };

  return (
    <FormProvider {...formMethods}>
      <form onSubmit={onSubmit} className="space-y-4">
        {/* Form title removed, TaskDetailView handles overall dialog title */}
        
        <div>
          <label htmlFor="title" className="block text-sm font-medium text-text-secondary">Title</label>
          <input 
            id="title" 
            {...formMethods.register('title')} 
            className="mt-1 block w-full border border-ui-border rounded-md shadow-sm p-2 focus:ring-accent-focus focus:border-accent-focus sm:text-sm bg-ui-input-bg text-text-primary"
          />
          {formMethods.formState.errors.title && <p className="mt-1 text-sm text-destructive">{formMethods.formState.errors.title.message}</p>}
        </div>

        <div>
          <label htmlFor="description" className="block text-sm font-medium text-text-secondary">Description</label>
          <textarea 
            id="description" 
            {...formMethods.register('description')} 
            className="mt-1 block w-full border border-ui-border rounded-md shadow-sm p-2 focus:ring-accent-focus focus:border-accent-focus sm:text-sm bg-ui-input-bg text-text-primary"
            rows={3}
          />
           {formMethods.formState.errors.description && <p className="mt-1 text-sm text-destructive">{formMethods.formState.errors.description.message}</p>}
        </div>

        <div className="grid grid-cols-2 gap-4">
          <div>
            <label htmlFor="status" className="block text-sm font-medium text-text-secondary">Status</label>
            <select 
              id="status" 
              {...formMethods.register('status')} 
              className="mt-1 block w-full border border-ui-border rounded-md shadow-sm p-2 focus:ring-accent-focus focus:border-accent-focus sm:text-sm bg-ui-input-bg text-text-primary"
            >
              <option value="pending">Pending</option>
              <option value="planning">Planning</option>
              <option value="in_progress">In Progress</option>
              <option value="completed">Completed</option>
              <option value="skipped">Skipped</option>
              <option value="deferred">Deferred</option>
            </select>
             {formMethods.formState.errors.status && <p className="mt-1 text-sm text-destructive">{formMethods.formState.errors.status.message}</p>}
          </div>

          <div>
            <label htmlFor="priority" className="block text-sm font-medium text-text-secondary">Priority</label>
            <select 
              id="priority" 
              {...formMethods.register('priority', { valueAsNumber: true })} 
              className="mt-1 block w-full border border-ui-border rounded-md shadow-sm p-2 focus:ring-accent-focus focus:border-accent-focus sm:text-sm bg-ui-input-bg text-text-primary"
            >
              <option value={0}>None</option>
              <option value={1}>Low</option>
              <option value={2}>Medium</option>
              <option value={3}>High</option>
            </select>
            {formMethods.formState.errors.priority && <p className="mt-1 text-sm text-destructive">{formMethods.formState.errors.priority.message}</p>}
          </div>
        </div>

        <div>
          <label htmlFor="due_date" className="block text-sm font-medium text-text-secondary">Due Date</label>
          <input 
            type="date" 
            id="due_date" 
            {...formMethods.register('due_date')} 
            className="mt-1 block w-full border border-ui-border rounded-md shadow-sm p-2 focus:ring-accent-focus focus:border-accent-focus sm:text-sm bg-ui-input-bg text-text-primary"
          />
           {formMethods.formState.errors.due_date && <p className="mt-1 text-sm text-destructive">{formMethods.formState.errors.due_date.message}</p>}
        </div>
        
        {saveError && <p className="mt-2 text-sm text-destructive">Save error: {saveError.message}</p>}

        <div className="flex justify-end space-x-3 pt-2">
          <button 
            type="button" 
            onClick={effectiveOnCancel} 
            className="px-4 py-2 text-sm font-medium rounded-md shadow-sm border border-ui-border text-text-secondary hover:bg-ui-element-bg-hover focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-accent-focus"
          >
            Cancel
          </button>
          <button 
            type="submit" 
            disabled={!canSave || isSaving} 
            className="px-4 py-2 text-sm font-medium rounded-md shadow-sm text-white bg-brand-primary hover:bg-brand-primary-hover disabled:opacity-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-brand-primary-focus"
          >
            {isSaving ? 'Saving...' : (isCreating ? 'Create Task' : 'Save Changes')}
          </button>
        </div>
      </form>
    </FormProvider>
  );
};

export default TaskForm; 