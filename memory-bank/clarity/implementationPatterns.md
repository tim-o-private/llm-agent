This document outlines key architectural patterns and strategies for implementing UI components and interacting with the API. Follow these guidelines to ensure consistency, maintainability, and conciseness in the codebase, aligning with our project goals.

---

## Pattern 1: Centralized Overlay State Management

**Goal:** Manage the state of modals, trays, and other overlays consistently and centrally.

*   **DO:** Use the `useOverlayStore` Zustand store to control which overlay is open and pass data to it.
*   **DO:** Create a single `OverlayManager` component that reads the `useOverlayStore` state and renders the correct overlay component.
*   **DO:** Have overlay components read their visibility state and initial data from props passed down by the `OverlayManager`.
*   **DO:** Have overlay components call `useOverlayStore.getState().closeOverlay()` when they need to close themselves (e.g., on button click, escape key).
*   **DON'T:** Manage individual `isOpen` state variables (e.g., `useState(false)`) for modals/trays within components or pages.
*   **DON'T:** Pass `setIsOpen` functions or similar state setters down through multiple component levels (avoid prop drilling for overlay state).

**Example (Illustrative):**

```typescript
// DON'T DO THIS in a page component (TodayView.tsx)
const [isQuickAddTrayOpen, setIsQuickAddTrayOpen] = useState(false);
const [isTaskDetailTrayOpen, setIsTaskDetailTrayOpen] = useState(false);
// ... more state for data and handlers ...

// DO THIS in a component that triggers an overlay
import { useOverlayStore } from '@/stores/useOverlayStore';

// To open Quick Add Tray
useOverlayStore.getState().openOverlay('quickAddTray');

// To open Task Detail Tray with data
useOverlayStore.getState().openOverlay('taskDetailTray', { taskId: task.id });

// DO THIS in the OverlayManager component
import { useOverlayStore } from '@/stores/useOverlayStore';
import QuickAddTray from '@/components/overlays/QuickAddTray';
import TaskDetailTray from '@/components/overlays/TaskDetailTray';

function OverlayManager() {
  const { activeOverlay } = useOverlayStore();

  if (!activeOverlay) return null;

  switch (activeOverlay.type) {
    case 'quickAddTray':
      return <QuickAddTray isOpen={true} onClose={useOverlayStore.getState().closeOverlay} />;
    case 'taskDetailTray':
      return <TaskDetailTray isOpen={true} initialData={activeOverlay.data} onClose={useOverlayStore.getState().closeOverlay} />;
    default:
      return null;
  }
}

// DO THIS in an overlay component (QuickAddTray.tsx)
function QuickAddTray({ isOpen, onClose }) { // Receive state via props
  // ... implementation ...
  return (
    <Dialog open={isOpen} onClose={onClose}> {/* Use isOpen and onClose props */}
      {/* ... content ... */}
      <button onClick={onClose}>Close</button> {/* Call onClose prop */}
    </Dialog>
  );
}
```

---

## Pattern 2: UI Component Strategy: Radix UI Primitives + Tailwind CSS

**Goal:** Use Radix UI Primitives for accessible component behavior and Tailwind CSS for all styling.

*   **DO:** Use components from `@radix-ui/react-*` (Radix UI Primitives) for accessible, unstyled UI behaviors (Dialogs, Dropdowns, Checkboxes, Sliders, etc.).
*   **DO:** Use the built-in properties provided by Radix UI Primitives (e.g., `open`, `onOpenChange`, `value`, `onValueChange`) to control component behavior.
*   **DO:** Apply styling to Radix Primitives using Tailwind CSS utility classes, potentially encapsulated within wrapper components (see Pattern 6).
*   **DO:** Create wrapper components in `components/ui/` around Radix Primitives to encapsulate common styling patterns and provide a consistent API within our project.
*   **DON'T:** Use components for the same purpose from `@headlessui/react`.
*   **DON'T:** Use the `@radix-ui/themes` library, as it provides pre-styled components that conflict with our Tailwind styling strategy.
*   **DON'T:** Rely on `@radix-ui/colors` library for color definitions; use Tailwind's color system instead.

**Example (Illustrative):**

