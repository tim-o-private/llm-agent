### 🎯 Goal
Use Zustand stores with local-first operations and background synchronization to create a consistent state management pattern across the application.

### 📝 Description
This pattern builds on Pattern 5 (Centralized API Interaction with React Query) by adding an additional layer of local state management that allows for immediate UI updates and background synchronization with the database. It creates a clear separation between UI state and data state, while providing a consistent approach to state management across components.

### 🛠 Implementation

1. **Create entity-specific Zustand stores:**
   ```typescript
   // stores/useTaskStore.ts
   export const useTaskStore = create<TaskStore>()(
     devtools(
       immer((set, get) => ({
         // State
         tasks: {}, // Normalized data structure
         isLoading: false,
         error: null,
         pendingChanges: {}, // Track changes for sync
         lastSyncTime: 0,
         isSyncing: false,
         
         // Actions
         fetchTasks: async () => { /* ... */ },
         createTask: (task) => { /* ... */ },
         updateTask: (id, updates) => { /* ... */ },
         deleteTask: (id) => { /* ... */ },
         syncWithServer: async () => { /* ... */ },
         
         // Selectors
         getTaskById: (id) => { /* ... */ },
         getSubtasksByParentId: (parentId) => { /* ... */ },
       })),
       { name: 'taskStore' }
     )
   );
   ```

2. **Implement optimistic UI updates:**
   ```typescript
   createTask: (taskData) => {
     // Generate temporary ID for optimistic UI
     const tempId = `temp_${Date.now()}`;
     
     // Create task with temporary ID
     const newTask = { id: tempId, ...taskData };
     
     // Update local state immediately
     set(state => {
       state.tasks[tempId] = newTask;
       state.pendingChanges[tempId] = {
         action: 'create',
         data: newTask
       };
     });
     
     return tempId; // Return ID for reference
   }
   ```

3. **Set up background synchronization:**
   ```typescript
   // In store initialization
   if (typeof window !== 'undefined') {
     setInterval(() => {
       const store = useTaskStore.getState();
       if (Object.keys(store.pendingChanges).length > 0) {
         store.syncWithServer();
       }
     }, 10000); // Sync every 10 seconds
   }
   ```

4. **Handle reconciliation with server state:**
   ```typescript
   // For temporary IDs after creating on server
   if (data) { // Server returned data with real ID
     set(state => {
       // Remove the temp task
       delete state.tasks[tempId];
       // Add the real task with server-generated ID
       state.tasks[data.id] = data;
     });
   }
   ```

5. **Use in components:**
   ```tsx
   function TaskList() {
     const { 
       tasks, 
       isLoading, 
       createTask, 
       updateTask, 
       deleteTask 
     } = useTaskStore();
     
     // Initial data load (only needed once)
     useEffect(() => {
       useTaskStore.getState().fetchTasks();
     }, []);
     
     // Use normalized data from store
     const taskList = Object.values(tasks);
     
     // Actions trigger optimistic UI updates
     const handleCreateTask = () => {
       createTask({ title: 'New Task' });
     };
     
     // ...rest of component
   }
   ```

### 📚 Key Patterns & Practices

1. **Entity normalization:** Store entity data in a normalized form using an object with IDs as keys for quick lookups and updates.

2. **Temporary IDs for optimistic UI:** Generate temporary IDs for new entities and replace them with server-generated IDs after sync.

3. **Change tracking:** Track all changes (creates, updates, deletes) in a `pendingChanges` object to sync with the server.

4. **Background synchronization:** Set up a background interval to periodically sync changes with the server.

5. **Resilience to network issues:** Implement retry mechanisms and conflict resolution strategies.

### 📋 When to Use

- For entity-related data that needs to be accessed across multiple components
- When you want immediate UI feedback without waiting for API responses
- In scenarios where offline capability or resilience to network issues is important
- When you need a consistent approach to state management across the application

### 🚫 When to Avoid

- For purely local UI state (use regular Zustand stores without sync)
- For simple forms or ephemeral state (use React's useState/useReducer)
- When real-time data consistency is critical (use websockets or server-sent events)

### 📝 Documentation Reference

For detailed information on this pattern, see:
- **[Supporting Design Document](./state-management-design.md)**
- **[Supporting Code Example (TypeScript)](./state-management-example.ts)**
- **[Supporting React Component Example](./state-management-component-example.tsx)**

### Supporting Documents:

*   **Design Rationale & Detailed Flow:** [../guides/state-management-design.md](../guides/state-management-design.md)
*   **Core Store Logic Example (TypeScript):** [../examples/state-management-example.ts](../examples/state-management-example.ts)
*   **React Component Usage Example (TSX):** [../examples/state-management-component-example.tsx](../examples/state-management-component-example.tsx) 