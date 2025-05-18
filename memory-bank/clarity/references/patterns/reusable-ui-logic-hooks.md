# Reusable UI Logic Hooks: `useObjectEditManager` and `useReorderableList`

**Owner:** AI Agent & Development Team
**Status:** Proposed
**Created:** (Current Date)
**Last Updated:** (Current Date)

## 1. Introduction

To enhance code reusability, maintainability, and separation of concerns within the Clarity web application, we propose the creation of two versatile custom React hooks:

*   `useObjectEditManager`: A hook to manage the state and actions for editing an arbitrary data object within a modal or form.
*   `useReorderableList`: A hook to manage the state and actions for a list of items that can be reordered using drag-and-drop, and supports operations like adding and editing list items.

These hooks aim to abstract common patterns observed in components like `TaskDetailView.tsx` (for editing a task and managing its subtasks) and `TodayView.tsx` (for reordering top-level tasks).

## 2. `useObjectEditManager`

### 2.1. Purpose

This hook will encapsulate the logic for managing the editing lifecycle of a single data object. It will integrate with React Hook Form for form state management and validation, and handle data fetching, mutation (save/update), and change tracking.

### 2.2. Proposed API & Features

```typescript
interface ObjectEditManagerOptions<
  TData extends { id: string },
  TFormData extends FieldValues,
  TUpdateData extends Record<string, unknown>,
  TCreateData = Omit<TUpdateData, 'id'>
> {
  objectType: string; // e.g., "task", "calendarEvent"
  objectId: string | null; // ID of the object to edit, or null for new object
  fetchQueryHook: (id: string | null) => UseQueryResult<TData | null, Error>; // React Query hook to fetch the object
  updateMutationHook: () => UseMutationResult<TData, Error, { id: string; updates: TUpdateData }, unknown>;
  createMutationHook?: () => UseMutationResult<TData, Error, TCreateData, unknown>; // Optional for creation
  zodSchema: z.ZodType<TFormData>;
  defaultValues: DefaultValues<TFormData>; // Changed from initialFormData
  transformDataToFormData: (data: TData | null) => TFormData;
  transformFormDataToUpdateData: (formData: TFormData, originalData: TData | null) => TUpdateData;
  transformFormDataToCreateData?: (formData: TFormData) => TCreateData; // Added
  onSaveSuccess?: (savedData: TData, isNew: boolean) => void; // Added isNew flag
  onClose?: () => void; // Callback to handle modal close logic
  onLoadError?: (error: Error) => void; // Added
}

interface ObjectEditManagerResult<TData, TFormData extends FieldValues> {
  // RHF form methods and state
  formMethods: UseFormReturn<TFormData>; // Includes register, handleSubmit, control, reset, formState, watch, etc.
  
  // Data state
  originalData: TData | null;
  isLoading: boolean; // True if fetching or saving
  isFetching: boolean; // Added: True if fetching initial data specifically
  error: Error | null;
  
  // Actions
  handleSave: (e?: React.BaseSyntheticEvent) => Promise<void>; // Wrapper around RHF handleSubmit
  handleCancel: () => void; // Handles dirty checking and confirmation
  
  // Status
  isDirty: boolean; // From RHF
  isSaving: boolean; // Combined loading state of mutations
  canSubmit: boolean; // Added: Considers isDirty and !isSaving

  // Utility to reset form, useful after external changes or successful save
  resetForm: (data?: TData | null) => void; // Resets form with new data or defaults
}

function useObjectEditManager<
  TData extends { id: string },
  TFormData extends FieldValues,
  TUpdateData extends Record<string, unknown>,
  TCreateData = Omit<TUpdateData, 'id'>
>(
  options: ObjectEditManagerOptions<TData, TFormData, TUpdateData, TCreateData>
): ObjectEditManagerResult<TData, TFormData>;
```

**Key Features:**

*   **Generic Typing:** `TData` (original object type), `TFormData` (RHF form data type), `TUpdateData` (type for mutation payload), `TCreateData` (type for creating new items).
*   **React Hook Form Integration:** Exposes `formMethods` directly.
*   **Data Lifecycle Management:** Handles fetching, resetting form on data change, and mutation calls.
*   **Dirty State & Change Tracking:** Leverages RHF's `isDirty`.
*   **Configurable:** Transformation functions allow adapting to various data structures.
*   **Save & Cancel Logic:** Provides standardized handlers, including confirmation for unsaved changes on cancel.

### 2.3. Benefits

*   Reduces boilerplate in components that edit single objects.
*   Standardizes form handling, validation, and submission logic.
*   Improves testability by isolating editing logic.
*   Promotes consistency across different editor modals/forms.

## 3. `useReorderableList`

### 3.1. Purpose

This hook will manage the state and interactions for a list of items that can be reordered via drag-and-drop (using `dnd-kit`), and potentially supports adding new items or triggering edits for existing items within that list.

### 3.2. Proposed API & Features