```typescript
// DON'T DO THIS (using Headless UI component)
import { Dialog } from '@headlessui/react';
// ...

// DON'T DO THIS (using Radix Themes component)
import { Button } from '@radix-ui/themes';
// ...

// DO THIS (using Radix UI Primitive + Tailwind Styling, potentially via Pattern 6)
import * as Dialog from '@radix-ui/react-dialog';
import { useState } from 'react'; // Example state, or use Pattern 1
import clsx from 'clsx'; // Recommended for conditional classes

// Example using direct Tailwind classes (or encapsulated in Pattern 6 component)
function MyStyledModal({ children, open, onOpenChange }) { // Receive Radix props
  return (
    <Dialog.Root open={open} onOpenChange={onOpenChange}> {/* Use Radix properties */}
      <Dialog.Portal>        {/* Apply Tailwind classes directly or via Pattern 6 wrapper */}
        <Dialog.Overlay className={clsx("fixed inset-0 bg-black", open ? "opacity-50" : "opacity-0", "transition-opacity")} />
        <Dialog.Content className="fixed top-1/2 left-1/2 transform -translate-x-1/2 -translate-y-1/2 bg-white p-6 rounded shadow-lg"> {/* Apply Tailwind classes */}
          {children}
          <Dialog.Close asChild>
            <button className="absolute top-2 right-2 text-gray-500 hover:text-gray-700">X</button> {/* Apply Tailwind classes */}
          </Dialog.Close>
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  );
}

// Usage in another component:
function MyComponent() {
  const [isOpen, setIsOpen] = useState(false); // Or use Overlay Store (Pattern 1)

  return (
    <>
      <button onClick={() => setIsOpen(true)}>Open Modal</button>
      <MyStyledModal open={isOpen} onOpenChange={setIsOpen}> {/* Use Radix property */}
        <div>Modal Content</div>
      </MyStyledModal>
    </>
  );
}
```

---

## Pattern 3: Re-evaluated Animation Strategy

**Goal:** Use animations deliberately and efficiently, favoring simplicity.

*   **DO:** Use standard CSS transitions or keyframe animations for simple visual feedback (fades, slides, hover effects) where possible. Define these using Tailwind utilities or standard CSS, potentially within wrapper components (Pattern 6).
*   **DO:** Ensure any implemented animations align with the "low-stim" and "minimal cognitive load" design principles.
*   **DON'T:** Add or retain `framer-motion` for animations that can be achieved simply and efficiently with CSS.
*   **DON'T:** Implement complex, distracting, or unnecessary animations.

---

## Pattern 4: Consolidated Application Layout

**Goal:** Have a single, clear component defining the main application structure.

*   **DO:** Use only one component (e.g., `webApp/src/layouts/AppShell.tsx`) for the main application shell (sidebar, content area, etc.).
*   **DO:** Ensure all routes requiring the main layout use this single component.
*   **DON'T:** Maintain multiple layout files that serve the same purpose of defining the main page structure. Delete redundant layout files.

---

## Pattern 5: Centralized API Interaction with React Query

**Goal:** Manage data fetching and mutations consistently using React Query, encapsulating API logic.

*   **DO:** Use `@tanstack/react-query` for all data fetching, caching, and mutations interacting with Supabase or the `chatServer/` API.
*   **DO:** Create custom React Query hooks (e.g., `useTasks`, `useCreateTask`) in a dedicated directory (e.g., `@/api/hooks/`) to encapsulate Supabase calls (`supabase.from(...)...`) or calls to `chatServer/` endpoints.
*   **DO:** Implement `onSuccess` handlers in mutation hooks to invalidate relevant queries using `queryClient.invalidateQueries()` to ensure UI freshness.
*   **DO:** Have components call only these custom React Query hooks to fetch or mutate data.
*   **DON'T:** Make direct calls to the raw `supabase` client (`supabase.from(...)...`) or `fetch` calls to `chatServer/` within UI components, pages, or other parts of the application outside of the dedicated API hooks/service functions.
*   **DON'T:** Implement manual `isLoading`, `error`, or data state management for API calls within components; rely on React Query's hook return values for this.

**Example (Illustrative):**

