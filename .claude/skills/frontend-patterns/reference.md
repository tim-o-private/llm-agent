# Frontend Patterns — Full Reference

## 1. Radix Themes = Provider Only, NOT Components

**This is the most important rule.** Radix Themes provides the `<Theme>` wrapper and CSS variables. Do NOT import pre-styled components from `@radix-ui/themes`.

```tsx
// ✅ Theme provider in main.tsx
import { Theme } from '@radix-ui/themes';
<Theme accentColor="violet" grayColor="slate" appearance={effectiveAppearance}>
  <App />
</Theme>

// ✅ Radix Primitives + Tailwind for components
import * as Dialog from '@radix-ui/react-dialog';
<Dialog.Content className="bg-ui-element-bg rounded-lg p-6">

// ❌ NEVER import pre-styled Radix Themes components
import { Button } from '@radix-ui/themes';  // FORBIDDEN
```

## 2. Semantic Color Tokens — No Hardcoded Colors

All colors come from semantic tokens in `tailwind.config.js`, which map to Radix CSS variables:

```tsx
// ✅ Semantic tokens
<div className="bg-ui-element-bg text-text-primary border-ui-border">
<button className="bg-brand-primary text-white">

// ❌ FORBIDDEN — Tailwind defaults
<div className="bg-blue-500 text-gray-900 border-red-400">

// ❌ FORBIDDEN — Inline colors
<div style={{ backgroundColor: '#3b82f6' }}>
```

**Common token names — use these, not invented ones:**

| Purpose | Token | Resolves to |
|---|---|---|
| Panel/dropdown background | `bg-ui-element-bg` | `var(--color-panel-solid)` |
| Subtle highlight (unread) | `bg-ui-bg-alt` | `var(--gray-2)` |
| Hover state | `bg-ui-interactive-bg` | `var(--gray-3)` |
| Standard border | `border-ui-border` | `var(--gray-6)` |
| Dividers | `divide-ui-border` | `var(--gray-6)` |
| Primary text | `text-text-primary` | `var(--gray-12)` |
| Secondary text (legible) | `text-text-secondary` | `var(--gray-11)` |
| Muted text (low contrast) | `text-text-muted` | `var(--gray-9)` — avoid in dark mode panels |

**Warning:** Do NOT invent token names like `bg-surface-primary`, `border-border-primary`, etc. Tailwind silently ignores unknown tokens and generates no CSS. Always verify token names against `tailwind.config.js`.

**`text-text-muted` vs `text-text-secondary`:** Use `text-text-secondary` (`--gray-11`) for body text in dropdowns and panels. `text-text-muted` (`--gray-9`) has insufficient contrast on dark backgrounds. Reserve `text-text-muted` for disabled/placeholder states on light surfaces only.

For CSS files, use raw Radix variables:
```css
.my-component {
  background-color: var(--gray-3);
  color: var(--gray-12);
  border: 1px solid var(--accent-9);
}
```

## 3. React Query for All API State

```tsx
import { useTaskHooks } from '@/api/hooks/useTaskHooks';

export function TaskList() {
  const { data: tasks, isLoading, error } = useTaskHooks.useFetchTasks();

  if (isLoading) return <LoadingSpinner />;
  if (error) return <ErrorMessage error={error} />;

  return (
    <div className="space-y-4">
      {tasks.map(task => <TaskCard key={task.id} task={task} />)}
    </div>
  );
}
```

**Never use `useState` + `useEffect` for API calls. Never call Supabase directly from components.**

## 4. Auth Tokens — Always From Supabase Client

```tsx
// ✅ Get token from Supabase client
import { supabase } from '@/lib/supabaseClient';

async function getAuthHeaders(): Promise<HeadersInit> {
  const { data: { session } } = await supabase.auth.getSession();
  if (!session?.access_token) throw new Error('Not authenticated');
  return {
    'Content-Type': 'application/json',
    Authorization: `Bearer ${session.access_token}`,
  };
}

// ❌ NEVER get token from Zustand (may be stale/null on startup)
const token = useAuthStore.getState().session?.access_token;
```

## 5. Centralized Overlays via Zustand

