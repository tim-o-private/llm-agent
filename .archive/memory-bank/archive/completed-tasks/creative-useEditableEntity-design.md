# Creative Design: `useEditableEntity` Hook

**Task:** Task 9 (Clarity UI) - Architect and Implement `useEditableEntity` Hook & Refactor `TaskDetailView`

**Date:** (Current Date)

## 1. Introduction & Goal

The `useEditableEntity` hook aims to provide a comprehensive, reusable, and configurable solution for managing the state and lifecycle of editable entities within the Clarity UI. It will abstract common patterns such as data fetching, form management (integrating with React Hook Form), sub-entity list management (including CRUD and reordering), dirty state detection, and save/cancel operations.

The primary goal is to simplify component logic (like in `TaskDetailView.tsx`), reduce boilerplate, improve maintainability, and establish a robust and predictable pattern for developing features that involve editing complex data structures.

This hook is intended to supersede the previous combination of `useObjectEditManager`, `useReorderableList`, `useTaskDetailStateManager`, and `useEntityEditManager` for such scenarios.

## 2. Core Requirements

The hook must:
1.  Fetch an entity's data based on a provided ID.
2.  Initialize and manage form state for the main entity using React Hook Form.
3.  Optionally manage a list of sub-entities, supporting:
    *   Display.
    *   Addition of new sub-entities.
    *   Updating existing sub-entities.
    *   Removal of sub-entities.
    *   Reordering of sub-entities (integrating with `dnd-kit`).
4.  Accurately track "dirty" state:
    *   Changes in the main entity's form.
    *   Changes to the list of sub-entities (add, remove, reorder, content change).
5.  Provide a `save` mechanism that:
    *   Receives the original entity state, current form state, and current sub-entity state.
    *   Delegates the actual persistence logic (delta calculation, API calls) to a `saveHandler` function provided in its configuration.
6.  Provide a `cancel` or `reset` mechanism to revert changes to the last saved state.
7.  Expose loading states (initial fetch, saving) and error states.
8.  Be highly configurable via an `EntityTypeConfig` object to adapt to different entity structures and backend interactions.
9.  Be well-typed using TypeScript generics.

## 3. API Definition

### 3.1. Input: `EntityTypeConfig<TEntityData, TFormData, TSubEntityData, TSubEntityListItemData>`

