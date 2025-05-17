# State Management Design Document

## Current State Analysis

### Current Implementation Patterns

The current application uses a mix of state management approaches:

1. **React Query for API Interactions**
   - Located in `webApp/src/api/hooks/useTaskHooks.ts`
   - Handles all CRUD operations with Supabase
   - Provides data fetching, mutations, and cache invalidation

2. **Zustand for UI State**
   - Located in `webApp/src/stores/useTaskViewStore.ts`
   - Currently focused on UI-related state (selections, open modals, etc.)
   - Recently refactored to remove actual task data storage

3. **Component Local State**
   - Individual components maintain their own local state
   - Examples: form data in `TaskDetailView.tsx`, edit state in `SubtaskItem.tsx`
   - Creates inconsistency across component implementations

### Issues with Current Approach

1. **Inconsistent State Management**
   - Different components use different approaches to state
   - Direct API calls mixed with cached data
   - Manual state synchronization becomes complex

2. **No Offline Capability**
   - Changes require immediate API calls
   - No local-first approach with eventual sync

3. **Performance Concerns**
   - Frequent API calls may impact performance
   - Lack of optimistic updates in some components

## Proposed Architecture: Unified Zustand Store with Eventual Sync

### Core Principles

1. **Entity-Centric Stores**
   - Create individual stores per entity type (tasks, subtasks, etc.)
   - Maintain complete, normalized data models

2. **Local-First with Eventual Sync**
   - Local changes applied immediately to Zustand store
   - Background synchronization to database every 5-10 seconds
   - Conflict resolution strategy defined per entity type

3. **Optimistic Updates by Default**
   - UI updates immediately on local changes
   - Rollback mechanisms for failed syncs

4. **React Query for Initial Data Loading**
   - Continue using React Query for initial data fetching
   - After initial load, Zustand becomes source of truth

### Implementation Pattern

#### 1. Store Structure

```typescript
// Example for Tasks
interface TaskState {
  // Data
  tasks: Record<string, Task>;
  isLoading: boolean;
  error: Error | null;
  
  // Sync state
  pendingChanges: Record<string, { action: 'create' | 'update' | 'delete', data: Partial<Task> }>;
  lastSyncTime: number;
  isSyncing: boolean;
  
  // Actions
  fetchTasks: () => Promise<void>;
  createTask: (task: Omit<NewTaskData, 'user_id'>) => Promise<string>; // Returns local ID
  updateTask: (id: string, updates: Partial<Task>) => void;
  deleteTask: (id: string) => void;
  syncWithServer: () => Promise<void>;
}
```

#### 2. Sync Implementation

```typescript
// Pseudo-code for sync implementation
const syncWithServer = async () => {
  if (isSyncing || Object.keys(pendingChanges).length === 0) return;
  
  set({ isSyncing: true });
  
  try {
    // Process creates, updates, deletes in batch if possible
    for (const [id, change] of Object.entries(pendingChanges)) {
      if (change.action === 'create') {
        // Handle create...
      } else if (change.action === 'update') {
        // Handle update...
      } else if (change.action === 'delete') {
        // Handle delete...
      }
    }
    
    // Clear processed changes
    set({ 
      pendingChanges: {}, 
      lastSyncTime: Date.now(),
      isSyncing: false 
    });
  } catch (error) {
    set({ 
      error, 
      isSyncing: false 
    });
    // Could implement retry logic here
  }
};
```

#### 3. Automatic Sync Interval

```typescript
// In store initialization
useEffect(() => {
  const syncInterval = setInterval(() => {
    syncWithServer();
  }, 7000); // Sync every 7 seconds
  
  return () => clearInterval(syncInterval);
}, []);
```

#### 4. Component Integration

