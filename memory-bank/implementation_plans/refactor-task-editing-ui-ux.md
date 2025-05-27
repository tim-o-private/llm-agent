# Implementation Plan: Refactor Task Editing UI and Logic

**Version:** 1.0
**Date:** (Current Date)
**Author:** AI Assistant (Gemini)
**Status:** Proposed

## 1. Overview & Goals

This document outlines the plan to refactor the task editing functionality within the Clarity web application. The primary goals are to:

*   Improve code modularity and maintainability.
*   Enhance type safety by introducing strong types and reducing the use of `any`.
*   Simplify the `TaskDetailView` component by decoupling responsibilities.
*   Make the `useEditableEntity` hook more generic and focused on single entity form management.
*   Standardize on React Query for server state management for tasks, with Zustand (`useTaskStore`) serving as a reactive cache or for client-specific UI state.
*   Provide a foundation for robustly editing tasks and their subtasks, including future reordering capabilities.
*   Utilize Radix UI Form for building accessible and robust forms.

## 2. Current State & Problems

*   `TaskDetailView.tsx`: Currently a monolithic component handling data fetching, form state, subtask display, and save logic, making it difficult to understand and modify.
*   `useEditableEntity.ts`: Attempts to be generic but has become overly complex due to handling various sub-entity scenarios directly and lacking clear boundaries for data fetching/saving.
*   **Typing:** Over-reliance on `any` or overly broad types (e.g., `Record<string, any>`) compromises type safety and developer experience.
*   **Data Fetching:** Inconsistent patterns for fetching data (sometimes direct store access, sometimes through hooks, but not consistently React Query for server state).

## 3. Proposed Architecture

The refactor will introduce a clearer separation of concerns:

*   **Server State Management:** `TanStack Query (React Query)` will be the definitive source for fetching, caching, and updating server-side data (tasks, subtasks).
    *   New hooks will be created in `webApp/src/api/hooks/useTaskApi.ts`.
*   **Form State Management:** `react-hook-form` (RHF) controlled by `useEditableEntity` will manage the state of individual entity forms. Zod will be used for validation.
*   **UI Components:**
    *   `TaskDetailView.tsx`: Will become a layout component, orchestrating the display of the main task form and the subtask list.
    *   `TaskForm.tsx` (New): A dedicated component for rendering and managing the form for a single task entity (main task or a subtask being edited). It will use `useEditableEntity`.
    *   `SubtaskList.tsx` (New): A component responsible for displaying, adding, editing (by invoking `TaskForm`), and eventually reordering subtasks associated with a parent task.
*   **Generic Editing Hook:**
    *   `useEditableEntity.ts` (Refactored): Will be a highly generic hook responsible for:
        *   Initializing and managing form state with `react-hook-form`.
        *   Integrating with Zod for validation.
        *   Orchestrating data loading via a `queryFn` (which will typically be a React Query `useQuery` hook).
        *   Orchestrating data saving via a `saveMutationFn` (which will typically be a React Query `useMutation` hook).
        *   Transforming data between the entity shape and the form shape.
*   **Zustand Store (`useTaskStore.ts`):**
    *   Its role will be primarily as a reactive cache that is updated by React Query (e.g., through `onSuccess` callbacks or query invalidations).
    *   It can also be used for purely client-side UI state related to tasks if necessary, but not as the primary source of truth for server data.

## 4. Detailed Component & Hook Specifications

### 4.1. Types (`webApp/src/types/editableEntityTypes.ts` - New)