```typescript
// DON'T DO THIS in a component or page
import { supabase } from '@/lib/supabaseClient';

const [tasks, setTasks] = useState([]);
const [isLoading, setIsLoading] = useState(true);
const [error, setError] = useState(null);

useEffect(() => {
  async function fetchTasks() {
    setIsLoading(true);
    const { data, error } = await supabase.from('tasks').select('*');
    if (error) setError(error);
    else setTasks(data);
    setIsLoading(false);
  }
  fetchTasks();
}, []);

// ... manual error/loading handling in JSX ...

// DO THIS by creating a custom hook in @/api/hooks/useTaskHooks.ts
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { supabase } from '@/lib/supabaseClient';

export function useTasks() {
  return useQuery({
    queryKey: ['tasks'],
    queryFn: async () => {
      const { data, error } = await supabase.from('tasks').select('*');
      if (error) throw error; // React Query expects errors to be thrown
      return data;
    },
  });
}

export function useCreateTask() {
   const queryClient = useQueryClient();
   return useMutation({
     mutationFn: async (newTaskData) => {
       const { data, error } = await supabase.from('tasks').insert([newTaskData]).select().single();
       if (error) throw error;
       return data;     },
     onSuccess: () => {
        // Automatically refetch the tasks list after creating one
        queryClient.invalidateQueries(['tasks']);
     }
   });
}

// DO THIS in a component or page
import { useTasks, useCreateTask } from '@/api/hooks/useTaskHooks';

function TaskList() {
  const { data: tasks, isLoading, error } = useTasks();

  if (isLoading) return <div>Loading tasks...</div>;
  if (error) return <div>Error loading tasks: {error.message}</div>;

  // ... render tasks ...
}

function CreateTaskButton() {
  const createMutation = useCreateTask();

  const handleClick = async () => {
     try {
       await createMutation.mutateAsync({ name: 'New Task' });
       // Task list will auto-update due to onSuccess invalidation
     } catch (error) {
       // Handle mutation error
     }  };

  return <button onClick={handleClick} disabled={createMutation.isLoading}>Add Task</button>;
}
```

---

## Pattern 6: Encapsulating Styling Patterns with Wrapper Components

**Goal:** Make common combinations of Tailwind utility classes recognizable and reusable by encapsulating them within dedicated React components. This addresses the difficulty in identifying repeated style patterns when utilities are applied directly.

*   **DO:** When you notice the same set of Tailwind utility classes being repeated across different parts of the application (e.g., for a card, a section header, a form input wrapper, a panel container), create a new, small React component (e.g., `PanelContainer`, `Card`, `SectionHeader`, `InputWrapper`).
*   **DO:** Apply the repeated set of utility classes to the appropriate element *inside* this new wrapper component's JSX.
*   **DO:** Use the new wrapper component throughout the application instead of repeating the raw utility classes. Pass `children` or specific props to make the wrapper flexible.
*   **DO:** Consider using the `clsx` (or similar) library within these wrapper components if you need to conditionally apply utility classes based on props (e.g., `<Button variant="primary" />` applies different classes).
*   **DON'T:** Repeat the exact same long string of Tailwind utility classes in the `className` prop of multiple different components or elements if that combination represents a logical UI pattern.
*   **DON'T:** Create wrapper components for every single `div` or element; focus on encapsulating *meaningful, repeated* combinations of styles.

**Example (Illustrative):**

```typescript
// DON'T DO THIS (Repeating classes in multiple places)
function ComponentA() {
  return (
    <div className="flex flex-col h-full bg-white dark:bg-gray-800 shadow-lg border-l border-gray-200 dark:border-gray-700">      {/* ... content ... */}
    </div>
  );
}

function ComponentB() {
  return (
    <aside className="flex flex-col h-full bg-white dark:bg-gray-800 shadow-lg border-l border-gray-200 dark:border-gray-700">      {/* ... other content ... */}
    </aside>
  );
}

// DO THIS (Create a wrapper component)
// web/apps/web/src/components/ui/PanelContainer.tsx
import { HTMLAttributes } from 'react';
import clsx from 'clsx'; // Optional, but useful

interface PanelContainerProps extends HTMLAttributes<HTMLDivElement | HTMLElement> {
  // Define props for variations if needed
  as?: 'div' | 'aside' | 'section'; // Allow rendering as different semantic elements
  className?: string; // Allow overriding/adding classes
}

function PanelContainer({ as: Comp = 'div', className, children, ...props }: PanelContainerProps) {
  const baseClasses = "flex flex-col h-full bg-white dark:bg-gray-800 shadow-lg border-l border-gray-200 dark:border-gray-700";
  return (
    <Comp className={clsx(baseClasses, className)} {...props}>
      {children}
    </Comp>
  );
}

// Usage in other components
function ComponentA() {
  return (
    <PanelContainer> {/* Use the wrapper */}
      {/* ... content ... */}
    </PanelContainer>
  );
}

function ComponentB() {
  return (
    <PanelContainer as="aside"> {/* Use the wrapper, specify element */}
      {/* ... other content ... */}
    </PanelContainer>
  );
}
```

