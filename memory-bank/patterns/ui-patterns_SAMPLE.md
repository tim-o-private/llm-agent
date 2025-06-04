# UI Implementation Patterns

> **Purpose**: All frontend implementation patterns for the `webApp/` directory. Follow these patterns to ensure consistency and prevent reinventing existing solutions.

## Pattern 1: Component Architecture

### Radix UI Primitives + Tailwind CSS
**Use**: Radix UI primitives for behavior, Tailwind CSS for styling
**Avoid**: Headless UI, `@radix-ui/themes` components, `@radix-ui/colors`

```tsx
// ✅ CORRECT - Radix primitive with Tailwind styling
import * as Dialog from '@radix-ui/react-dialog';

export function Modal({ children, ...props }) {
  return (
    <Dialog.Root {...props}>
      <Dialog.Portal>
        <Dialog.Overlay className="fixed inset-0 bg-black/50" />
        <Dialog.Content className="fixed top-1/2 left-1/2 transform -translate-x-1/2 -translate-y-1/2 bg-white rounded-lg p-6">
          {children}
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  );
}

// ❌ AVOID - Direct @radix-ui/themes usage
import { Button } from '@radix-ui/themes';
```

### Component Organization
```
webApp/src/components/
├── ui/                    # Shared, reusable components
│   ├── Button.tsx
│   ├── Modal.tsx
│   └── ErrorMessage.tsx
├── features/              # Feature-specific components
│   ├── tasks/
│   ├── chat/
│   └── auth/
└── layouts/               # Layout components
    └── AppShell.tsx
```

## Pattern 2: State Management

### Centralized Overlay Management
**Use**: `useOverlayStore` for modals, trays, and overlays
**Location**: `webApp/src/stores/useOverlayStore.ts`

```tsx
// ✅ CORRECT - Centralized overlay state
import { useOverlayStore } from '@/stores/useOverlayStore';

export function TaskCard({ task }) {
  const { openModal } = useOverlayStore();
  
  const handleEdit = () => {
    openModal('editTask', { taskId: task.id });
  };
  
  return (
    <div onClick={handleEdit}>
      {task.title}
    </div>
  );
}

// ❌ AVOID - Local modal state
const [isModalOpen, setIsModalOpen] = useState(false);
```

### React Query for API State
**Use**: Custom hooks in `webApp/src/api/hooks/`
**Pattern**: Encapsulate all Supabase interactions

```tsx
// ✅ CORRECT - Custom React Query hook
import { useTaskHooks } from '@/api/hooks/useTaskHooks';

export function TaskList() {
  const { data: tasks, isLoading, error } = useTaskHooks.useFetchTasks();
  
  if (isLoading) return <LoadingSpinner />;
  if (error) return <ErrorMessage error={error} />;
  
  return (
    <div>
      {tasks.map(task => <TaskCard key={task.id} task={task} />)}
    </div>
  );
}

// ❌ AVOID - Direct Supabase calls in components
const [tasks, setTasks] = useState([]);
useEffect(() => {
  supabase.from('tasks').select('*').then(setTasks);
}, []);
```

## Pattern 3: Styling and Theming

### Semantic Color Tokens Only
**Use**: Semantic tokens from `tailwind.config.js`
**Avoid**: Hardcoded colors, Tailwind default colors

```tsx
// ✅ CORRECT - Semantic color tokens
<div className="bg-ui-element-bg text-text-primary border-ui-border">
  <Button className="bg-brand-primary text-white">Save</Button>
</div>

// ❌ FORBIDDEN - Hardcoded or default Tailwind colors
<div className="bg-blue-500 text-white border-gray-300">
<div className="bg-gray-100 text-gray-900">
```

### Wrapper Components for Common Patterns
**Use**: Reusable wrapper components for repeated Tailwind combinations

```tsx
// ✅ CORRECT - Wrapper component
export function Card({ children, className = '', ...props }) {
  return (
    <div 
      className={`bg-ui-element-bg border border-ui-border rounded-lg p-4 ${className}`}
      {...props}
    >
      {children}
    </div>
  );
}

// Usage
<Card className="shadow-lg">
  <h2>Task Details</h2>
</Card>
```

## Pattern 4: Error and Loading States

### Consistent Error Display
**Use**: Standardized `ErrorMessage` component
**Location**: `webApp/src/components/ui/ErrorMessage.tsx`

```tsx
// ✅ CORRECT - Consistent error handling
import { ErrorMessage } from '@/components/ui/ErrorMessage';

export function TaskList() {
  const { data, isLoading, error } = useTaskHooks.useFetchTasks();
  
  if (error) return <ErrorMessage error={error} />;
  if (isLoading) return <LoadingSpinner />;
  
  return <div>{/* content */}</div>;
}
```

### Loading State Management
**Use**: React Query loading states + UI feedback

