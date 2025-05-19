# `useEditableEntity` Hook: Developer Guide

This guide provides comprehensive documentation for the `useEditableEntity` hook, its configuration, and usage patterns within the Clarity project.

## 1. Overview

The `useEditableEntity` hook is a powerful and configurable utility designed to manage the state and lifecycle of editable entities. It aims to simplify component logic for features involving data fetching, form management (using React Hook Form), sub-list management (including CRUD and drag-and-drop reordering), dirty state tracking, and save/cancel operations.

**Key Goals:**
*   Provide a consistent and reusable pattern for entity editing.
*   Abstract common boilerplate for data fetching, form handling, and state synchronization.
*   Integrate seamlessly with `useTaskStore` (and potentially other Zustand stores) for data persistence.
*   Support complex scenarios like parent-child data structures (e.g., Tasks with Subtasks).

## 2. Core Concepts

*   **Entity:** The primary data object being edited (e.g., a Task).
*   **Form Data:** A subset or transformation of the Entity data suitable for form inputs.
*   **Sub-Entities/Sub-List:** A collection of related child items managed under the parent Entity (e.g., Subtasks of a Task).
*   **`EntityTypeConfig`:** A configuration object passed to the hook that defines how it should behave for a specific entity type. This is the primary way to customize the hook.
*   **`UseEditableEntityResult`:** The object returned by the hook, providing state variables and handler functions to the consuming component.

## 3. API Documentation

This section details the `EntityTypeConfig` interface and the `UseEditableEntityResult` object.

### 3.1. `EntityTypeConfig<TEntityData, TFormData, TSubEntityListItemData, TSubEntityListItemFormInputData>`

The `EntityTypeConfig` object is crucial for tailoring the `useEditableEntity` hook to a specific entity.

*   `TEntityData`: The complete data structure of the entity as fetched/saved.
*   `TFormData`: The structure for the main entity's form (React Hook Form).
*   `TSubEntityListItemData`: The structure for a single item in the managed sub-entity list.
*   `TSubEntityListItemFormInputData`: Data structure for editing/creating a single sub-entity item's form.