```typescript
interface ReorderableListOptions<
  TItem extends { id: UniqueIdentifier }, 
  TNewItemData
> {
  listName: string; // Changed from objectType
  parentObjectId: string | null; // ID of the parent object this list belongs to
  
  // Data Hooks
  fetchListQueryHook: (parentId: string | null) => UseQueryResult<TItem[], Error>;
  updateOrderMutationHook: () => UseMutationResult<
    TItem[], 
    Error,
    { parentId: string | null; orderedItems: Array<{ id: UniqueIdentifier; position: number } & Partial<TItem>> }, // Updated payload
    unknown
  >;
  createItemMutationHook?: () => UseMutationResult<
    TItem, 
    Error,
    { parentId: string | null; newItem: TNewItemData; position?: number }, // Updated payload
    unknown
  >; 
  
  // Item Configuration
  getItemId: (item: TItem) => UniqueIdentifier; // Type changed
  getItemPosition?: (item: TItem) => number; 
  getNewItemPosition?: (items: TItem[], newItemData: TNewItemData) => number;
  
  // Callbacks
  onReorderCommit?: (reorderedItems: TItem[]) => void; 
  onItemAdded?: (newItem: TItem) => void;
  onFetchError?: (error: Error) => void; // Added
}

interface ReorderableListResult<TItem extends { id: UniqueIdentifier }, TNewItemData> {
  // List State
  items: TItem[]; // Reflects optimistic updates
  isLoading: boolean; 
  isFetching: boolean; // Added
  isUpdatingOrder: boolean; // Added
  isAddingItem: boolean; // Added
  error: Error | null;
  
  // Dnd-kit State & Handlers
  dndSensors: ReturnType<typeof useSensors>;
  handleDragStart: (event: DragStartEvent) => void; // Added
  handleDragEnd: (event: DragEndEvent) => void;
  activeDragItem: TItem | null; // Added
  
  // Item Actions
  handleAddItem?: (newItemData: TNewItemData) => Promise<TItem | undefined>; // Updated return type
  
  // Removed isReordering, isAddingItem (covered by more specific states)
  // Removed optimisticItems, setOptimisticItems (managed internally)

  refetchList: () => void; // Added
}

function useReorderableList<
  TItem extends { id: UniqueIdentifier },
  TNewItemData
>(
  options: ReorderableListOptions<TItem, TNewItemData>
): ReorderableListResult<TItem, TNewItemData>;
```

**Key Features:**

*   **Generic Typing:** `TItem` (type of list items, must have `id: UniqueIdentifier`), `TNewItemData` (type for creating new items).
*   **`dnd-kit` Integration:** Encapsulates sensor setup, `handleDragStart`, and `handleDragEnd` logic.
*   **Optimistic Updates:** Handled internally; the `items` array reflects optimistic state.
*   **Data Lifecycle:** Handles fetching the list, committing reordered positions, and adding new items.
*   **Configurable:** Item ID and position accessors, mutation hooks.

### 3.3. Benefits

*   Abstracts complex `dnd-kit` setup and state management for reorderable lists.
*   Provides a consistent pattern for optimistic UI updates during drag-and-drop.
*   Simplifies components that display and manage ordered lists of sub-entities.
*   Enhances testability of list interaction logic.

## 4. Integration Example (Conceptual for `TaskDetailView`)

```typescript
// Simplified TaskDetailView.tsx (Conceptual)

const TaskDetailView = ({ taskId, isOpen, onOpenChange }) => {
  const {
    formMethods,
    originalData: task,
    isLoading: isLoadingTask,
    handleSave,
    handleCancel,
    isDirty: isTaskDirty,
    isSaving: isTaskSaving,
  } = useObjectEditManager<Task, TaskFormData, UpdateTaskData>({
    objectType: 'task',
    objectId: taskId,
    fetchQueryHook: useFetchTaskById,
    updateMutationHook: useUpdateTask,
    zodSchema: taskFormSchema,
    transformDataToFormData: /* ... */,
    transformFormDataToUpdateData: /* ... */,
    onSaveSuccess: () => onOpenChange(false),
    onClose: () => onOpenChange(false),
  });

  const {
    items: subtasks,
    isLoading: isLoadingSubtasks,
    handleDragEnd: handleSubtaskDragEnd,
    handleAddItem: handleAddSubtask,
    dndSensors: subtaskDndSensors,
    optimisticItems: optimisticSubtasks,
    setOptimisticItems: setOptimisticSubtasks,
  } = useReorderableList<Task, NewTaskData>({ // Assuming Subtask is also a Task type
    objectType: 'subtask',
    parentObjectId: taskId,
    fetchListQueryHook: useFetchSubtasks,
    updateOrderMutationHook: useUpdateSubtaskOrder,
    createItemMutationHook: useCreateTask, // Adapted for subtasks
    getItemId: (item) => item.id,
    getItemPosition: (item) => item.subtask_position,
  });

  // ... JSX using formMethods, task data, subtask data, and handlers ...
  // The "Save Changes" button's disabled state would consider isTaskDirty, 
  // isTaskSaving, and potentially a similar 'isDirty' or 'isSaving' flag 
  // from useReorderableList if subtask changes should also gate the main save.
  // Alternatively, subtask changes (add, reorder, edit) might be auto-saved.
};
```

## 5. Next Steps

1.  **Refine API:** Discuss and finalize the proposed hook APIs.
2.  **Implementation:** Develop the `useObjectEditManager` and `useReorderableList` hooks.
3.  **Refactor `TaskDetailView.tsx`:** Integrate these hooks into `TaskDetailView.tsx` as the first use case.
4.  **Identify Other Use Cases:** Explore other components that could benefit from these hooks.
5.  **Testing:** Write unit and integration tests for the hooks. 