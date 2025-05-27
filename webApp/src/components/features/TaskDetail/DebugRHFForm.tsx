import React from 'react';
import { useForm, FormProvider } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { Input } from '@/components/ui/Input';
import { Textarea } from '@/components/ui/Textarea';

// Minimal schema matching TaskForm
const debugSchema = z.object({
  title: z.string().min(1, 'Title is required'),
  description: z.string().nullable(),
  status: z.enum(['pending', 'planning', 'in_progress', 'completed', 'skipped', 'deferred']),
  priority: z.union([z.literal(0), z.literal(1), z.literal(2), z.literal(3)]),
  due_date: z.string().nullable().optional(),
});

type DebugFormData = z.infer<typeof debugSchema>;

export const DebugRHFForm: React.FC = () => {
  const formMethods = useForm<DebugFormData>({
    resolver: zodResolver(debugSchema),
    mode: 'onChange',
    defaultValues: {
      title: '',
      description: null,
      status: 'pending',
      priority: 0,
      due_date: null,
    },
  });

  const onSubmit = (data: DebugFormData) => {
    console.log('Form submitted:', data);
  };

  // Watch all values to see changes
  const watchedValues = formMethods.watch();
  // Removed console.log to prevent infinite loop

  return (
    <FormProvider {...formMethods}>
      <div className="p-4 border border-blue-300 rounded-md space-y-4">
        <h3 className="text-lg font-semibold">Debug React Hook Form</h3>
        
        <form onSubmit={formMethods.handleSubmit(onSubmit)} className="space-y-4">
          <div>
            <label htmlFor="rhf-title" className="block text-sm font-medium">Title</label>
            <Input 
              id="rhf-title"
              {...formMethods.register('title')}
              placeholder="Type here..."
            />
            {formMethods.formState.errors.title && (
              <p className="text-xs text-red-500">{formMethods.formState.errors.title.message}</p>
            )}
            <p className="text-xs text-gray-500">Current: "{watchedValues.title}"</p>
          </div>

          <div>
            <label htmlFor="rhf-description" className="block text-sm font-medium">Description</label>
            <Textarea 
              id="rhf-description"
              {...formMethods.register('description')}
              placeholder="Type description..."
              rows={3}
            />
            <p className="text-xs text-gray-500">Current: "{watchedValues.description}"</p>
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <label htmlFor="rhf-status" className="block text-sm font-medium">Status</label>
              <select 
                id="rhf-status"
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
              <p className="text-xs text-gray-500">Current: "{watchedValues.status}"</p>
            </div>

            <div>
              <label htmlFor="rhf-priority" className="block text-sm font-medium">Priority</label>
              <select 
                id="rhf-priority"
                {...formMethods.register('priority', { valueAsNumber: true })}
                className="mt-1 block w-full border border-ui-border rounded-md shadow-sm p-2 focus:ring-accent-focus focus:border-accent-focus sm:text-sm bg-ui-input-bg text-text-primary"
              >
                <option value={0}>None</option>
                <option value={1}>Low</option>
                <option value={2}>Medium</option>
                <option value={3}>High</option>
              </select>
              <p className="text-xs text-gray-500">Current: {watchedValues.priority}</p>
            </div>
          </div>

          <div>
            <label htmlFor="rhf-due-date" className="block text-sm font-medium">Due Date</label>
            <input 
              type="date"
              id="rhf-due-date"
              {...formMethods.register('due_date')}
              className="mt-1 block w-full border border-ui-border rounded-md shadow-sm p-2 focus:ring-accent-focus focus:border-accent-focus sm:text-sm bg-ui-input-bg text-text-primary"
            />
            <p className="text-xs text-gray-500">Current: "{watchedValues.due_date}"</p>
          </div>

          <button 
            type="submit" 
            className="px-4 py-2 bg-blue-500 text-white rounded-md hover:bg-blue-600"
          >
            Test Submit
          </button>
        </form>

        <div className="text-xs">
          <p><strong>Form State:</strong></p>
          <p>isDirty: {formMethods.formState.isDirty.toString()}</p>
          <p>isValid: {formMethods.formState.isValid.toString()}</p>
          <p>Errors: {JSON.stringify(formMethods.formState.errors)}</p>
        </div>
      </div>
    </FormProvider>
  );
}; 