```tsx
// Example component using the store
function TaskList() {
  const { tasks, isLoading, createTask, updateTask, deleteTask } = useTaskStore();
  
  // Tasks are already available locally, no loading state needed after initial load
  if (isLoading) return <Spinner />;
  
  return (
    <div>
      {Object.values(tasks).map(task => (
        <TaskItem 
          key={task.id} 
          task={task}
          onUpdate={(updates) => updateTask(task.id, updates)}
          onDelete={() => deleteTask(task.id)}
        />
      ))}
      <button onClick={() => createTask({ title: 'New Task' })}>
        Add Task
      </button>
    </div>
  );
}
```

### Entity Store Template

```typescript
// Generic template for entity stores
export const createEntityStore = <T extends { id: string }>(
  name: string,
  apiEndpoint: string
) => {
  return create<EntityState<T>>()(
    devtools(
      immer((set, get) => ({
        // State
        entities: {},
        isLoading: false,
        error: null,
        pendingChanges: {},
        lastSyncTime: 0,
        isSyncing: false,
        
        // Initialize
        init: async () => {
          set({ isLoading: true });
          try {
            const data = await fetchFromApi(apiEndpoint);
            const normalized = normalizeData(data);
            set({ entities: normalized, isLoading: false });
          } catch (error) {
            set({ error, isLoading: false });
          }
        },
        
        // CRUD operations (with optimistic updates)
        create: (data) => {
          const tempId = `temp_${Date.now()}`;
          const newEntity = { ...data, id: tempId };
          
          set(state => {
            state.entities[tempId] = newEntity;
            state.pendingChanges[tempId] = { action: 'create', data: newEntity };
          });
          
          return tempId;
        },
        
        update: (id, updates) => {
          set(state => {
            if (state.entities[id]) {
              state.entities[id] = { ...state.entities[id], ...updates };
              
              // Track changes for sync
              state.pendingChanges[id] = { 
                action: 'update', 
                data: updates 
              };
            }
          });
        },
        
        delete: (id) => {
          set(state => {
            // Track for sync before deletion
            if (state.entities[id]) {
              state.pendingChanges[id] = { action: 'delete', data: { id } };
              delete state.entities[id];
            }
          });
        },
        
        syncWithServer: async () => {
          // Implement sync logic
        }
      })),
      { name: `${name}Store` }
    )
  );
};
```

## Implementation Plan

1. **Phase 1: Create Base Store Implementation**
   - Develop the store template with sync capability
   - Implement the TaskStore as first example
   - Keep existing React Query hooks for compatibility

2. **Phase 2: Component Migration**
   - Update components to use the new stores
   - Start with simpler components like TaskItem
   - Gradually migrate more complex components like TaskDetailView

3. **Phase 3: Enhance Sync Features**
   - Add conflict resolution
   - Implement optimistic UI updates
   - Add offline support indicators

4. **Phase 4: Remove/Refactor React Query Usage**
   - Limit React Query to initial data fetching
   - Update components to rely on Zustand for state

## Benefits of New Architecture

1. **Consistent State Management**
   - Single source of truth for each entity type
   - Predictable data flow in all components

2. **Improved Performance**
   - Reduced API calls through batched updates
   - Optimistic UI updates for improved user experience

3. **Better Developer Experience**
   - Consistent patterns for state access and modification
   - Simplified component logic with no direct API calls

4. **Resilience to Network Issues**
   - Local-first approach enables offline capabilities
   - Background sync handles eventual consistency

## Potential Challenges and Mitigations

1. **Complex Sync Logic**
   - Solution: Implement sync logic incrementally, starting with simple cases
   - Consider using a library like Replicache for sync

2. **Conflict Resolution**
   - Solution: Implement entity-specific conflict resolution strategies
   - Use timestamps and versions to detect conflicts

3. **Migration Complexity**
   - Solution: Incremental migration with hybrid approach during transition
   - Maintain backward compatibility during migration

## Conclusion

The proposed architecture creates a consistent, robust state management pattern focused on local-first development with eventual synchronization. By using Zustand stores as the single source of truth and implementing background synchronization, we can improve performance, user experience, and developer productivity. 