---

## Pattern 7: Consistent Error Display

**Goal:** Show errors to the user in a clear, consistent, and predictable way.

*   **DO:** Display clear, user-friendly error messages that explain what went wrong in simple terms.
*   **DO:** Show validation errors directly next to the form field they relate to.
*   **DO:** Show general application errors (e.g., failed API calls not tied to a specific form) in a prominent global area like a banner or notification system.
*   **DO:** Use dedicated, reusable UI components for displaying error messages (e.g., `<ErrorMessage text="Invalid input" />`).
*   **DO:** Log technical error details to the console or a monitoring service for debugging, but avoid showing these to the user.
*   **DON'T:** Show raw backend error messages or technical stack traces to the user.
*   **DON'T:** Hide errors or fail silently when something goes wrong from the user's perspective.
*   **DON'T:** Use inconsistent methods for displaying errors across the application.

**Example (Illustrative):**

```typescript
// web/apps/web/src/components/ui/ErrorMessage.tsx
import clsx from 'clsx';

interface ErrorMessageProps {
  text?: string | null;
  className?: string;
}

function ErrorMessage({ text, className }: ErrorMessageProps) {
  if (!text) return null;  return (
    <p className={clsx("text-red-500 text-sm mt-1", className)}> {/* Apply styling */}
      {text}
    </p>
  );
}

// Usage in a form component
function MyForm() {
  const [emailError, setEmailError] = useState<string | null>(null);
  // ... form state and validation logic ...

  const handleSubmit = () => {
    if (!isValidEmail(email)) {
      setEmailError("Please enter a valid email address.");
      return;
    }
    // ... submit logic ...
  };

  return (
    <form onSubmit={handleSubmit}>
      <div>
        <label htmlFor="email">Email:</label>
        <input
          id="email"
          type="email"
          // ... input props ...
        />
        <ErrorMessage text={emailError} /> {/* Display error below input */}
      </div>
      {/* ... other fields ... */}
      {/* For a general form submission error not tied to a field: */}
      {/* <ErrorMessage text={generalFormError} className="mb-4" /> */}
      <button type="submit">Submit</button>
    </form>
  );
}
```

---

## Pattern 8: Consistent Loading Indication

**Goal:** Inform the user clearly when content is loading or an action is in progress.

*   **DO:** Use visual indicators for loading states, such as spinners, skeleton loaders, or progress bars.
*   **DO:** Disable interactive elements (buttons, inputs) while an action is in progress to prevent duplicate submissions and indicate status.
*   **DO:** Show loading states for both initial data fetches (e.g., loading a page) and user-initiated actions (e.g., clicking a save button).
*   **DO:** Leverage the `isLoading` status provided by React Query hooks (Pattern 5) to manage loading states automatically.
*   **DON'T:** Leave the user uncertain about whether an action is processing or if content is still loading.
*   **DON'T:** Block the entire UI with a modal spinner unless the application is truly unusable during the loading period.
*   **DON'T:** Use inconsistent loading indicators across different parts of the application.

**Example (Illustrative):**

```typescript
// Using React Query's isLoading
import { useTasks, useCreateTask } from '@/api/hooks/useTaskHooks'; // Pattern 5

function TaskList() {
  const { data: tasks, isLoading, error } = useTasks();

  if (isLoading) {
    return <div>Loading tasks... <Spinner /></div>; {/* Use a Spinner component */}
    // Or return <TaskSkeletonList />; // Use a skeleton loader
  }

  if (error) {
    return <ErrorMessage text="Failed to load tasks." />; // Pattern 7
  }

  // ... render task list ...
}

function CreateTaskButton() {
  const createMutation = useCreateTask();

  const handleClick = async () => {
     // ... get task data ...
     createMutation.mutate(newTaskData); // Trigger mutation
  };

  return (
    <button onClick={handleClick} disabled={createMutation.isLoading}> {/* Disable while loading */}
      {createMutation.isLoading ? 'Adding...' : 'Add Task'} {/* Update button text */}
    </button>
  );
}
```

---

## Pattern 9: Form Management

**Goal:** Handle forms, validation, and submission logic in a structured and maintainable way.