\`\`\`typescript
import { UseFormReturn, FieldValues, Path } from 'react-hook-form';
import { ZodSchema } from 'zod';
import { SensorDescriptor, DragEndEvent } from '@dnd-kit/core';

// TEntityData: The complete data structure of the entity as fetched from the backend/store.
// TFormData: The subset of TEntityData (or a transformation of it) used for the main entity's form (React Hook Form).
// TSubEntityCollectionData: The raw data structure for the collection of sub-entities as part of TEntityData (e.g., Task['subtasks']).
// TSubEntityListItemData: The data structure for a single item within the sub-entity list. This is what the hook will primarily manage.
// TSubEntityListItemFormInputData: Data structure for editing/creating a single sub-entity item (if forms are used for sub-items).

export interface EntityTypeConfig<
  TEntityData,
  TFormData extends FieldValues,
  TSubEntityCollectionData = TSubEntityListItemData[], // Default to array of list items
  TSubEntityListItemData = any, // Type for individual items in the managed list
  TSubEntityListItemFormInputData extends FieldValues = FieldValues, // For forms related to sub-items
> {
  // --- Entity Identification & Fetching ---
  entityId: string | null | undefined; // ID for fetching existing, or null/undefined for new.
  queryHook: (id: string | null | undefined) => { // Allow null id for create scenarios
    data: TEntityData | undefined;
    isLoading: boolean;
    isFetching: boolean; // For background fetching
    error: any;
    // Potentially refetch/invalidate functions if needed directly by the hook
  };

  // --- Main Entity Form Management (React Hook Form) ---
  // Converts the complete fetched entity data to the data structure for the main RHF form.
  transformDataToForm: (entityData: TEntityData) => TFormData;
  // Optional Zod schema for RHF validation.
  formSchema?: ZodSchema<TFormData>;

  // --- Sub-Entity List Management (Optional) ---
  // Path within TEntityData to access the collection of sub-entities (e.g., 'subtasks').
  subEntityPath?: Path<TEntityData>; 
  // Transforms the raw sub-entity collection from TEntityData into the list of TSubEntityListItemData managed by the hook.
  transformSubCollectionToList?: (subCollection: TSubEntityCollectionData | undefined) => TSubEntityListItemData[];
  // Unique ID field for items in the sub-entity list (for dnd-kit and list operations).
  subEntityListItemIdField: keyof TSubEntityListItemData;
  // Function to create an empty/default new sub-entity list item (can be form data or final data).
  createEmptySubEntityListItem?: () => TSubEntityListItemData | TSubEntityListItemFormInputData;
  // Optional: if sub-items are complex and have their own forms managed elsewhere,
  // this can help integrate their dirty state.
  // isSubEntityItemDirty?: (originalItem: TSubEntityListItemData, currentItem: TSubEntityListItemData) => boolean;
  
  // --- Data Persistence ---
  // The core save function. Receives all necessary data to compute deltas and persist.
  saveHandler: (
    originalEntity: TEntityData | null, // Snapshot of the entity when editing started or last save
    currentFormData: TFormData,
    currentSubEntityList: TSubEntityListItemData[] | undefined, // Current state of the sub-entity list
  ) => Promise<TEntityData | void>; // Returns the saved entity or void. Allows updating internal state post-save.

  // --- Utilities (Optional, with sensible defaults) ---
  isDataEqual?: (a: TEntityData | TFormData | TSubEntityListItemData, b: TEntityData | TFormData | TSubEntityListItemData) => boolean;
  cloneData?: <T>(data: T) => T;

  // --- Callbacks (Optional) ---
  onSaveSuccess?: (savedEntity: TEntityData) => void;
  onSaveError?: (error: any) => void;
  onCancel?: () => void; // Called after form reset on cancel.
  onDirtyStateChange?: (isDirty: boolean) => void; // If component needs to know about dirty state changes.

  // --- Configuration for dnd-kit (if sub-entities are reorderable) ---
  enableSubEntityReordering?: boolean; 
  // dndSensors?: SensorDescriptor[]; // Allow custom sensors
}
\`\`\`
### 3.2. Output: `UseEditableEntityResult<TEntityData, TFormData, TSubEntityListItemData>`

\`\`\`typescript
import { UseFormReturn, FieldValues } from 'react-hook-form';
import { DndContextProps } from '@dnd-kit/core'; // Assuming a type like this exists or can be made
import { SortableListProps } from 'path-to-your-sortable-list-component-types'; // Placeholder

export interface UseEditableEntityResult<
  TEntityData,
  TFormData extends FieldValues,
  TSubEntityListItemData = any,
> {
  // --- Data State ---
  originalEntity: TEntityData | null; // Snapshot of the entity when editing started or last successful save.
  currentEntityDataForForm: TFormData | undefined; // The data currently in the form.
  isLoading: boolean; // True during initial data fetch.
  isFetching: boolean; // True during background refetches.
  error: any | null; // Error from queryHook or save operation.

  // --- Form Management (React Hook Form) ---
  // The RHF instance for the main entity's form.
  formMethods: UseFormReturn<TFormData>; 
  // Convenience alias for formMethods.formState.isDirty related to the main form.
  isMainFormDirty: boolean; 

  // --- Sub-Entity List Management ---
  // The current list of sub-entity items.
  subEntityList: TSubEntityListItemData[]; 
  // Indicates if the sub-entity list has changed (items added, removed, reordered, or content of an item changed).
  isSubEntityListDirty: boolean; 
  // Functions to manipulate the sub-entity list.
  addSubItem: (newItemData: TSubEntityListItemData) => void;
  updateSubItem: (id: string | number, updatedItemData: Partial<TSubEntityListItemData> | ((prev: TSubEntityListItemData) => TSubEntityListItemData)) => void;
  removeSubItem: (id: string | number) => void;
  // (Reordering is handled via dnd-kit props below if enabled)

  // --- Overall Status & Actions ---
  // True if the main form is dirty OR the sub-entity list is dirty.
  isDirty: boolean; 
  isSaving: boolean; // True while the saveHandler is executing.
  
  // Triggers the save process using the configured saveHandler.
  handleSave: () => Promise<void>; 
  // Resets form and sub-entity list to their original/last saved state. Calls onCancel.
  handleCancel: () => void; 
  // Resets the form and state, optionally to new data (e.g., after a create operation).
  resetState: (newEntityData?: TEntityData) => void; 

  // --- dnd-kit Integration for Sub-Entity Reordering (if enabled) ---
  dndContextProps?: Pick<DndContextProps, 'sensors' | 'onDragEnd' | 'modifiers' | 'collisionDetection'>; // Expose necessary props for DndContext
  // Props to be passed to a sortable list component (e.g., one built with dnd-kit's useSortable).
  // It's assumed the component using this hook will render its own SortableList.
  // The hook provides the necessary state and handlers.
  // The 'id' property on items must match subEntityListItemIdField.
  getSortableListProps: () => { 
    items: Array<TSubEntityListItemData & { id: string | number }>; // Ensure items have an id for dnd-kit
    // any other props your sortable list component might need from the hook
  };
}
\`\`\`

## 4. Architectural Design (Internal Workings)

### 4.1. State Management

The hook will internally manage several pieces of state:
*   `originalEntitySnapshot`: Stores a deep clone of the entity data as it was when editing began (or after the last successful save). Used for dirty checking and resetting.
*   `internalSubEntityList`: The current state of the sub-entity list, managed by the hook.
*   `isSaving`, `isLoading`, `isFetching`, `error`: Standard async operation states.
*   React Hook Form instance (`formMethods`): Manages the main entity form state.

### 4.2. Data Flow & Effects

1.  **Initialization & Data Fetching:**
    *   On mount or `entityId` change, if `entityId` is provided, `queryHook` is called.
    *   `isLoading`/`isFetching`/`error` are updated based on `queryHook`'s status.
    *   When data is fetched successfully:
        *   `originalEntitySnapshot` is set with a deep clone of the fetched data.
        *   The RHF form is reset with `transformDataToForm(fetchedData)`.
        *   `internalSubEntityList` is initialized using `transformSubCollectionToList(fetchedData[subEntityPath])`.
        *   If `entityId` is null/undefined (create mode):
            *   `originalEntitySnapshot` remains null.
            *   RHF form is initialized with `transformDataToForm(createEmptyEntity())` (config needs `createEmptyEntity` or similar for `TEntityData`).
            *   `internalSubEntityList` is initialized as empty or with default items.

2.  **Dirty Checking (`isDirty` state):**
    *   Calculated reactively based on:
        *   `formMethods.formState.isDirty` (for the main form).
        *   Comparison of `internalSubEntityList` against the sub-entities derived from `originalEntitySnapshot`. This involves checking for added/removed items, reordering, and deep comparison of individual item content (potentially using `isSubEntityItemDirty` if provided, or a generic deep equal).
    *   A `useEffect` will monitor these dependencies and update the exposed `isDirty` state. `onDirtyStateChange` callback is invoked.

3.  **Main Form Interactions:**
    *   Handled by the RHF instance (`formMethods`) exposed by the hook. The consuming component uses these methods to register inputs, etc.

4.  **Sub-Entity List Operations (`addSubItem`, `updateSubItem`, `removeSubItem`, `dndContextProps.onDragEnd`):**
    *   These functions update the `internalSubEntityList` state.
    *   Each modification will trigger a re-evaluation of `isSubEntityListDirty` and consequently the overall `isDirty` state.

5.  **Save Operation (`handleSave`):**
    *   Sets `isSaving` to true.
    *   Retrieves current form values using `formMethods.getValues()`.
    *   Calls the configured `saveHandler` with `originalEntitySnapshot`, current form values, and `internalSubEntityList`.
    *   On successful save (promise resolves):
        *   If `saveHandler` returns the updated entity, update `originalEntitySnapshot` with the new entity data.
        *   Reset the RHF form with `transformDataToForm(savedEntityData)`.
        *   Re-initialize `internalSubEntityList` from the saved entity data. This effectively resets the dirty state.
        *   Call `onSaveSuccess` callback.
    *   On save error (promise rejects):
        *   Set `error` state.
        *   Call `onSaveError` callback.
    *   Finally, sets `isSaving` to false.

6.  **Cancel Operation (`handleCancel`):**
    *   Resets RHF form to `transformDataToForm(originalEntitySnapshot)` (or empty state if `originalEntitySnapshot` is null).
    *   Resets `internalSubEntityList` to the state derived from `originalEntitySnapshot`.
    *   Calls `onCancel` callback.

7.  **Reset State (`resetState`):**
    *   Similar to cancel, but can optionally take `newEntityData` to reset to a new baseline (e.g., after a successful creation where the backend returns the full new entity).

### 4.3. Key Internal Hooks and Logic

*   `useEffect` for fetching data when `entityId` changes.
*   `useEffect` for calculating `isDirty` based on RHF's `isDirty` and `internalSubEntityList` changes.
*   `useForm` from React Hook Form to manage the main entity's form.
*   `useState` for `originalEntitySnapshot`, `internalSubEntityList`, `isSaving`, etc.
*   `useCallback` for memoizing handler functions exposed by the hook.
*   `useMemo` for memoizing derived data where appropriate (e.g., the `items` prop for `getSortableListProps`).
*   If `enableSubEntityReordering` is true, `useSensors` and `DragEndEvent` handler logic from `dnd-kit` will be used to manage sub-entity reordering.

## 5. Open Questions & Considerations

1.  **Granularity of Sub-Entity Dirty Checking:** How deep should sub-entity dirty checking go? If a sub-entity is a complex object, should the hook be responsible for its internal dirty state, or should that be delegated (e.g., if each sub-entity item uses its own RHF form)?
    *   **Decision:** For now, the hook will perform a deep comparison of sub-entity items if `isSubEntityItemDirty` is not provided. This keeps the initial API simpler. For very complex sub-items, they might use their own instance of `useEditableEntity` managed by a parent component.
2.  **Creation Flow:** How is a "new" entity handled? `entityId` would be `null`/`undefined`. The `queryHook` should handle this gracefully (e.g., not fetch, return `undefined` data). `transformDataToForm` might need to handle `undefined` input to produce default form values. `saveHandler` would then likely perform a create operation.
    *   **Decision:** `queryHook` signature updated to accept `null | undefined`. `EntityTypeConfig` will need to provide a way to get initial `TFormData` for new entities, likely via `transformDataToForm` handling `undefined` or a new `createEmptyFormData` config option.
3.  **Error Handling:** Define how errors from `queryHook` and `saveHandler` are exposed and managed.
    *   **Decision:** A single `error` state in the result will hold the most recent error.
4.  **Optimistic Updates:** Should the hook support optimistic updates for sub-entity operations or save operations?
    *   **Decision:** Defer optimistic updates for the initial version to keep complexity down. The `saveHandler` can implement its own optimistic logic if needed, and the hook will reset based on the data returned by `saveHandler`.
5.  **Dependencies and Memoization:** Careful attention to `useCallback`, `useMemo`, and `useEffect` dependencies will be critical to prevent unnecessary re-renders and ensure stability, especially given the complexity.
6.  **Default `isDataEqual` and `cloneData`:** Provide robust default implementations (e.g., using `lodash/isEqual` and `lodash/cloneDeep` or a similar library like `rfdc`).

## 6. Integration with `TaskDetailView.tsx` (High-Level)

*   `TaskDetailView` will instantiate `useEditableEntity` with a specific `EntityTypeConfig` for `Task` entities.
*   `queryHook` will use `useGetTaskByIdQuery` (or similar from `useTaskStore` selectors if data is already in Zustand).
*   `transformDataToForm` will map `Task` data to `TaskFormData` for RHF.
*   `subEntityPath` will be `'subtasks'`. `transformSubCollectionToList` will map `Task['subtasks']` to a list of `SubtaskListItemData`. `subEntityListItemIdField` will be `'id'`.
*   `saveHandler` will encapsulate the logic currently in `TaskDetailView`'s save function (which computes deltas and calls `useTaskStore` actions).
*   The JSX in `TaskDetailView` will be refactored to use `formMethods` from the hook for parent task fields, and `subEntityList` + manipulation functions for subtasks.

This hook aims to be the primary driver of state and interaction logic within `TaskDetailView`, making the component itself much leaner. 