```typescript
import { ZodSchema } from 'zod';
import { UseFormReturn, FieldValues, Path, PathValue } from 'react-hook-form';
import { UseQueryResult, UseMutationResult } from '@tanstack/react-query';
import { AppError } from './error'; // Assuming AppError is in a sibling file or imported correctly

export interface UseEditableEntityConfig<
  TQueryKey extends readonly unknown[], // For React Query: queryKey
  TEntityData,                          // Type of the entity data fetched
  TFormData extends FieldValues,        // Type for react-hook-form
  TSaveData,                            // Type for the data sent on save (often a partial of TEntityData or TFormData)
  TQueryError = AppError,               // Error type for the query
  TSaveError = AppError                 // Error type for the mutation
> {
  entityId: string | null | undefined; // ID of the entity to edit, or null/undefined for creation
  queryKey: TQueryKey; // React Query key, incorporating entityId
  queryFn: (id: string) => Promise<TEntityData>; // Async function to fetch entity data, used by useQuery
  saveMutationFn: (data: TSaveData & { id?: string }) => Promise<TEntityData>; // Async function to save entity data
  transformDataToForm: (entityData: TEntityData | undefined) => TFormData;
  transformFormToSaveData?: (formData: TFormData, initialData: TEntityData | undefined) => TSaveData; // Optional, defaults to formData as TSaveData
  formSchema: ZodSchema<TFormData>;
  defaultFormValues?: TFormData; // Used if entityId is null/undefined or if queryFn returns undefined initially
  entityName: string; // For logging and potentially UI messages, e.g., "Task"
  onSaveSuccess?: (savedData: TEntityData, formValues: TFormData, variables: TSaveData & { id?: string }) => void;
  onSaveError?: (error: TSaveError, formValues: TFormData, variables: TSaveData & { id?: string }) => void;
  isCreatable?: boolean; // If true, allows entityId to be null/undefined for creating new entities
}

export interface UseEditableEntityReturn<
  TEntityData,
  TFormData extends FieldValues,
  TQueryError = AppError,
  TSaveError = AppError
> {
  formMethods: UseFormReturn<TFormData>;
  isSaving: boolean;
  isLoadingInitialData: boolean; // From useQuery
  isFetchingInitialData: boolean; // From useQuery
  initialDataError: TQueryError | null; // From useQuery
  saveError: TSaveError | null; // From useMutation
  canSave: boolean; // formMethods.formState.isDirty && formMethods.formState.isValid
  handleSave: () => Promise<void>;
  resetFormToInitial: () => void;
  initialData: TEntityData | undefined; // Data as fetched
  isCreating: boolean; // True if entityId was initially null/undefined
}

// Example FormData for a Task
export interface TaskFormData {
  title: string;
  description: string | null;
  status: TaskStatus; // Assuming TaskStatus is imported from api/types
  priority: TaskPriority; // Assuming TaskPriority is imported from api/types
  due_date?: string | null;
  // ... other editable fields from Task interface
}
```

### 4.2. Hook: `useEditableEntity.ts` (Refactored)

*   **Signature:**
    ```typescript
    function useEditableEntity<
      TQueryKey extends readonly unknown[],
      TEntityData,
      TFormData extends FieldValues,
      TSaveData,
      TQueryError = AppError,
      TSaveError = AppError
    >(config: UseEditableEntityConfig<TQueryKey, TEntityData, TFormData, TSaveData, TQueryError, TSaveError>): UseEditableEntityReturn<TEntityData, TFormData, TQueryError, TSaveError>;
    ```
*   **Core Logic:**
    *   Uses `config.entityId` to determine if it's an edit or create mode.
    *   `useQuery` (from `@tanstack/react-query`):
        *   `queryKey`: Derived from `config.queryKey` and `config.entityId`.
        *   `queryFn`: Wraps `config.queryFn(config.entityId)` if `entityId` is present.
        *   `enabled`: Only if `config.entityId` is present and not in create mode without initial fetch.
    *   `useForm` (from `react-hook-form`):
        *   `resolver`: `zodResolver(config.formSchema)`.
        *   `defaultValues`: `config.defaultFormValues` or transformed data from `useQuery`.
    *   `useEffect` to `reset` the form when `useQuery` data changes or `entityId` changes.
    *   `useMutation` (from `@tanstack/react-query`):
        *   `mutationFn`: `config.saveMutationFn`.
        *   `onSuccess`: Invalidates relevant queries (e.g., list query for the entity type, the specific entity query), calls `config.onSaveSuccess`.
        *   `onError`: Calls `config.onSaveError`.
    *   `handleSave` function:
        *   Calls `formMethods.handleSubmit`.
        *   If valid, calls the save mutation with `config.transformFormToSaveData(formData, initialData)` or just `formData`.
    *   Returns `UseEditableEntityReturn` structure.

