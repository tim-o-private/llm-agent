# Implementation Plan: Refactor Task Editing UI and Logic

**Version:** 1.1
**Date:** (Current Date)
**Author:** AI Assistant (Gemini)
**Status:** Proposed (Revised to align with Zustand-first write strategy)

## 1. Overview & Goals

This document outlines the plan to refactor the task editing functionality within the Clarity web application. The primary goals are to:

*   Improve code modularity and maintainability.
*   Enhance type safety by introducing strong types and reducing the use of `any`.
*   Simplify the `TaskDetailView` component by decoupling responsibilities.
*   Make the `useEditableEntity` hook more generic and focused on single entity form management, integrating with the established Zustand-first state management pattern.
*   Standardize on React Query for initial data loading/hydration of Zustand stores and for background server synchronization orchestrated by Zustand.
*   Ensure Zustand (`useTaskStore`) remains the primary in-app source of truth for UI display (after initial hydration) and the first receiver of UI-driven changes for optimistic updates.
*   Provide a foundation for robustly editing tasks and their subtasks, including future reordering capabilities.
*   Utilize Radix UI Form for building accessible and robust forms.

## 2. Current State & Problems

*   `TaskDetailView.tsx`: Currently a monolithic component handling data fetching, form state, subtask display, and save logic, making it difficult to understand and modify.
*   `useEditableEntity.ts`: Attempts to be generic but has become overly complex due to handling various sub-entity scenarios directly and lacking clear boundaries for data fetching/saving within the established state flow.
*   **Typing:** Over-reliance on `any` or overly broad types compromises type safety and developer experience.
*   **Data Fetching/Saving:** Need to ensure clear adherence to the pattern: React Query for initial load/hydration & background sync; Zustand for immediate UI state and optimistic updates.

## 3. Proposed Architecture (Aligned with Zustand-First Writes)

The refactor will adhere to the established state management architecture:

*   **Initial Data Loading & Hydration:** `TanStack Query (React Query)` (e.g., hooks in `webApp/src/api/hooks/useTaskApi.ts`) will be used for initial data fetching. This data will then hydrate/populate the relevant **Zustand stores** (e.g., `useTaskStore`).
*   **Primary In-App Source of Truth (for UI display after hydration):** **Zustand Stores** will hold the data displayed in the UI. Components will primarily read data from these stores.
*   **UI-Driven Writes & Optimistic Updates:**
    *   When a user saves a form (e.g., `TaskForm`), the change will be dispatched as an action to the relevant **Zustand store**.
    *   The Zustand store will immediately update its local state (providing an optimistic UI update) and add the change to a `pendingChanges` queue.
*   **Background Synchronization:** The **Zustand store** will orchestrate the background synchronization of `pendingChanges` with the server. This synchronization process will utilize API-calling functions, which can be wrapped by React Query mutation hooks (from `useTaskApi.ts`) for their execution, retry logic, and server response handling.
*   **Form State Management:** `react-hook-form` (RHF), controlled by the refactored `useEditableEntity` hook, will manage the state of individual entity forms. Zod will be used for validation.
*   **UI Components:**
    *   `TaskDetailView.tsx`: Will become a layout component, orchestrating the display of the main task form and the subtask list.
    *   `TaskForm.tsx` (New): A dedicated component for rendering and managing the form for a single task entity. It will use `useEditableEntity`, which in turn interacts with Zustand for data sourcing and saving.
    *   `SubtaskList.tsx` (New): A component responsible for displaying, adding, and editing subtasks, interacting with Zustand for its data.
*   **Generic Editing Hook:**
    *   `useEditableEntity.ts` (Refactored): Will be a generic hook responsible for:
        *   Initializing and managing form state with `react-hook-form`.
        *   Integrating with Zod for validation.
        *   Sourcing initial data for the form via a selector from a Zustand store.
        *   Dispatching save actions to a Zustand store.
        *   Transforming data between the entity shape (from Zustand) and the form shape.

## 4. Detailed Component & Hook Specifications

### 4.1. Types (`webApp/src/types/editableEntityTypes.ts` - New)