*   **DO:** Use a dedicated form management library (e.g., React Hook Form, Formik) for handling complex form state, validation, submission, and error handling. React Hook Form is recommended for its performance and developer experience.
*   **DO:** Define your form schemas and validation rules clearly, preferably using a schema validation library like Zod or Yup alongside your form library.
*   **DO:** Separate the form UI components from the form handling logic. Create reusable input components that can be easily integrated with the chosen form library.
*   **DON'T:** Manage complex multi-input form state and validation manually using many `useState` hooks within a component.
*   **DON'T:** Put complex form submission logic directly inside the component's event handlers without abstracting it.

**Example (Illustrative - using React Hook Form concept):**

```typescript
// DON'T DO THIS (Manual form state/validation for a complex form)
function ComplexFormManual() {
  const [name, setName] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [nameError, setNameError] = useState(null);
  const [emailError, setEmailError] = useState(null);
  // ... more state and validation logic ...
  const handleSubmit = () => { /* ... manual validation and submission ... */ };
  return ( /* ... inputs and errors ... */ );
}

// DO THIS (Using a form library like React Hook Form)
import { useForm } from 'react-hook-form';
import { z } from 'zod'; // Example validation library
import { zodResolver } from '@hookform/resolvers/zod'; // Resolver for RHF

// Define schema for validation
const signUpSchema = z.object({
  name: z.string().min(1, "Name is required"),
  email: z.string().email("Invalid email address"),
  password: z.string().min(8, "Password must be at least 8 characters"),
});

function SignUpForm() {
  const { register, handleSubmit, formState: { errors } } = useForm({
    resolver: zodResolver(signUpSchema), // Integrate validation schema
  });

  const onSubmit = (data) => {
    console.log(data); // Form data is collected and validated
    // ... call API mutation hook (Pattern 5) to submit data ...
  };

  return (
    <form onSubmit={handleSubmit(onSubmit)}> {/* Use handleSubmit from RHF */}
      <div>
        <label htmlFor="name">Name:</label>
        <input id="name" {...register("name")} /> {/* Register input with RHF */}
        <ErrorMessage text={errors.name?.message} /> {/* Display RHF validation error (Pattern 7) */}
      </div>
      <div>
        <label htmlFor="email">Email:</label>
        <input id="email" type="email" {...register("email")} />
        <ErrorMessage text={errors.email?.message} />
      </div>
      <div>
        <label htmlFor="password">Password:</label>
        <input id="password" type="password" {...register("password")} />
        <ErrorMessage text={errors.password?.message} />
      </div>
      <button type="submit">Sign Up</button>
    </form>
  );
}
```

---

## Pattern 10: Accessibility Best Practices

**Goal:** Build a UI that is usable and accessible to people with disabilities.

*   **DO:** Use semantic HTML elements (`<button>`, `<nav>`, `<aside>`, `<header>`, `<footer>`, `<main>`, `<article>`, `<section>`, etc.) appropriately to convey meaning and structure.
*   **DO:** Provide meaningful `alt` text for all `<img>` elements that convey information. If an image is purely decorative, use `alt=""`.
*   **DO:** Ensure sufficient color contrast between text and background colors. Use tools to check contrast ratios.
*   **DO:** Ensure all interactive elements are keyboard navigable and have clear focus indicators. Radix UI Primitives (Pattern 2) handle much of this automatically.
*   **DO:** Use ARIA attributes (`aria-label`, `aria-labelledby`, `aria-describedby`, `role`, etc.) when semantic HTML alone is not sufficient to convey meaning or structure to assistive technologies. Radix UI Primitives handle many standard ARIA roles and states.
*   **DO:** Test the UI using keyboard navigation alone.
*   **DO:** Test the UI with a screen reader (e.g., VoiceOver on Mac, NVDA on Windows, TalkBack on Android) to understand how it is announced.
*   **DON'T:** Use non-semantic elements (`<div>`, `<span>`) for interactive controls like buttons or links without adding appropriate ARIA roles and keyboard handlers.
*   **DON'T:** Rely solely on visual cues (like color) to convey information (e.g., using only red text to indicate an error without an icon or text description).
*   **DON'T:** Remove or obscure focus outlines.

**Example (Illustrative):**