### 4.3. API Hooks: `webApp/src/api/hooks/useTaskApi.ts` (New/Enhanced)

This file will centralize all React Query hooks related to Task entities.

```typescript
import { useQuery, useMutation, useQueryClient, UseQueryResult, UseMutationResult } from '@tanstack/react-query';
import { Task, NewTaskData, UpdateTaskData, TaskStatus, TaskPriority } from '../types'; // Assuming these are correctly defined
import { AppError } from '@/types/error'; // Adjust path as needed
// Assume an apiClient exists for making actual API calls, e.g.:
// import apiClient from '@/api/apiClient';

// == Query Keys ==
export const taskQueryKeys = {
  all: ['tasks'] as const,
  lists: () => [...taskQueryKeys.all, 'list'] as const,
  list: (filters: string) => [...taskQueryKeys.lists(), { filters }] as const, // Example with filters
  details: () => [...taskQueryKeys.all, 'detail'] as const,
  detail: (id: string | undefined) => [...taskQueryKeys.details(), id] as const,
  subtasks: (parentId: string | undefined) => [...taskQueryKeys.all, 'subtasks', parentId] as const,
};

// == API Functions (examples - adapt to your actual API client) ==
// These would typically live in an API client service, not directly in the hook file,
// but are shown here for completeness of the example.
const fetchTaskById = async (id: string): Promise<Task> => {
  // return apiClient.get<Task>(`/tasks/${id}`);
  console.log(`Simulating fetch Task ${id}`);
  // Replace with actual API call
  return new Promise(resolve => setTimeout(() => resolve({ id, title: `Task ${id}`, description: 'Fetched Desc', status: 'pending', priority: 0, user_id: 'user1', created_at: new Date().toISOString(), updated_at: new Date().toISOString(), completed: false } as Task), 500));
};

const createTask = async (data: NewTaskData): Promise<Task> => {
  // return apiClient.post<Task>('/tasks', data);
  console.log('Simulating create Task', data);
  const newTask = { ...data, id: `new-${Date.now()}`, created_at: new Date().toISOString(), updated_at: new Date().toISOString(), completed: data.status === 'completed' } as Task;
  return new Promise(resolve => setTimeout(() => resolve(newTask), 500));
};

const updateTask = async (data: UpdateTaskData & { id: string }): Promise<Task> => {
  // return apiClient.put<Task>(`/tasks/${data.id}`, data);
  console.log(`Simulating update Task ${data.id}`, data);
   const updatedTask = { ...data, title: data.title || "Updated Title", updated_at: new Date().toISOString(), completed: data.status === 'completed' } as Task;
  return new Promise(resolve => setTimeout(() => resolve(updatedTask), 500));
};

const fetchSubtasks = async (parentId: string): Promise<Task[]> => {
    // return apiClient.get<Task[]>(`/tasks/${parentId}/subtasks`);
    console.log(`Simulating fetch subtasks for ${parentId}`);
    return new Promise(resolve => setTimeout(() => resolve([]), 500)); // Example empty array
}

// == React Query Hooks ==
export const useFetchTask = (taskId: string | undefined): UseQueryResult<Task, AppError> => {
  return useQuery<Task, AppError, Task, readonly unknown[]>({ // Explicitly type queryKey
    queryKey: taskQueryKeys.detail(taskId),
    queryFn: () => {
      if (!taskId) throw new Error("Task ID is required to fetch a task.");
      return fetchTaskById(taskId);
    },
    enabled: !!taskId,
  });
};

export const useCreateTaskMutation = (): UseMutationResult<Task, AppError, NewTaskData> => {
  const queryClient = useQueryClient();
  return useMutation<Task, AppError, NewTaskData>({
    mutationFn: createTask,
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: taskQueryKeys.lists() });
      queryClient.setQueryData(taskQueryKeys.detail(data.id), data);
    },
  });
};

export const useUpdateTaskMutation = (): UseMutationResult<Task, AppError, UpdateTaskData & { id: string }> => {
  const queryClient = useQueryClient();
  return useMutation<Task, AppError, UpdateTaskData & { id: string }>({
    mutationFn: updateTask,
    onSuccess: (data, variables) => {
      queryClient.invalidateQueries({ queryKey: taskQueryKeys.lists() });
      queryClient.invalidateQueries({ queryKey: taskQueryKeys.detail(variables.id) });
      queryClient.setQueryData(taskQueryKeys.detail(data.id), data); // Optimistically update if needed, or rely on invalidation
    },
  });
};

export const useFetchSubtasks = (parentId: string | undefined): UseQueryResult<Task[], AppError> => {
    return useQuery<Task[], AppError, Task[], readonly unknown[]>({
        queryKey: taskQueryKeys.subtasks(parentId),
        queryFn: () => {
            if (!parentId) throw new Error("Parent Task ID is required to fetch subtasks.");
            return fetchSubtasks(parentId);
        },
        enabled: !!parentId,
    });
};
```

