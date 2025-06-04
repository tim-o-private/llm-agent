# UI Patterns

**Files**: [`TaskList.tsx`](../webApp/src/components/features/tasks/TaskList.tsx) [`Modal.tsx`](../webApp/src/components/ui/Modal.tsx) [`useTaskHooks.ts`](../webApp/src/api/hooks/useTaskHooks.ts)
**Rules**: [ui-001](../rules/ui-rules.json#ui-001) [ui-002](../rules/ui-rules.json#ui-002) [ui-003](../rules/ui-rules.json#ui-003)

## Pattern 1: Radix + Tailwind

```tsx
// ✅ DO: Radix primitive + Tailwind
import * as Dialog from '@radix-ui/react-dialog';

export function Modal({ children, ...props }) {
  return (
    <Dialog.Root {...props}>
      <Dialog.Portal>
        <Dialog.Overlay className="fixed inset-0 bg-black/50" />
        <Dialog.Content className="fixed top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 bg-ui-element-bg rounded-lg p-6">
          {children}
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  );
}

// ❌ DON'T: @radix-ui/themes components
import { Button } from '@radix-ui/themes';
```

## Pattern 2: Centralized Overlays

```tsx
// ✅ DO: useOverlayStore
import { useOverlayStore } from '@/stores/useOverlayStore';

export function TaskCard({ task }) {
  const { openModal } = useOverlayStore();
  return <div onClick={() => openModal('editTask', { taskId: task.id })}>{task.title}</div>;
}

// ❌ DON'T: Local state
const [isModalOpen, setIsModalOpen] = useState(false);
```

## Pattern 3: React Query Hooks

```tsx
// ✅ DO: Custom hooks
import { useTaskHooks } from '@/api/hooks/useTaskHooks';

export function TaskList() {
  const { data: tasks, isLoading, error } = useTaskHooks.useFetchTasks();
  
  if (isLoading) return <LoadingSpinner />;
  if (error) return <ErrorMessage error={error} />;
  
  return <div>{tasks.map(task => <TaskCard key={task.id} task={task} />)}</div>;
}

// ❌ DON'T: Direct Supabase
const [tasks, setTasks] = useState([]);
useEffect(() => supabase.from('tasks').select('*').then(setTasks), []);
```

## Pattern 4: Semantic Colors

```tsx
// ✅ DO: Semantic tokens
<div className="bg-ui-element-bg text-text-primary border-ui-border">
  <Button className="bg-brand-primary">Save</Button>
</div>

// ❌ DON'T: Hardcoded colors
<div className="bg-blue-500 text-white border-gray-300">
<div style={{ backgroundColor: '#3b82f6' }}>
```

## Pattern 5: Error/Loading States

```tsx
// ✅ DO: Consistent error handling
import { ErrorMessage } from '@/components/ui/ErrorMessage';

export function TaskForm({ taskId }) {
  const { mutate: updateTask, isPending } = useTaskHooks.useUpdateTask();
  
  return (
    <form onSubmit={handleSubmit}>
      <Button disabled={isPending}>
        {isPending ? <LoadingSpinner size="sm" /> : 'Save'}
      </Button>
    </form>
  );
}

// ❌ DON'T: No error handling
const { data } = useQuery('tasks', fetchTasks);
```

## Pattern 6: Forms with Zod

```tsx
// ✅ DO: React Hook Form + Zod
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';

const taskSchema = z.object({
  title: z.string().min(1, 'Title required'),
  description: z.string().optional(),
});

export function TaskForm() {
  const { register, handleSubmit, formState: { errors } } = useForm({
    resolver: zodResolver(taskSchema),
  });
  
  return (
    <form onSubmit={handleSubmit(onSubmit)}>
      <input {...register('title')} />
      {errors.title && <ErrorMessage error={errors.title.message} />}
    </form>
  );
}

// ❌ DON'T: Manual state
const [formData, setFormData] = useState({});
```

## Pattern 7: Accessibility

```tsx
// ✅ DO: ARIA labels and keyboard support
export function TaskCard({ task, onEdit }) {
  return (
    <article 
      className="focus:ring-2 focus:ring-brand-primary"
      tabIndex={0}
      role="button"
      aria-label={`Edit task: ${task.title}`}
      onKeyDown={(e) => e.key === 'Enter' && onEdit()}
      onClick={onEdit}
    >
      <h3>{task.title}</h3>
    </article>
  );
}

// ❌ DON'T: No accessibility
<div onClick={onEdit}>{task.title}</div>
```

## Pattern 8: CSS Animations

```css
/* ✅ DO: CSS transitions */
.modal-overlay {
  opacity: 0;
  transition: opacity 0.2s ease-in-out;
}

.modal-overlay[data-state="open"] {
  opacity: 1;
}

/* ❌ DON'T: framer-motion for simple animations */
```

## Pattern 9: Single Layout

```tsx
// ✅ DO: AppShell for all pages
export function AppShell({ children }) {
  return (
    <div className="min-h-screen bg-ui-bg">
      <Header />
      <main className="container mx-auto px-4 py-8">{children}</main>
    </div>
  );
}

// Usage
export function TasksPage() {
  return <AppShell><TaskList /></AppShell>;
}
```

## Pattern 10: Wrapper Components

```tsx
// ✅ DO: Reusable wrappers
export function Card({ children, className = '', ...props }) {
  return (
    <div className={`bg-ui-element-bg border border-ui-border rounded-lg p-4 ${className}`} {...props}>
      {children}
    </div>
  );
}

// Usage
<Card className="shadow-lg">
  <h2>Task Details</h2>
</Card>
```

## Examples

### Complete Component Example
```tsx
/**
 * @docs memory-bank/patterns/ui-patterns.md#pattern-3-react-query-hooks
 * @rules memory-bank/rules/ui-rules.json#ui-004,ui-005
 * @examples memory-bank/patterns/ui-patterns.md#pattern-5-error-loading-states
 */
import { useTaskHooks } from '@/api/hooks/useTaskHooks';
import { ErrorMessage } from '@/components/ui/ErrorMessage';
import { LoadingSpinner } from '@/components/ui/LoadingSpinner';
import { Card } from '@/components/ui/Card';

export function TaskList() {
  const { data: tasks, isLoading, error } = useTaskHooks.useFetchTasks();
  
  if (isLoading) return <LoadingSpinner />;
  if (error) return <ErrorMessage error={error} />;
  
  return (
    <div className="space-y-4">
      {tasks.map(task => (
        <Card key={task.id}>
          <h3 className="text-text-primary">{task.title}</h3>
          <p className="text-text-secondary">{task.description}</p>
        </Card>
      ))}
    </div>
  );
}
```

### Complete Form Example
```tsx
/**
 * @docs memory-bank/patterns/ui-patterns.md#pattern-6-forms-with-zod
 * @rules memory-bank/rules/ui-rules.json#ui-007
 */
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { Button } from '@/components/ui/Button';
import { ErrorMessage } from '@/components/ui/ErrorMessage';

const taskSchema = z.object({
  title: z.string().min(1, 'Title required'),
  description: z.string().optional(),
});

export function TaskForm({ onSubmit }) {
  const { register, handleSubmit, formState: { errors } } = useForm({
    resolver: zodResolver(taskSchema),
  });
  
  return (
    <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
      <div>
        <input 
          {...register('title')} 
          placeholder="Task title"
          className="w-full p-2 border border-ui-border rounded"
        />
        {errors.title && <ErrorMessage error={errors.title.message} />}
      </div>
      
      <div>
        <textarea 
          {...register('description')} 
          placeholder="Description (optional)"
          className="w-full p-2 border border-ui-border rounded"
        />
      </div>
      
      <Button type="submit" className="bg-brand-primary">
        Create Task
      </Button>
    </form>
  );
}
```

## Quick Reference

**Locations**:
- Shared: `webApp/src/components/ui/`
- Features: `webApp/src/components/features/`
- Hooks: `webApp/src/api/hooks/`
- Stores: `webApp/src/stores/`

**Imports**:
- `@/components/ui/` - Shared components
- `@/api/hooks/` - React Query hooks
- `@/stores/` - Zustand stores

**Dependencies**:
- `@radix-ui/react-*` - UI primitives
- `@tanstack/react-query` - API state
- `react-hook-form` + `zod` - Forms
- `zustand` - Global state 