```tsx
// ✅ CORRECT - Comprehensive loading states
export function TaskForm({ taskId }) {
  const { mutate: updateTask, isPending } = useTaskHooks.useUpdateTask();
  
  return (
    <form onSubmit={handleSubmit}>
      <Button 
        type="submit" 
        disabled={isPending}
        className={isPending ? 'opacity-50 cursor-not-allowed' : ''}
      >
        {isPending ? <LoadingSpinner size="sm" /> : 'Save'}
      </Button>
    </form>
  );
}
```

## Pattern 5: Form Management

### React Hook Form + Zod Validation
**Use**: Structured form handling with validation

```tsx
// ✅ CORRECT - React Hook Form with Zod
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';

const taskSchema = z.object({
  title: z.string().min(1, 'Title is required'),
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
```

## Pattern 6: Accessibility

### WCAG 2.1 AA Compliance
**Requirements**: Semantic HTML, ARIA attributes, keyboard navigation

```tsx
// ✅ CORRECT - Accessible component
export function TaskCard({ task, onEdit }) {
  return (
    <article 
      className="focus:outline-none focus:ring-2 focus:ring-brand-primary"
      tabIndex={0}
      role="button"
      aria-label={`Edit task: ${task.title}`}
      onKeyDown={(e) => e.key === 'Enter' && onEdit()}
      onClick={onEdit}
    >
      <h3>{task.title}</h3>
      <p>{task.description}</p>
    </article>
  );
}
```

### Focus Management
**Use**: Visible focus indicators, logical tab order

```css
/* ✅ CORRECT - Visible focus indicators */
.focus-visible:focus {
  outline: 2px solid var(--accent-9);
  outline-offset: 2px;
}

/* Skip links for screen readers */
.skip-link {
  position: absolute;
  top: -40px;
  left: 6px;
  background: var(--accent-9);
  color: white;
  padding: 8px;
  text-decoration: none;
  transition: top 0.3s;
}

.skip-link:focus {
  top: 6px;
}
```

## Pattern 7: Animation Strategy

### CSS-First Approach
**Use**: CSS transitions for simple animations
**Avoid**: `framer-motion` unless CSS is insufficient

```css
/* ✅ CORRECT - CSS transitions */
.modal-overlay {
  opacity: 0;
  transition: opacity 0.2s ease-in-out;
}

.modal-overlay[data-state="open"] {
  opacity: 1;
}

.card {
  transform: translateY(0);
  transition: transform 0.2s ease-in-out;
}

.card:hover {
  transform: translateY(-2px);
}
```

## Pattern 8: Application Layout

### Single Layout Component
**Use**: Consolidated `AppShell.tsx` for main layout
**Location**: `webApp/src/layouts/AppShell.tsx`

```tsx
// ✅ CORRECT - Single layout component
export function AppShell({ children }) {
  return (
    <div className="min-h-screen bg-ui-bg">
      <Header />
      <main className="container mx-auto px-4 py-8">
        {children}
      </main>
      <Footer />
    </div>
  );
}

// Usage in pages
export function TasksPage() {
  return (
    <AppShell>
      <TaskList />
    </AppShell>
  );
}
```

## Anti-Patterns (What NOT to Do)

### ❌ Don't Reinvent Existing Components
```tsx
// ❌ WRONG - Creating new modal when one exists
export function MyCustomModal() {
  // Custom modal implementation
}

// ✅ CORRECT - Use existing Modal component
import { Modal } from '@/components/ui/Modal';
```

### ❌ Don't Use Hardcoded Colors
```tsx
// ❌ WRONG - Hardcoded colors
<div style={{ backgroundColor: '#3b82f6' }}>
<div className="bg-blue-500">

// ✅ CORRECT - Semantic tokens
<div className="bg-brand-primary">
```

### ❌ Don't Skip Error Handling
```tsx
// ❌ WRONG - No error handling
const { data } = useQuery('tasks', fetchTasks);

// ✅ CORRECT - Proper error handling
const { data, error, isLoading } = useQuery('tasks', fetchTasks);
if (error) return <ErrorMessage error={error} />;
```

## Quick Reference

### File Locations
- **Shared Components**: `webApp/src/components/ui/`
- **Feature Components**: `webApp/src/components/features/`
- **Custom Hooks**: `webApp/src/hooks/`
- **API Hooks**: `webApp/src/api/hooks/`
- **Stores**: `webApp/src/stores/`
- **Types**: `webApp/src/api/types.ts`

### Import Aliases
- `@/components/ui/` - Shared UI components
- `@/hooks/` - Custom React hooks
- `@/api/hooks/` - React Query hooks
- `@/stores/` - Zustand stores
- `@/api/types` - TypeScript types

### Key Dependencies
- **UI Primitives**: `@radix-ui/react-*`
- **Styling**: `tailwindcss`
- **State Management**: `zustand`, `@tanstack/react-query`
- **Forms**: `react-hook-form`, `zod`
- **Icons**: `@radix-ui/react-icons` 