```html
{# DON'T DO THIS (Non-semantic button) #}
<div onclick="doSomething()">Click Me</div>

{# DO THIS (Semantic button) #}
<button onclick="doSomething()">Click Me</button>

{# DO THIS (Image with alt text) #}
<img src="/chart.png" alt="Bar chart showing sales increasing over the last quarter">

{# DO THIS (Decorative image) #}
<img src="/icon-arrow.png" alt="">

{# DO THIS (Link with clear text) #}
<a href="/learn-more">Learn More about Feature X</a>

{# DON'T DO THIS (Ambiguous link text) #}
<a href="/learn-more">Learn More</a> {/* If multiple "Learn More" links on page */}
```

---

## Pattern 11: Standardized DDL & Row Level Security (RLS) for Data Access

**Goal:** Ensure consistent, coherent, secure and maintainable DDL through centralized `ddl.sql` file & Row Level Security (RLS) for user data in Supabase, ensuring users to access and modify only their own records.

*   **DO:** Ensure `memory-bank/clarity/DDL.sql` is kept up to date when changes are made to the DDL.
*   **DO:** Ensure all tables with a user_id column implement appropriate RLS.
*   **DO:** Implement a reusable SQL helper function (e.g., `public.is_record_owner(record_user_id uuid)`) that checks if the `auth.uid()` of the currently authenticated user matches the `user_id` of a given record. This function should use `SECURITY DEFINER`.
*   **DO:** For each table containing user-specific data and a `user_id` column, enable RLS and create policies that use this helper function in both `USING` (for SELECT, UPDATE, DELETE) and `WITH CHECK` (for INSERT, UPDATE) clauses.
*   **DO:** Manage the creation of the helper function and all RLS policies through Supabase database migrations to ensure consistency across environments and maintain version control.
*   **DO:** Clearly document this RLS strategy and the standard policy application process.
*   **DON'T:** Manually create RLS policies directly in the Supabase dashboard for production environments without a corresponding migration script.
*   **DON'T:** Write complex, repetitive RLS logic directly in each policy if a helper function can centralize it.
*   **DON'T:** Forget to enable RLS on tables that require it (`ALTER TABLE your_table ENABLE ROW LEVEL SECURITY;`).

**Reference Implementation:**

For detailed steps on how to implement this, including SQL function creation, policy examples, and migration management, refer to the guide:
[`supabaseRLSGuide.md`](./supabaseRLSGuide.md)

This guide covers:
*   Creating the `is_record_owner` SQL function.
*   Applying standardized RLS policies to tables.
*   Managing these database objects via Supabase migrations.
*   Testing RLS effectively.

---

## Pattern 12: Monorepo Structure and Component Architecture (Post-Refactor)

**Goal:** Define the high-level structure of the refactored project, outlining the roles of its major components and how they interact. This pattern documents the architectural decisions made during the Phase 0.6 project restructure.

*   **DO:** Maintain a clear separation of concerns between the frontend application (`webApp`), the backend API server (`chatServer`), and the core LLM agent logic (`src`).
*   **DO:** Use the defined interaction flows for communication between these components.
*   **DO:** Manage environment-specific configurations in their respective locations (`webApp/.env`, root `.env`).

### 1. Overall Structure & Roles

The project is now organized into three primary top-level directories, each serving a distinct purpose:

*   **`webApp/`**: Contains the React/TypeScript frontend application. This is what the end-user interacts with for task management, AI coaching, and other UI-driven features. It is responsible for all presentation logic and direct user interaction.
    *   Further details in `webApp/README.md`.
*   **`chatServer/`**: A Python FastAPI backend server. Its primary roles are:
    1.  To provide an API for the `webApp` (e.g., for chat functionality, agent-driven actions).
    2.  To load and manage Langchain agent configurations (from `config/agents/`).
    3.  To execute agent logic by leveraging the core `src/` directory.
    4.  (Future) To handle more complex backend tasks, data processing, or interactions with external services that shouldn't be done directly from the frontend.
    *   Further details in `chatServer/README.md`.
*   **`src/`**: The core Python library for the LLM agent framework. This includes:
    1.  The command-line interface (CLI) for direct agent interaction and development.
    2.  Core logic for agent instantiation, context management, and tool integration.
    3.  Utilities for configuration loading and other shared functionalities.
    *   This directory is utilized by both the `chatServer` (as a library) and the standalone Python CLI.

### 2. Key Decision: Separation of Concerns

The main driver for the refactor was to establish a clearer separation of concerns:

*   **Frontend (`webApp`):** Focuses solely on user interface and user experience. It fetches data and triggers actions via APIs.
*   **Backend (`chatServer`):** Acts as an intermediary and business logic layer. It protects direct access to certain resources, orchestrates complex operations (like agent execution), and can manage its own state or connections (e.g., to Supabase with service roles if needed for specific agent tasks).
*   **Core Logic (`src`):** Contains the reusable engine for LLM agent functionality, independent of how it's exposed (CLI or `chatServer`).

This separation improves maintainability, scalability, and allows for independent development and deployment of the different parts of the application.

### 3. Interaction Flows

*   **`webApp` <-> `chatServer`:**
    *   The `webApp` communicates with the `chatServer` primarily via RESTful API calls to endpoints defined in `chatServer/main.py` (e.g., `/api/chat`).
    *   All chat messages from the UI are sent to the `chatServer`.
    *   (Future) Other agent-driven actions initiated from the UI (e.g., processing notes, creating tasks via agent) will also go through `chatServer` APIs.
*   **`chatServer` <-> `src/`:**
    *   The `chatServer` imports and uses modules from the `src/` directory as a Python library.
    *   It relies on `LLM_AGENT_SRC_PATH=src` (set in the root `.env` file) being added to `sys.path` (as handled in `chatServer/main.py`) to find and load core agent logic, configurations, and utilities from `src/`.
    *   Specifically, it uses `ConfigLoader` and agent execution logic from `src/core/` to run agents based on requests from the `webApp`.
*   **`webApp` <-> Supabase:**
    *   For user authentication and direct data operations (CRUD on tasks, user settings, etc.), the `webApp` interacts directly with Supabase.
    *   This interaction is managed through React Query hooks (`@/api/hooks/`) as defined in **Pattern 5**, which use the Supabase JavaScript client.
    *   Security for these direct frontend-to-Supabase calls is enforced by Supabase's Row Level Security (RLS) policies, as defined in **Pattern 11**.

### 4. Path Aliases & Module Resolution

*   **`webApp/` (Frontend):**
    *   Uses TypeScript path aliases (e.g., `@/*` pointing to `webApp/src/*`) defined in `webApp/tsconfig.json` for cleaner and more maintainable import paths within the React application.
*   **`chatServer/` & `src/` (Backend & Core):**
    *   The `chatServer` relies on the `src/` directory being available in the Python path. This is typically achieved by setting `LLM_AGENT_SRC_PATH=src` in the root `.env` file, which `chatServer/main.py` uses to dynamically add `src` to `sys.path`.
    *   The core Python CLI in `src/` also benefits from the project root being set up for `pip install -e .`, which makes the `src` package importable.

### 5. Configuration Management

Configuration is managed separately for different parts of the application:

*   **`webApp/.env`**: Contains environment variables specifically for the frontend application, primarily `VITE_SUPABASE_URL` and `VITE_SUPABASE_ANON_KEY`.
*   **Root `.env` (in project root `/`):** Contains environment variables for the backend components:
    *   `LLM_AGENT_SRC_PATH=src`: Crucial for `chatServer` to locate the core agent logic.
    *   API keys needed by agents (e.g., `GOOGLE_API_KEY`, `OPENAI_API_KEY`) which might be used by `src/` when agents are executed by either `chatServer` or the CLI.
*   **`config/agents/`**: YAML and Markdown files defining agent configurations (prompts, tools, models). These are loaded by the core logic in `src/` and thus used by both `chatServer` (when serving agent interactions to `webApp`) and the Python CLI.
*   **`config/settings.yaml`**: General settings for the Python CLI and potentially some core library defaults.

*   **Configuration Management:** Critical paths and environment variables (`LLM_AGENT_SRC_PATH` for `chatServer`, `VITE_SUPABASE_URL`, `VITE_SUPABASE_ANON_KEY`, and `VITE_API_BASE_URL` for `webApp`) must be managed through `.env` files (and Fly.io secrets for deployment). The `webApp` utilizes Vite's proxy in `vite.config.ts` for local development to route `/api/*` requests to the `chatServer` at `http://localhost:3001`. For production, `webApp` API calls are constructed using `import.meta.env.VITE_API_BASE_URL`, which is set to the deployed `chatServer`'s URL (e.g., `https://clarity-chatserver.fly.dev`) during the build process.
*   **Root Project Files:** Top-level files like `.gitignore`, the root `package.json` (with `concurrently` script), `pnpm-workspace.yaml`, and deployment configurations (`fly.toml`, `Dockerfile` for each app) are crucial for managing the monorepo and deployments.

---