| Property                         | Type                                                                                                | Required | Description                                                                                                                                                                                              |
| -------------------------------- | --------------------------------------------------------------------------------------------------- | -------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `entityId`                       | `string \| null \| undefined`                                                                       | Yes      | The ID of the entity to load. If `null` or `undefined`, the hook operates in "create new" mode, and `originalEntity` will be `null`.                                                                    |
| `queryHook`                      | `(id: string \| null \| undefined) => { data: TEntityData \| undefined; isLoading: boolean; ... }`      | Yes      | A function (typically a React Query custom hook) that fetches entity data. **Provided by the consumer, called by the hook.** Must return `data`, `isLoading`, `isFetching`, and `error` properties.         |
| `transformDataToForm`            | `(entityData: TEntityData \| undefined) => TFormData`                                               | Yes      | Transforms the fetched `TEntityData` (or `undefined` in create mode) into the `TFormData` structure required by React Hook Form. Ensures decoupling of API and form shapes.                               |
| `formSchema`                     | `ZodSchema<TFormData>`                                                                              | No       | Optional Zod schema for main form validation with React Hook Form. If provided, it's passed to `useForm` as the resolver.                                                                               |
| `subEntityPath`                  | `Path<TEntityData>`                                                                                 | No       | Optional path (string like 'details.items' or 'subtasks') to the sub-entity collection within `TEntityData`. If undefined, sub-list features are generally disabled or expect data via `transformSubCollectionToList`. |
| `transformSubCollectionToList`   | `(dataForSubList: any) => TSubEntityListItemData[]`                                                 | No       | Transforms raw sub-entity data into an array of `TSubEntityListItemData`. `dataForSubList` is the data from `subEntityPath` if provided, otherwise it's the entire parent `TEntityData` (or `undefined`).          |
| `subEntityListItemIdField`       | `keyof TSubEntityListItemData`                                                                      | Yes      | The property name on `TSubEntityListItemData` that serves as its unique identifier (e.g., 'id'). **Crucial for DND, CRUD operations, and React keys.**                                                     |
| `createEmptySubEntityListItem`   | `() => TSubEntityListItemData \| TSubEntityListItemFormInputData`                                   | No       | Optional function to generate a new, empty item for the sub-entity list when `addSubItem` is called without arguments or if specific default generation is needed.                                      |
| `saveHandler`                    | `(originalEntity: TEntityData \| null, currentFormData: TFormData, currentSubEntityList?: TSubEntityListItemData[]) => Promise<TEntityData \| void>` | Yes      | Asynchronous function to persist changes. Receives the original entity snapshot (`null` in create mode), current form data, and the current sub-entity list. Should return the saved entity or `void`. |
| `isDataEqual`                    | `(a: any, b: any) => boolean`                                                                       | No       | Optional custom function for deep equality checks, used for determining `isSubEntityListDirty`. Defaults to `lodash-es/isEqual`.                                                                     |
| `cloneData`                      | `<T>(data: T) => T`                                                                                 | No       | Optional custom function for deep cloning data, used for creating snapshots. Defaults to `lodash-es/cloneDeep`.                                                                                       |
| `onSaveSuccess`                  | `(savedEntity: TEntityData) => void`                                                                | No       | Callback executed after `saveHandler` successfully completes. Receives the entity returned by `saveHandler`, or the original snapshot if `saveHandler` returned `void`.                                |
| `onSaveError`                    | `(error: any) => void`                                                                              | No       | Callback executed if `saveHandler` throws an error. Receives the error object.                                                                                                                             |
| `onCancel`                       | `() => void`                                                                                        | No       | Callback executed when `handleCancel` is called, *after* the internal state (form, sub-list) has been reset to original values.                                                                         |
| `onDirtyStateChange`             | `(isDirty: boolean) => void`                                                                        | No       | Callback executed whenever the overall `isDirty` state of the entity (combined form and sub-list dirtiness) changes.                                                                                   |
| `enableSubEntityReordering`      | `boolean`                                                                                           | No       | If `true`, enables drag-and-drop reordering for the sub-entity list using `dnd-kit`. Defaults to `false`. Requires `subEntityListItemIdField` to be correctly configured.                          |

### 3.2. `UseEditableEntityResult<TEntityData, TFormData, TSubEntityListItemData>`

This is the object returned by the `useEditableEntity` hook.