```typescript
import { ZodSchema } from 'zod';
import { UseFormReturn, FieldValues } from 'react-hook-form';
import { AppError } from './error'; // Assuming AppError is in a sibling file or imported correctly
import { Task, TaskStatus, TaskPriority } from '@/api/types'; // Ensure correct path

// Type for the function that retrieves entity data, likely from a Zustand store
export type GetEntityDataFn<TEntityData> = (entityId: string | undefined) => TEntityData | undefined;

// Type for the function that saves entity data, by dispatching to a Zustand store
// Returns a Promise that can resolve upon optimistic update or after queuing.
export type SaveEntityFn<TFormData, TEntityData> = (
  formData: TFormData,
  originalEntityData: TEntityData | undefined, // To help Zustand action with diffing or context
  entityId?: string | undefined
) => Promise<void | TEntityData>; // Returns void or the optimistically updated/created entity

export interface UseEditableEntityConfig<
  TEntityData,
  TFormData extends FieldValues,
> {
  entityId: string | null | undefined;
  getEntityDataFn: GetEntityDataFn<TEntityData>;
  saveEntityFn: SaveEntityFn<TFormData, TEntityData>;
  transformDataToForm: (entityData: TEntityData | undefined) => TFormData;
  // transformFormToSaveData is implicitly handled by what's passed to saveEntityFn
  formSchema: ZodSchema<TFormData>;
  defaultFormValues?: TFormData; // For creating new entities or as a fallback
  entityName: string; // For logging, UI messages
  onSaveSuccess?: (updatedData: TEntityData | void, formValues: TFormData) => void; // Callback after successful Zustand dispatch
  onSaveError?: (error: AppError | Error, formValues: TFormData) => void; // Callback if Zustand dispatch fails (e.g., validation within store action)
  isCreatable?: boolean;
}

export interface UseEditableEntityReturn<
  TEntityData,
  TFormData extends FieldValues,
> {
  formMethods: UseFormReturn<TFormData>;
  isSaving: boolean; // Reflects the state of the saveEntityFn call
  // isLoadingInitialData is now more about whether data is present from getEntityDataFn
  // and if the store itself has a loading state for that data.
  // This might need to be derived or passed in if Zustand has per-entity loading states.
  // For simplicity, we'll assume data is available or undefined synchronously from Zustand for the form.
  initialDataError: AppError | Error | null; // Errors from attempting to save (Zustand dispatch phase)
  saveError: AppError | Error | null;
  canSave: boolean; // formMethods.formState.isDirty && formMethods.formState.isValid
  handleSave: () => Promise<void>;
  resetFormToInitial: () => void;
  initialData: TEntityData | undefined; // Data as sourced from getEntityDataFn
  isCreating: boolean;
}

// Example FormData for a Task
export interface TaskFormData {
  title: string;
  description: string | null;
  status: TaskStatus;
  priority: TaskPriority;
  due_date?: string | null;
  // ... other editable fields from Task interface
}
```

### 4.2. Hook: `useEditableEntity.ts` (Refactored)

*   **Signature:**
    ```typescript
    function useEditableEntity<
      TEntityData,
      TFormData extends FieldValues
    >(config: UseEditableEntityConfig<TEntityData, TFormData>): UseEditableEntityReturn<TEntityData, TFormData>;
    ```
*   **Core Logic:**
    *   Uses `config.entityId` to determine if it's an edit or create mode (`isCreating`).
    *   Sources `initialData` using `config.getEntityDataFn(config.entityId)`.
    *   `useForm` (from `react-hook-form`):
        *   `resolver`: `zodResolver(config.formSchema)`.
        *   `defaultValues`: `config.transformDataToForm(initialData)` or `config.defaultFormValues`.
    *   `useEffect` to `reset` the form when `initialData` (from Zustand, via `getEntityDataFn`) changes or `entityId` changes. This ensures the form reflects the current state from the store.
    *   `handleSave` function:
        *   Sets `isSaving` to true.
        *   Calls `formMethods.handleSubmit`.
        *   If valid, calls `config.saveEntityFn(formData, initialData, config.entityId)`.
        *   Handles success (`config.onSaveSuccess`) or error (`config.onSaveError`) from the `saveEntityFn` promise.
        *   Sets `isSaving` to false in a `finally` block.
    *   Returns `UseEditableEntityReturn` structure.
    *   **No direct `useQuery` or `useMutation` from `@tanstack/react-query` will be called *within* this hook for fetching/saving entity data. That is handled by Zustand or the functions configuring this hook.**