### 4.4. Component: `TaskForm.tsx` (New)

*   **Props:**
    *   `taskId: string | null | undefined` (for editing or creating)
    *   `parentTaskId?: string | null` (if creating a subtask)
    *   `onSaveSuccess?: (savedTask: Task) => void`
    *   `onCancel?: () => void`
*   **Core Logic:**
    *   Defines `TaskFormData` interface and `taskFormSchema` (Zod schema).
    *   Configures `UseEditableEntityConfig` for Tasks:
        *   `entityId`: `taskId` prop.
        *   `queryKey`: `taskQueryKeys.detail(taskId)`.
        *   `queryFn`: `(id) => fetchTaskById(id)` (from `useTaskApi`).
        *   `saveMutationFn`: Based on `taskId` (create or update), using `createTask` or `updateTask` from `useTaskApi`.
        *   `transformDataToForm`: Maps `Task` to `TaskFormData`.
        *   `transformFormToSaveData`: Maps `TaskFormData` to `NewTaskData` or `UpdateTaskData`. If `parentTaskId` is present, includes it in `NewTaskData`.
        *   `formSchema`: `taskFormSchema`.
        *   `defaultFormValues`: For a new task.
        *   `entityName`: "Task".
        *   `onSaveSuccess`: Calls prop `onSaveSuccess`, potentially closes modal/form.
    *   Calls `useEditableEntity` with this config.
    *   Renders a form using Radix UI Form components (`Form.Root`, `Form.Field`, `Form.Label`, `Form.Control`, `Form.Message`, `Form.Submit`).
    *   Binds inputs to `formMethods` from `useEditableEntity`.
    *   Submit button calls `handleSave` from `useEditableEntity`.
    *   Cancel button calls `onCancel` prop.

### 4.5. Component: `SubtaskList.tsx` (New)

*   **Props:**
    *   `parentTaskId: string`
*   **Core Logic:**
    *   Uses `useFetchSubtasks(parentTaskId)` from `useTaskApi.ts` to get subtask data.
    *   Displays a list of subtasks (e.g., using `TaskCard` or a simpler list item).
    *   "Add Subtask" button:
        *   Likely opens a modal containing `TaskForm` with `taskId={null}` and `parentTaskId={props.parentTaskId}`.
    *   Each subtask item should have an "Edit" button:
        *   Opens a modal containing `TaskForm` with `taskId={subtask.id}`.
    *   (Future) Drag-and-drop reordering logic (e.g., using `dnd-kit`). This will involve a new mutation in `useTaskApi.ts` for updating subtask positions.

### 4.6. Component: `TaskDetailView.tsx` (Refactored)

