# UI Patterns

**Files**: [`TaskList.tsx`](../webApp/src/components/features/tasks/TaskList.tsx) [`Modal.tsx`](../webApp/src/components/ui/Modal.tsx) [`useTaskHooks.ts`](../webApp/src/api/hooks/useTaskHooks.ts)
**Rules**: [ui-001](../rules/ui-rules.json#ui-001) [ui-002](../rules/ui-rules.json#ui-002) [ui-003](../rules/ui-rules.json#ui-003)

## Pattern 1: Radix Themes + Primitives + Tailwind

```tsx
// ✅ DO: Radix Themes provider for theming foundation
// main.tsx
import { Theme } from '@radix-ui/themes';
<Theme accentColor="violet" grayColor="slate" appearance={effectiveAppearance}>
  <App />
</Theme>

// ✅ DO: Radix primitives + semantic Tailwind tokens
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

// ✅ DO: Custom components using Radix CSS variables
export const Button = ({ variant = 'primary', className, ...props }) => (
  <button
    className={clsx(
      'btn',
      { 'btn-primary': variant === 'primary' },
      className
    )}
    {...props}
  />
);

// ❌ DON'T: Pre-styled Radix Themes components
import { Button } from '@radix-ui/themes';

// ❌ DON'T: Hardcoded colors
<div className="bg-blue-500 text-white border-red-400">
```

## Pattern 2: Semantic Color Tokens

```tsx
// ✅ DO: Semantic tokens from tailwind.config.js
<div className="bg-ui-element-bg text-text-primary border-ui-border">
  <Button className="bg-brand-primary text-white">Save</Button>
</div>

// ❌ DON'T: Tailwind default colors
<div className="bg-gray-100 text-gray-900 border-gray-300">

// ❌ DON'T: Inline hardcoded colors
<div style={{ backgroundColor: '#3b82f6' }}>
```

## Pattern 3: React Query Hooks

```tsx
// ✅ DO: Custom hooks for API state
import { useTaskHooks } from '@/api/hooks/useTaskHooks';

export function TaskList() {
  const { data: tasks, isLoading, error } = useTaskHooks.useFetchTasks();
  
  if (isLoading) return <LoadingSpinner />;
  if (error) return <ErrorMessage error={error} />;
  
  return <div>{tasks.map(task => <TaskCard key={task.id} task={task} />)}</div>;
}

// ❌ DON'T: Direct Supabase calls
const [tasks, setTasks] = useState([]);
useEffect(() => supabase.from('tasks').select('*').then(setTasks), []);
```

## Pattern 4: Centralized Overlays

```tsx
// ✅ DO: useOverlayStore for modals/dialogs
import { useOverlayStore } from '@/stores/useOverlayStore';

export function TaskCard({ task }) {
  const { openModal } = useOverlayStore();
  return <div onClick={() => openModal('editTask', { taskId: task.id })}>{task.title}</div>;
}

// ❌ DON'T: Local modal state
const [isModalOpen, setIsModalOpen] = useState(false);
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
// ✅ DO: React Hook Form + Zod validation
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

// ❌ DON'T: Manual validation
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
/* ✅ DO: CSS transitions for simple animations */
.modal-overlay {
  opacity: 0;
  transition: opacity 0.2s ease-in-out;
}

.modal-overlay[data-state="open"] {
  opacity: 1;
}

/* ❌ DON'T: framer-motion for simple animations */
```

## Pattern 9: Single Layout (AppShell)

```tsx
// ✅ DO: Consistent AppShell wrapper
export function AppShell({ children }) {
  return (
    <div className="min-h-screen bg-ui-bg">
      <Header />
      <main className="container mx-auto px-4 py-8">{children}</main>
    </div>
  );
}

// Usage in pages
export function TasksPage() {
  return <AppShell><TaskList /></AppShell>;
}
```

## Pattern 10: Wrapper Components

```tsx
// ✅ DO: Reusable UI wrappers
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

## Pattern 11: Keyboard Shortcuts

```tsx
// ✅ DO: Use useEffect with proper cleanup and input checks
import { useEffect } from 'react';

export function TaskView() {
  const { focusedTaskId, setFocusedTaskId } = useTaskViewStore();
  
  useEffect(() => {
    const handleKeyDown = (event: KeyboardEvent) => {
      // Check if input/modal is focused
      const activeElement = document.activeElement;
      const isInputFocused = activeElement instanceof HTMLInputElement || 
                             activeElement instanceof HTMLTextAreaElement ||
                             activeElement?.getAttribute('role') === 'dialog';
      
      if (isInputFocused && event.key !== 'Escape') {
        return; // Don't process shortcuts when typing
      }
      
      switch (event.key.toLowerCase()) {
        case 't':
          event.preventDefault();
          setFastInputFocused(true);
          break;
        case 'e':
          if (focusedTaskId) {
            event.preventDefault();
            openDetailModal(focusedTaskId);
          }
          break;
        case 'escape':
          event.preventDefault();
          closeAllModals();
          break;
      }
    };
    
    document.addEventListener('keydown', handleKeyDown);
    return () => document.removeEventListener('keydown', handleKeyDown);
  }, [focusedTaskId, setFocusedTaskId]);
  
  return <div>Task view content...</div>;
}

// ❌ DON'T: Missing cleanup or input checks
useEffect(() => {
  document.addEventListener('keydown', handleKeyDown);
  // Missing cleanup function
}, []);
```

## Pattern 12: Custom UI Hooks

```tsx
// ✅ DO: Extract reusable UI logic into custom hooks
export function useDisclosure(initialOpen = false) {
  const [isOpen, setIsOpen] = useState(initialOpen);
  
  const open = useCallback(() => setIsOpen(true), []);
  const close = useCallback(() => setIsOpen(false), []);
  const toggle = useCallback(() => setIsOpen(prev => !prev), []);
  
  return { isOpen, open, close, toggle };
}

export function useLocalStorage<T>(key: string, initialValue: T) {
  const [storedValue, setStoredValue] = useState<T>(() => {
    try {
      const item = window.localStorage.getItem(key);
      return item ? JSON.parse(item) : initialValue;
    } catch (error) {
      console.warn(`Error reading localStorage key "${key}":`, error);
      return initialValue;
    }
  });

  const setValue = useCallback((value: T | ((val: T) => T)) => {
    try {
      const valueToStore = value instanceof Function ? value(storedValue) : value;
      setStoredValue(valueToStore);
      window.localStorage.setItem(key, JSON.stringify(valueToStore));
    } catch (error) {
      console.warn(`Error setting localStorage key "${key}":`, error);
    }
  }, [key, storedValue]);

  return [storedValue, setValue] as const;
}

// Usage
function TaskSettings() {
  const { isOpen, open, close } = useDisclosure();
  const [viewMode, setViewMode] = useLocalStorage('taskViewMode', 'list');
  
  return (
    <div>
      <Button onClick={open}>Settings</Button>
      <Modal open={isOpen} onOpenChange={close}>
        <select value={viewMode} onChange={(e) => setViewMode(e.target.value)}>
          <option value="list">List</option>
          <option value="grid">Grid</option>
        </select>
      </Modal>
    </div>
  );
}

// ❌ DON'T: Repeat logic across components
function Component1() {
  const [isOpen, setIsOpen] = useState(false);
  const open = () => setIsOpen(true);
  const close = () => setIsOpen(false);
  // Repeated logic...
}
```

## Complete Examples

### Task List Component
```tsx
/**
 * @docs memory-bank/patterns/ui-patterns.md#pattern-3-react-query-hooks
 * @rules memory-bank/rules/ui-rules.json#ui-004,ui-005
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

### Form Component
```tsx
/**
 * @docs memory-bank/patterns/ui-patterns.md#pattern-6-forms-with-zod
 * @rules memory-bank/rules/ui-rules.json#ui-007
 */
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';

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

**Dependencies**:
- `@radix-ui/react-*` - UI primitives
- `@tanstack/react-query` - API state
- `react-hook-form` + `zod` - Forms
- `zustand` - Global state 