| Property                      | Type                                                                 | Description                                                                                                                                                              |
| ----------------------------- | -------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| `originalEntity`              | `TEntityData \| null`                                                | A deep-cloned snapshot of the original entity data as loaded or last successfully saved. `null` in create mode or if data hasn't loaded. Stays unchanged until the next successful save or `resetState` call. |
| `isLoading`                   | `boolean`                                                            | True if the entity data is initially loading (typically reflects `queryHook`'s `isLoading` state on first load).                                                                      |
| `isFetching`                  | `boolean`                                                            | True if the entity data is currently being fetched (e.g., a refetch initiated by `queryHook`).                                                                             |
| `error`                       | `any \| null`                                                        | Stores any error object returned from `queryHook` during fetching or an error thrown by `saveHandler` during saving.                                                                     |
| `formMethods`                 | `UseFormReturn<TFormData>`                                           | The complete return object from React Hook Form's `useForm` hook (includes `register`, `control`, `handleSubmit`, `formState`, `getValues`, `reset`, etc.), for managing the main entity form. |
| `isMainFormDirty`             | `boolean`                                                            | True if the main entity form (managed by RHF) has changes compared to its data when `formMethods.reset()` was last called (typically after load or save).                                      |
| `subEntityList`               | `TSubEntityListItemData[]`                                           | The current, potentially modified, array of sub-entity list items. This list is directly mutable via `addSubItem`, `updateSubItem`, `removeSubItem`, and DND reordering.           |
| `isSubEntityListDirty`        | `boolean`                                                            | True if the `subEntityList` has changes (items added, removed, reordered, or item content changed) compared to its original state when loaded or last saved.                                |
| `addSubItem`                  | `(newItemData: TSubEntityListItemData) => void`                      | Adds a new item to the end of the `subEntityList`. Marks the sub-list as dirty.                                                                                             |
| `updateSubItem`               | `(id: string \| number, updatedDataOrFn: Partial<TSubEntityListItemData> \| ((prev: TSubEntityListItemData) => TSubEntityListItemData)) => void` | Updates an item in `subEntityList` identified by its ID (using `subEntityListItemIdField`). Can accept a partial update object or an updater function. Marks sub-list as dirty.          |
| `removeSubItem`               | `(id: string \| number) => void`                                     | Removes an item from `subEntityList` identified by its ID. Marks the sub-list as dirty.                                                                                              |
| `isDirty`                     | `boolean`                                                            | Overall dirty state: `true` if either `isMainFormDirty` or `isSubEntityListDirty` is true. Use this to enable/disable save buttons, prompt users, etc.                                  |
| `isSaving`                    | `boolean`                                                            | True if the `saveHandler` (and thus, `handleSave`) is currently executing its asynchronous operation. Useful for disabling UI during save.                                                |
| `handleSave`                  | `() => Promise<void>`                                                | Asynchronous function to trigger the save process. Internally calls `config.saveHandler` if `isDirty` is true and not already `isSaving`. Handles updating snapshots and form state on success. |
| `handleCancel`                | `() => void`                                                         | Resets the form and `subEntityList` to their original states (derived from `originalEntity`). Calls `config.onCancel` (if provided) *after* reset.                                     |
| `resetState`                  | `(newEntityData?: TEntityData) => void`                              | Resets the hook's internal state. If `newEntityData` is provided, it becomes the new `originalEntity` snapshot, and form/sub-list are updated accordingly. Otherwise, resets to the current `originalEntity` snapshot. |
| `dndContextProps`             | `Pick<CoreDndContextProps, 'sensors' \| 'onDragEnd'> \| undefined`       | Props to be spread onto a `DndContext` component if `config.enableSubEntityReordering` is true. Includes `sensors` (Pointer & Keyboard) and `onDragEnd` (the hook's internal handler). |
| `getSortableListProps`        | `() => { items: Array<TSubEntityListItemData & { id: string \| number }> }` | Function to get props for a sortable list component (e.g., one using `@dnd-kit/sortable`). Returns `subEntityList` items, ensuring each has an `id` property (stringified from `subEntityListItemIdField`). |

## 4. Usage Examples

This section will provide practical examples of how to use `useEditableEntity`.

### 4.1. Simple Entity (No Sub-List)

```typescript
// Example: Editing a User Profile (TEntityData = UserProfile, TFormData = UserProfileForm)
// Component consuming the hook:

import React from 'react'; // Import React for JSX
import { useEditableEntity, EntityTypeConfig } from '@/hooks/useEditableEntity'; // Adjust path
// import { useForm } from 'react-hook-form'; // Not directly used by component, but by the hook
import { z } from 'zod';

// Assume these types and API hooks exist
interface UserProfile {
  id: string;
  username: string;
  email: string;
  bio?: string;
}

interface UserProfileForm {
  username: string;
  email: string;
  bio?: string;
}

const userProfileSchema = z.object({
  username: z.string().min(3, { message: 'Username must be at least 3 characters.' }),
  email: z.string().email({ message: 'Invalid email address.' }),
  bio: z.string().max(200, { message: 'Bio cannot exceed 200 characters.' }).optional(),
});

// Mock API hook for fetching user profile
const useFetchUserProfile = (id: string | null | undefined) => {
  console.log(`[MockAPI] Fetching profile for ID: ${id}`);
  const [data, setData] = React.useState<UserProfile | undefined>(undefined);
  const [isLoading, setIsLoading] = React.useState(true);

  React.useEffect(() => {
    setIsLoading(true);
    if (id) {
      setTimeout(() => { // Simulate async fetch
        setData({ id, username: 'TestUser', email: 'test@example.com', bio: 'A bio for TestUser' });
        setIsLoading(false);
        console.log(`[MockAPI] Profile for ${id} fetched.`);
      }, 500);
    } else {
      setData(undefined); // For create mode
      setIsLoading(false);
      console.log(`[MockAPI] No ID provided (create mode).`);
    }
  }, [id]);

  return { data, isLoading, isFetching: isLoading, error: null }; // isFetching can be same as isLoading for simple mock
};

// Mock save function for user profile
const saveUserProfile = async (original: UserProfile | null, formData: UserProfileForm): Promise<UserProfile> => {
  console.log('[MockAPI] Attempting to save profile. Original:', original, 'Form Data:', formData);
  await new Promise(resolve => setTimeout(resolve, 700)); // Simulate async save
  
  const savedId = original?.id || `new-user-${Date.now()}`;
  const savedProfile: UserProfile = {
    id: savedId,
    username: formData.username,
    email: formData.email,
    bio: formData.bio,
  };
  console.log('[MockAPI] Profile saved successfully:', savedProfile);
  return savedProfile;
};

const UserProfileEditor: React.FC<{ userId: string | null }> = ({ userId }) => {
  const profileConfig: EntityTypeConfig<UserProfile, UserProfileForm, any> = React.useMemo(() => ({
    entityId: userId,
    queryHook: useFetchUserProfile,
    transformDataToForm: (data) => ({
      username: data?.username || '',
      email: data?.email || '',
      bio: data?.bio || '',
    }),
    formSchema: userProfileSchema,
    saveHandler: saveUserProfile,
    // Note: subEntityListItemIdField is required by EntityTypeConfig type, 
    // even if not using sub-entities. Provide a dummy or refine types for non-list scenarios.
    subEntityListItemIdField: 'id' as any, // Using 'as any' or a more specific dummy type key
    onSaveSuccess: (savedProfile) => {
      console.log('UserProfileEditor: Save successful!', savedProfile);
      // Potentially close modal, show notification, etc.
    },
    onSaveError: (error) => {
        console.error('UserProfileEditor: Save failed!', error);
    },
    onCancel: () => {
      console.log('UserProfileEditor: Edit cancelled by user.');
      // Potentially close modal
    },
  }), [userId]);

  const {
    formMethods,
    handleSave,
    handleCancel,
    isDirty,
    isLoading,
    isSaving, // Added isSaving for button state
    error,
  } = useEditableEntity(profileConfig);

  if (isLoading) return <p>Loading profile...</p>;
  if (error) return <p>Error loading profile: {error.message || 'Unknown error'}</p>;

  return (
    <form onSubmit={formMethods.handleSubmit(handleSave)} noValidate>
      <div>
        <label htmlFor="username">Username:</label>
        <input id="username" {...formMethods.register('username')} placeholder="Username" />
        {formMethods.formState.errors.username && 
          <p style={{ color: 'red' }}>{formMethods.formState.errors.username.message}</p>}
      </div>
      
      <div>
        <label htmlFor="email">Email:</label>
        <input id="email" type="email" {...formMethods.register('email')} placeholder="Email" />
        {formMethods.formState.errors.email && 
          <p style={{ color: 'red' }}>{formMethods.formState.errors.email.message}</p>}
      </div>

      <div>
        <label htmlFor="bio">Bio:</label>
        <textarea id="bio" {...formMethods.register('bio')} placeholder="Tell us about yourself..." />
        {formMethods.formState.errors.bio && 
          <p style={{ color: 'red' }}>{formMethods.formState.errors.bio.message}</p>}
      </div>

      <div style={{ marginTop: '20px' }}>
        <button type="submit" disabled={!isDirty || isSaving || isLoading}>
          {isSaving ? 'Saving...' : 'Save Profile'}
        </button>
        <button type="button" onClick={handleCancel} disabled={isSaving || isLoading}>
          Cancel
        </button>
      </div>
      {isDirty && <p style={{ fontStyle: 'italic' }}>You have unsaved changes.</p>}
    </form>
  );
};

export default UserProfileEditor; // Example component export
```

### 4.2. Complex Entity (With Sub-List) Example

This example demonstrates editing a `Task` entity which has a sub-list of `Subtask` items. It will showcase fetching, form handling for the parent task, and CRUD + reordering for subtasks.

```typescript
// Example: Editing a Task with Subtasks
// Component consuming the hook:

import React from 'react'; // Import React for JSX
import { 
  useEditableEntity, 
  EntityTypeConfig, 
  UseEditableEntityResult // Ensure this is imported if used directly for typing
} from '@/hooks/useEditableEntity'; // Adjust path as needed
import { DndContext, closestCenter, KeyboardSensor, PointerSensor, useSensor, useSensors } from '@dnd-kit/core';
import { SortableContext, sortableKeyboardCoordinates, verticalListSortingStrategy, useSortable } from '@dnd-kit/sortable';
import { CSS } from '@dnd-kit/utilities';
import { z } from 'zod';

// --- Type Definitions ---
interface Subtask {
  id: string;
  title: string;
  completed: boolean;
  order: number; // Assuming order is managed for DND
}

interface Task {
  id: string;
  title: string;
  description?: string;
  priority: 'low' | 'medium' | 'high';
  subtasks: Subtask[]; // Subtasks are part of the main Task entity
}

interface TaskForm {
  title: string;
  description?: string;
  priority: 'low' | 'medium' | 'high';
}

const taskFormSchema = z.object({
  title: z.string().min(1, "Title is required"),
  description: z.string().optional(),
  priority: z.enum(['low', 'medium', 'high']),
});

// --- Mock API Hooks & Functions ---

// Mock data store (simplified, in a real app this might be Zustand or a backend)
let mockTasksDb: Task[] = [
  { 
    id: 'task-1', 
    title: 'Grocery Shopping', 
    priority: 'medium', 
    subtasks: [
      { id: 'sub-1', title: 'Buy milk', completed: false, order: 0 },
      { id: 'sub-2', title: 'Buy eggs', completed: true, order: 1 },
      { id: 'sub-3', title: 'Buy bread', completed: false, order: 2 },
    ]
  },
  { id: 'task-2', title: 'Project Alpha', priority: 'high', subtasks: [] },
];

const useFetchTask = (id: string | null | undefined) => {
  console.log(`[MockTaskAPI] Fetching task for ID: ${id}`);
  const [data, setData] = React.useState<Task | undefined>(undefined);
  const [isLoading, setIsLoading] = React.useState(true);

  React.useEffect(() => {
    setIsLoading(true);
    if (id) {
      const foundTask = mockTasksDb.find(t => t.id === id);
      setTimeout(() => { // Simulate async fetch
        setData(foundTask ? { ...foundTask, subtasks: [...(foundTask.subtasks || [])] } : undefined); // Deep copy for safety
        setIsLoading(false);
        console.log(`[MockTaskAPI] Task for ${id} fetched:`, foundTask);
      }, 500);
    } else {
      setData(undefined); // Create mode
      setIsLoading(false);
      console.log(`[MockTaskAPI] No ID provided (create mode).`);
    }
  }, [id]);

  return { data, isLoading, isFetching: isLoading, error: null };
};

const saveTask = async (
  originalTask: Task | null, 
  formData: TaskForm, 
  currentSubtaskList?: Subtask[]
): Promise<Task> => {
  console.log('[MockTaskAPI] Attempting to save task. Original:', originalTask, 'Form Data:', formData, 'Subtasks:', currentSubtaskList);
  await new Promise(resolve => setTimeout(resolve, 700)); // Simulate async save

  const taskId = originalTask?.id || `task-${Date.now()}`;
  const updatedOrNewTask: Task = {
    id: taskId,
    ...formData,
    subtasks: currentSubtaskList 
      ? currentSubtaskList.map((st, index) => ({ ...st, order: index })) // Ensure order is updated
      : originalTask?.subtasks || [], // Keep original subtasks if currentSubtaskList is not provided (should not happen with proper config)
  };

  if (originalTask) {
    mockTasksDb = mockTasksDb.map(t => t.id === taskId ? updatedOrNewTask : t);
  } else {
    mockTasksDb.push(updatedOrNewTask);
  }
  console.log('[MockTaskAPI] Task saved successfully:', updatedOrNewTask);
  return { ...updatedOrNewTask }; // Return a copy
};

// --- Sortable Subtask Item (for DND) ---
interface SortableSubtaskItemProps {
  subtask: Subtask;
  onUpdate: (id: string, data: Partial<Subtask>) => void;
  onRemove: (id: string) => void;
}

const SortableSubtaskItem: React.FC<SortableSubtaskItemProps> = ({ subtask, onUpdate, onRemove }) => {
  const {
    attributes,
    listeners,
    setNodeRef,
    transform,
    transition,
    isDragging,
  } = useSortable({ id: subtask.id });

  const style = {
    transform: CSS.Transform.toString(transform),
    transition,
    opacity: isDragging ? 0.5 : 1,
    padding: '8px',
    border: '1px solid #ccc',
    marginBottom: '4px',
    backgroundColor: '#f9f9f9',
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
  };

  return (
    <div ref={setNodeRef} style={style} {...attributes} {...listeners}>
      <input
        type="checkbox"
        checked={subtask.completed}
        onChange={(e) => onUpdate(subtask.id, { completed: e.target.checked })}
      />
      <span style={{ textDecoration: subtask.completed ? 'line-through' : 'none', marginLeft: '8px', flexGrow: 1 }}>
        {subtask.title}
      </span>
      {/* Example: Basic inline edit for title - in reality, you'd use a controlled input or a modal */}
      <button onClick={() => {
        const newTitle = prompt("New title:", subtask.title);
        if (newTitle !== null) onUpdate(subtask.id, { title: newTitle });
      }} style={{marginRight: '5px'}}>Rename</button>
      <button onClick={() => onRemove(subtask.id)}>Remove</button>
    </div>
  );
};


// --- Main Task Editor Component ---
const TaskEditor: React.FC<{ taskId: string | null }> = ({ taskId }) => {
  const taskConfig: EntityTypeConfig<Task, TaskForm, Subtask> = React.useMemo(() => ({
    entityId: taskId,
    queryHook: useFetchTask,
    transformDataToForm: (data) => ({
      title: data?.title || '',
      description: data?.description || '',
      priority: data?.priority || 'medium',
    }),
    formSchema: taskFormSchema,
    subEntityPath: 'subtasks', // Path to the subtasks array within the Task entity
    transformSubCollectionToList: (subtasksArray) => {
      // Ensure subtasks are sorted by 'order' if it exists, or just return as is
      // The hook itself will handle DND reordering if enabled
      return (subtasksArray || []).sort((a: Subtask, b: Subtask) => (a.order || 0) - (b.order || 0));
    },
    subEntityListItemIdField: 'id', // 'id' field on Subtask objects
    createEmptySubEntityListItem: () => ({ // For the "Add Subtask" button
      id: `sub-${Date.now()}`,
      title: 'New Subtask',
      completed: false,
      order: 0, // Will be re-calculated based on list length or actual order on save
    }),
    saveHandler: saveTask,
    enableSubEntityReordering: true, // Enable DND for subtasks
    onSaveSuccess: (savedTask) => {
      console.log('TaskEditor: Save successful!', savedTask);
      // alert('Task saved!'); // Example notification
      // Potentially close modal, navigate, etc.
    },
    onSaveError: (error) => {
      console.error('TaskEditor: Save failed!', error);
      alert('Failed to save task.');
    },
    onCancel: () => {
      console.log('TaskEditor: Edit cancelled by user.');
      // alert('Changes discarded.');
      // Potentially close modal
    },
    onDirtyStateChange: (isDirty) => {
      console.log(`TaskEditor: Dirty state changed to: ${isDirty}`);
    }
  }), [taskId]);

  const {
    formMethods,
    handleSave,
    handleCancel,
    isDirty,
    isLoading,
    isSaving,
    error,
    subEntityList,
    addSubItem,
    updateSubItem,
    removeSubItem,
    dndContextProps, // For DND
    getSortableListProps, // For DND
  } = useEditableEntity(taskConfig);

  // DND Sensors
  const sensors = useSensors(
    useSensor(PointerSensor),
    useSensor(KeyboardSensor, {
      coordinateGetter: sortableKeyboardCoordinates,
    })
  );

  if (isLoading) return <p>Loading task...</p>;
  if (error) return <p>Error loading task: {(error as any)?.message || 'Unknown error'}</p>;

  const sortableItems = getSortableListProps ? getSortableListProps().items : [];

  return (
    <div>
      <form onSubmit={formMethods.handleSubmit(handleSave)} noValidate>
        <h3>Task Details</h3>
        <div>
          <label htmlFor="taskTitle">Title:</label>
          <input id="taskTitle" {...formMethods.register('title')} placeholder="Task Title" />
          {formMethods.formState.errors.title && 
            <p style={{ color: 'red' }}>{formMethods.formState.errors.title.message}</p>}
        </div>
        <div>
          <label htmlFor="taskDescription">Description:</label>
          <textarea id="taskDescription" {...formMethods.register('description')} placeholder="Task Description" />
          {formMethods.formState.errors.description && 
            <p style={{ color: 'red' }}>{formMethods.formState.errors.description.message}</p>}
        </div>
        <div>
          <label htmlFor="taskPriority">Priority:</label>
          <select id="taskPriority" {...formMethods.register('priority')}>
            <option value="low">Low</option>
            <option value="medium">Medium</option>
            <option value="high">High</option>
          </select>
          {formMethods.formState.errors.priority && 
            <p style={{ color: 'red' }}>{formMethods.formState.errors.priority.message}</p>}
        </div>

        <div style={{ marginTop: '20px' }}>
          <button type="submit" disabled={!isDirty || isSaving || isLoading}>
            {isSaving ? 'Saving Task...' : 'Save Task'}
          </button>
          <button type="button" onClick={handleCancel} disabled={isSaving || isLoading} style={{ marginLeft: '10px' }}>
            Cancel
          </button>
        </div>
        {isDirty && <p style={{ fontStyle: 'italic', color: 'orange' }}>You have unsaved changes.</p>}
      </form>

      <div style={{ marginTop: '30px' }}>
        <h3>Subtasks</h3>
        {dndContextProps && (
          <DndContext
            sensors={sensors}
            collisionDetection={closestCenter}
            onDragEnd={dndContextProps.onDragEnd} // Use onDragEnd from the hook
          >
            <SortableContext
              items={sortableItems} // Pass items from getSortableListProps
              strategy={verticalListSortingStrategy}
            >
              {subEntityList.map((subtask) => (
                <SortableSubtaskItem
                  key={subtask.id}
                  subtask={subtask}
                  onUpdate={updateSubItem} // Pass hook's updateSubItem
                  onRemove={removeSubItem} // Pass hook's removeSubItem
                />
              ))}
            </SortableContext>
          </DndContext>
        )}
        {!dndContextProps && subEntityList.length > 0 && ( // Fallback if DND is not enabled/configured
           subEntityList.map((subtask) => (
            <div key={subtask.id} style={{padding: '8px', border: '1px solid #eee', marginBottom: '4px'}}>
                {subtask.title} ({subtask.completed ? 'Completed' : 'Pending'})
                {/* Add non-DND edit/remove buttons here if needed */}
            </div>
           ))
        )}

        {subEntityList.length === 0 && <p>No subtasks yet.</p>}

        <button 
          type="button" 
          onClick={() => addSubItem(taskConfig.createEmptySubEntityListItem!())} 
          style={{ marginTop: '10px' }}
          disabled={isSaving || isLoading}
        >
          Add Subtask
        </button>
      </div>
    </div>
  );
};

export default TaskEditor; // Example component export
```

This example includes:
*   Type definitions for `Task`, `Subtask`, and `TaskForm`.
*   Mock API functions (`useFetchTask`, `saveTask`) to simulate data operations and persistence.
*   A `SortableSubtaskItem` component to render each subtask, enabling drag-and-drop using `dnd-kit`.
*   The main `TaskEditor` component that:
    *   Configures `EntityTypeConfig` for tasks, specifying `subEntityPath`, `transformSubCollectionToList`, `subEntityListItemIdField`, `createEmptySubEntityListItem`, and `enableSubEntityReordering`.
    *   Uses `useEditableEntity` to get form methods, list management functions, DND props, and state.
    *   Renders the main task form.
    *   Renders the subtask list within a `DndContext` and `SortableContext` if DND is enabled.
    *   Provides buttons for adding subtasks, saving the task, and canceling edits.

This comprehensive example should provide a good starting point for implementing complex entity editing with sub-lists using the `useEditableEntity` hook.

## 5. Best Practices & Patterns

*   **Configuration is Key:** Spend time defining a comprehensive `EntityTypeConfig`. This is where most of the customization happens.
*   **Leverage React Query for `queryHook`:** Use React Query (or similar data fetching libraries) to handle caching, refetching, and server state synchronization effectively. The `queryHook` should be a stable function reference if possible (e.g., defined outside the component or memoized).
*   **Data Transformation:**
    *   `transformDataToForm` is crucial for decoupling your API entity structure from your form structure.
    *   `transformSubCollectionToList` allows flexibility in how sub-entities are stored in the parent and how they are presented as a flat list.
*   **`saveHandler` Responsibilities:**
    *   The `saveHandler` is responsible for all data persistence logic (e.g., calling API endpoints, updating Zustand stores).
    *   It should calculate deltas if your backend requires only changed data.
    *   Returning the updated entity from `saveHandler` allows the hook to update its internal snapshot correctly. If `void` is returned, the hook assumes the caller (or `queryHook` refetch) will update the source of truth.
*   **Idempotency and Uniqueness:** Ensure `subEntityListItemIdField` points to a truly unique and stable ID for each sub-list item, especially when `enableSubEntityReordering` is true.
*   **Memoization:** For complex configurations or transformations within your component before passing them to `EntityTypeConfig`, use `useMemo` or `useCallback` to stabilize references and prevent unnecessary re-initializations of the hook.
*   **Error Handling:** Provide user-friendly feedback based on the `error` state and utilize `onSaveError`.
*   **State Updates & Callbacks:** Be mindful that `onSaveSuccess`, `onCancel`, and `onDirtyStateChange` are callbacks. If they close over state from your component, ensure they are stable or correctly handle closures.

## 6. Advanced Scenarios & Considerations

*   **Create Mode (`entityId` is null/undefined):**
    *   `queryHook` will likely return `data: undefined`.
    *   `transformDataToForm(undefined)` should return the default state for a new form.
    *   `originalEntitySnapshot` will be `null`. `saveHandler` will receive `null` as the first argument.
*   **Read-Only Views:** While primarily for editing, the hook can be used to display data by simply not providing save/edit interaction UI elements. The form could be set to read-only.
*   **Optimistic Updates:** Currently, optimistic updates are not built into the hook itself. They would typically be handled within your `saveHandler` (if it updates a local store like Zustand optimistically) or within your `queryHook` if using React Query's optimistic update features.
*   **Server-Side Validation Errors:** `saveHandler` should catch errors from the server. If these are validation errors pertaining to specific fields, you might need a mechanism to map them back to React Hook Form errors using `formMethods.setError()`. This is an advanced pattern not directly facilitated by the hook but can be implemented in the `saveHandler` or `onSaveError`.

## 7. Future Enhancements (Potential)

*   More built-in support for optimistic updates.
*   Helper utilities for common `saveHandler` patterns (e.g., diffing).
*   More granular control over DND behavior.
*   Refined typing for scenarios without sub-entities to make `subEntityListItemIdField` truly optional.

---

This guide will be updated as the hook evolves and new patterns emerge. 