### 4.3. API Hooks: `webApp/src/api/hooks/useTaskApi.ts` (Clarified Role)

This file will centralize all TanStack Query hooks related to Task entities.
**Important Clarification:** These hooks are primarily used for:
1.  **Initial data loading** to hydrate Zustand stores (e.g., on application startup or when a major data view is first accessed).
2.  By the **background synchronization process within Zustand stores** to communicate with the backend API (e.g., when `syncWithServer` in `useTaskStore` processes pending changes).

UI components like `TaskForm` will generally **not** call these React Query mutation hooks directly for saving form data. They will interact with Zustand actions instead.

```typescript
// ... (rest of the useTaskApi.ts content from previous plan, like taskQueryKeys, API functions, and RQ hooks remains the same)
// Add a comment at the top of the file or in its README explaining its role.

// Example:
// Note: These hooks are primarily intended for initial data hydration of Zustand stores
// and for use by the background server synchronization logic within those stores.
// UI components should typically interact with Zustand store actions for optimistic updates
// and data manipulation, rather than calling these mutation hooks directly for form saves.
import { useQuery, useMutation, useQueryClient, UseQueryResult, UseMutationResult } from '@tanstack/react-query';
// ... (rest of the code)
```

### 4.4. Component: `TaskForm.tsx` (New)

*   **Props:** (Same as before)
    *   `taskId: string | null | undefined`
    *   `parentTaskId?: string | null`
    *   `onSaveSuccess?: (savedTask: Task | void) => void` // Reflects Zustand optimistic update result
    *   `onCancel?: () => void`
*   **Core Logic:**
    *   Defines `TaskFormData` interface and `taskFormSchema`.
    *   Sources task data and save actions from `useTaskStore` (or equivalent selectors/actions).
    *   Configures `UseEditableEntityConfig` for Tasks:
        *   `entityId`: `taskId` prop.
        *   `getEntityDataFn`: e.g., `(id) => useTaskStore.getState().tasks[id]` (or a memoized selector from the store).
        *   `saveEntityFn`: A function that calls the appropriate `useTaskStore` action (e.g., `(formData, originalData, id) => id ? useTaskStore.getState().updateTask(id, transformFormToApiUpdate(formData, originalData)) : useTaskStore.getState().createTask(transformFormToApiCreate(formData, parentTaskId))`). This needs helper functions `transformFormToApiUpdate` and `transformFormToApiCreate` to shape data for Zustand actions.
        *   `transformDataToForm`: Maps `Task` (from Zustand) to `TaskFormData`.
        *   `formSchema`: `taskFormSchema`.
        *   `defaultFormValues`: For a new task.
        *   `entityName`: "Task".
        *   `onSaveSuccess`: Calls prop `onSaveSuccess`.
    *   Calls `useEditableEntity` with this config.
    *   Renders Radix UI Form components, binding to `formMethods` from `useEditableEntity`.
    *   Submit button calls `handleSave` from `useEditableEntity`.

### 4.5. Component: `SubtaskList.tsx` (New)

*   **Props:** (Same as before)
    *   `parentTaskId: string`
*   **Core Logic:**
    *   Uses a selector from `useTaskStore` to get subtask data for the `parentTaskId`.
    *   "Add Subtask" button opens a modal with `TaskForm` configured for creating a subtask (dispatching to `useTaskStore.createTask` with `parent_task_id`).
    *   "Edit" button opens `TaskForm` for the specific subtask.
    *   (Future) Drag-and-drop reordering will dispatch actions to `useTaskStore` to update subtask positions and queue for sync.

### 4.6. Component: `TaskDetailView.tsx` (Refactored)

*   **Core Logic:** (Largely the same conceptually)
    *   Gets `taskId` from route parameters.
    *   Renders `<TaskForm taskId={taskId} ... />`.
    *   If `taskId` is present, renders `<SubtaskList parentTaskId={taskId} ... />`.

## 5. Data Flow Summary (Aligned with Zustand-First Writes)