```tsx
// ✅ useOverlayStore for modals/dialogs
import { useOverlayStore } from '@/stores/useOverlayStore';

export function TaskCard({ task }) {
  const { openModal } = useOverlayStore();
  return (
    <div onClick={() => openModal('editTask', { taskId: task.id })}>
      {task.title}
    </div>
  );
}

// ❌ Don't use local useState for modal visibility
const [isModalOpen, setIsModalOpen] = useState(false);
```

## 6. Error and Loading States

Every data-fetching component must handle loading and error:

```tsx
const { mutate: updateTask, isPending } = useTaskHooks.useUpdateTask();

<Button disabled={isPending}>
  {isPending ? <LoadingSpinner size="sm" /> : 'Save'}
</Button>
```

## 7. Forms with React Hook Form + Zod

```tsx
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
```

**Never use manual `useState` + `onChange` for forms. Always validate with Zod.**

## 8. Accessibility (WCAG 2.1 AA)

```tsx
// ✅ ARIA labels, keyboard support, focus indicators
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

// ❌ No accessibility
<div onClick={onEdit}>{task.title}</div>
```

All interactive elements need: keyboard support, focus indicators, ARIA labels, semantic HTML.

## 9. Keyboard Shortcuts

```tsx
useEffect(() => {
  const handleKeyDown = (event: KeyboardEvent) => {
    const active = document.activeElement;
    const isInputFocused =
      active instanceof HTMLInputElement ||
      active instanceof HTMLTextAreaElement ||
      active?.getAttribute('role') === 'dialog';

    if (isInputFocused && event.key !== 'Escape') return;

    switch (event.key.toLowerCase()) {
      case 't': event.preventDefault(); setFastInputFocused(true); break;
      case 'escape': event.preventDefault(); closeAllModals(); break;
    }
  };

  document.addEventListener('keydown', handleKeyDown);
  return () => document.removeEventListener('keydown', handleKeyDown);
}, [dependencies]);
```

**Always check if input is focused. Always clean up event listeners.**

## 10. Animations — CSS First

```css
/* ✅ CSS transitions */
.modal-overlay {
  opacity: 0;
  transition: opacity 0.2s ease-in-out;
}
.modal-overlay[data-state="open"] { opacity: 1; }
```

**Use CSS transitions for simple animations. Use framer-motion sparingly for complex needs only.**

## 11. Wrapper Components

```tsx
// ✅ Reusable wrappers in components/ui/
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
```

## 12. Path Aliases

```tsx
// ✅ Use aliases
import { supabase } from '@/lib/supabaseClient';
import { Card } from '@components/ui/Card';

// ❌ Relative paths
import { supabase } from '../../../lib/supabaseClient';
```

`@/` → `src/`, `@components/` → `src/components/`

## 13. Component and Hook Testing

Test components with `@testing-library/react` and user interactions with `@testing-library/user-event`:

```tsx
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { NotificationBadge } from './NotificationBadge';

// Wrap with providers
function renderWithProviders(ui: React.ReactElement) {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return render(
    <QueryClientProvider client={queryClient}>{ui}</QueryClientProvider>
  );
}

test('shows unread count badge when count > 0', async () => {
  // Mock the API response
  vi.spyOn(global, 'fetch').mockResolvedValueOnce({
    ok: true,
    json: () => Promise.resolve({ count: 3 }),
  } as Response);

  renderWithProviders(<NotificationBadge />);
  await waitFor(() => {
    expect(screen.getByText('3')).toBeInTheDocument();
  });
});

test('opens dropdown on click', async () => {
  const user = userEvent.setup();
  renderWithProviders(<NotificationBadge />);

  await user.click(screen.getByRole('button', { name: /notifications/i }));
  expect(screen.getByText('Notifications')).toBeInTheDocument();
});
```

Test hooks with `msw` (Mock Service Worker) for API mocking:

```tsx
import { renderHook, waitFor } from '@testing-library/react';
import { useNotifications } from './useNotificationHooks';

test('fetches notifications when user is authenticated', async () => {
  // Setup msw handler for /api/notifications
  const { result } = renderHook(() => useNotifications(), { wrapper });
  await waitFor(() => expect(result.current.isSuccess).toBe(true));
  expect(result.current.data).toHaveLength(2);
});
```

**Test file naming:** Place test files alongside the component: `NotificationBadge.test.tsx` next to `NotificationBadge.tsx`.