*   **Core Logic:**
    *   Gets `taskId` from route parameters.
    *   Renders `<TaskForm taskId={taskId} />`.
    *   If `taskId` is present, renders `<SubtaskList parentTaskId={taskId} />`.
    *   Manages overall layout, potentially including a header or navigation elements.

## 5. Data Flow Summary

1.  **View Mount (`TaskDetailView` -> `TaskForm`):**
    *   `TaskForm` initializes `useEditableEntity`.
    *   `useEditableEntity` calls `useQuery` (via `config.queryFn` which uses `useFetchTask`).
    *   Data is fetched, `useEditableEntity` transforms it and sets form default values.
2.  **User Edits Form:**
    *   `react-hook-form` tracks dirty state and validation.
3.  **User Clicks Save:**
    *   `TaskForm` calls `handleSave` from `useEditableEntity`.
    *   `useEditableEntity` validates the form.
    *   If valid, `useEditableEntity` calls `useMutation` (via `config.saveMutationFn` which uses `useUpdateTask` or `useCreateTask`).
    *   `useMutation`'s `onSuccess`:
        *   Invalidates React Query caches (task list, task detail).
        *   React Query refetches data, updating the UI.
        *   `useTaskStore` (if subscribed to query changes or updated via callbacks) reflects new data.
        *   `TaskForm`'s `onSaveSuccess` callback is triggered.

## 6. Error Handling

*   `useEditableEntity` will expose `initialDataError` (from `useQuery`) and `saveError` (from `useMutation`).
*   `TaskForm` will display these errors to the user (e.g., using toast notifications or inline messages).
*   Field-level validation errors from Zod will be displayed by Radix UI Form components.
*   All errors should conform to the `AppError` interface where possible.

## 7. State Management (`useTaskStore.ts`)

*   `useTaskStore` will no longer be the primary owner of task server data.
*   It can subscribe to React Query's cache or be updated via `onSuccess` callbacks from mutations if specific client-side reactive state is needed beyond what React Query provides.
*   For example, if a global list of tasks needs to be instantly reactive elsewhere in the app, the store can hold a copy that's synced.
*   The `getTaskById` selector might still be useful if it reads from a store populated by React Query, providing a synchronous way to access already fetched data if needed by non-React components (though direct component usage of React Query hooks is preferred).

## 8. Testing Strategy

*   **Unit Tests (Vitest/Jest):**
    *   `useEditableEntity`: Test different configurations (create, edit, error states, transformations). Mock query/mutation functions.
    *   `useTaskApi`: Test individual query/mutation hooks. Mock the API client.
    *   `TaskForm`: Test rendering, form submission, interaction with `useEditableEntity`. Mock `useEditableEntity`.
    *   `SubtaskList`: Test rendering, interaction with `useFetchSubtasks`.
*   **Integration Tests (React Testing Library):**
    *   Test `TaskDetailView`'s ability to load a task, allow edits, save, and display subtasks.
    *   Test the flow of adding and editing subtasks.

## 9. Phased Rollout / Future Enhancements

*   **Phase 1 (This Plan):** Implement core refactor for `TaskDetailView`, `TaskForm`, `useEditableEntity`, and basic `SubtaskList` (display, add, edit).
*   **Phase 2:** Implement subtask reordering in `SubtaskList`.
*   **Phase 3:** Extend `useEditableEntity` or create variants for other entity types if the pattern proves successful (e.g., Projects).

## 10. Open Questions / Considerations

*   **Real-time Updates:** If tasks need real-time updates (e.g., via WebSockets), React Query's integration points or Supabase real-time subscriptions would be used to update the cache, and `useEditableEntity` would react to those changes.
*   **Optimistic Updates:** React Query's `onMutate` and related options can be used for optimistic updates in `useTaskApi.ts` if desired for better perceived performance.
*   **Complexity of `SubtaskList`:** If subtask management becomes very complex, `SubtaskList` itself might warrant further decomposition or its own dedicated state management hooks beyond simple list display.

This document provides a comprehensive plan. Upon review and approval, development can proceed. 