1.  **Initial App Load / View Mount:**
    *   A higher-level component or effect calls a React Query hook (e.g., `useFetchTasksListEffect` not shown, or `useFetchTask` if loading a specific detail view directly) to fetch initial data.
    *   The `onSuccess` callback of this React Query hook hydrates/updates the `useTaskStore` with the fetched tasks.
2.  **Form Mount (`TaskForm`):**
    *   `TaskForm` initializes `useEditableEntity`.
    *   `useEditableEntity` calls its `config.getEntityDataFn` which selects the current task data from `useTaskStore`.
    *   `useEditableEntity` transforms this data (if needed) and sets `react-hook-form`'s default values.
3.  **User Edits Form:**
    *   `react-hook-form` tracks dirty state and validation locally within the form.
4.  **User Clicks Save:**
    *   `TaskForm` calls `handleSave` from `useEditableEntity`.
    *   `useEditableEntity` validates the form.
    *   If valid, `useEditableEntity` calls its `config.saveEntityFn`.
    *   `saveEntityFn` **dispatches an action to `useTaskStore`** (e.g., `useTaskStore.getState().updateTask(id, updates)`).
    *   `useTaskStore`:
        *   Immediately updates its local state with the changes (optimistic UI update).
        *   Adds the change to its `pendingChanges` queue.
        *   Components subscribed to `useTaskStore` re-render with the optimistic update.
    *   The `onSaveSuccess` callback in `TaskForm` (via `useEditableEntity`) is triggered.
5.  **Background Synchronization (Managed by `useTaskStore`):**
    *   Periodically, or triggered by other events, `useTaskStore`'s `syncWithServer` logic runs.
    *   It processes items in `pendingChanges`.
    *   For each change, it calls the relevant React Query mutation hook (e.g., `useUpdateTaskMutation().mutate(...)`) to send the data to the server.
    *   React Query handles the API call, retries, etc.
    *   On successful server sync, the change is removed from `pendingChanges`. `useTaskStore` might update its state with confirmed data from server if different.
    *   On server sync error, `useTaskStore` handles the error (logs, marks pending change as errored, potentially reverts optimistic update or notifies user).

## 6. Error Handling

*   **Form Validation Errors:** Handled by Zod and `react-hook-form`, displayed by Radix UI Form components.
*   **Optimistic Update/Zustand Dispatch Errors:** The `saveEntityFn` promise in `useEditableEntity` can reject if the Zustand action itself fails synchronously (e.g., internal validation). These are surfaced via `saveError` in `useEditableEntity`.
*   **Background Server Sync Errors:** These are managed by the `useTaskStore`'s sync logic. The UI needs a way to observe this global sync status and any persistent errors (e.g., a toast, a status indicator). These errors are generally not tied to a specific `TaskForm` instance once its optimistic update has completed.

## 7. State Management (`useTaskStore.ts`) - Re-emphasized Role

*   As per `state-management-design.md`, `useTaskStore` is the **central hub for task-related state accessible by UI components after initial hydration.**
*   It is the **first recipient of UI-driven changes**, performing optimistic updates and managing a `pendingChanges` queue.
*   It **orchestrates background synchronization** with the server, using React Query mutation hooks for the actual API calls.
*   The `getTaskById` selector (or similar selectors) from `useTaskStore` will be the primary way `TaskForm` (via `useEditableEntity`) gets its data.

## 8. Testing Strategy

*   (Remains largely the same, but tests for `useEditableEntity` will mock Zustand store interactions instead of direct React Query query/mutation hooks for data sourcing/saving).

## 9. Phased Rollout / Future Enhancements

*   (Remains the same).

## 10. Open Questions / Considerations

*   **Hydration Strategy:** Ensure a robust and efficient way to hydrate `useTaskStore` from React Query on initial load.
*   **Selector Performance:** Use memoized selectors from Zustand (`import { createSelector } from 'reselect'` with Zustand or Zustand's own middleware if performance becomes an issue for components frequently reading from the store).
*   **Sync Error Visibility:** How are persistent background sync errors made visible to the user and how can they be resolved? (This is a broader concern of the sync mechanism in `useTaskStore`).

This revised plan should now be in full alignment with your specified state management architecture. 