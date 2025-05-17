import { create } from 'zustand';
import { devtools } from 'zustand/middleware';
import { immer } from 'zustand/middleware/immer';
import { useQueryClient } from '@tanstack/react-query';
import { useAuthStore } from '@/features/auth/useAuthStore';
import { supabase } from '@/lib/supabaseClient';
import { toast } from 'react-hot-toast'; // TODO: Replace with Radix Toast as per updated guidelines
import { Task, NewTaskData, UpdateTaskData } from '@/api/types';

// Define the structure of our task store
interface TaskStore {
  // Data
  tasks: Record<string, Task>;
  isLoading: boolean;
  error: Error | null;
  
  // Sync state
  pendingChanges: Record<string, { 
    action: 'create' | 'update' | 'delete'; 
    data: Partial<Task>;
    retryCount?: number;
  }>;
  lastSyncTime: number;
  isSyncing: boolean;
  
  // Actions
  fetchTasks: () => Promise<void>;
  createTask: (task: Omit<NewTaskData, 'user_id'>) => string; // Returns local ID
  updateTask: (id: string, updates: Partial<Task>) => void;
  deleteTask: (id: string) => void;
  syncWithServer: () => Promise<void>;
  
  // Selectors
  getTaskById: (id: string) => Task | undefined;
  getSubtasksByParentId: (parentId: string) => Task[];
}

const MAX_RETRY_COUNT = 3;
const RETRY_DELAY_MS = 1000;

/**
 * Store for managing tasks with local-first state and eventual sync
 */
export const useTaskStore = create<TaskStore>()(
  devtools(
    immer((set, get) => ({
      // Initial state
      tasks: {},
      isLoading: false,
      error: null,
      pendingChanges: {},
      lastSyncTime: 0,
      isSyncing: false,
      
      // Fetch tasks from the server and initialize the store
      fetchTasks: async () => {
        const userId = useAuthStore.getState().user?.id;
        if (!userId) {
          set({ error: new Error('User not authenticated') });
          return;
        }
        
        set({ isLoading: true });
        
        try {
          const { data, error } = await supabase
            .from('tasks')
            .select('*')
            .eq('user_id', userId)
            .order('position', { ascending: true, nullsFirst: true })
            .order('priority', { ascending: false })
            .order('created_at', { ascending: false });
            
          if (error) throw error;
          
          // Normalize the data into a record
          const normalizedTasks: Record<string, Task> = {};
          (data || []).forEach(task => {
            normalizedTasks[task.id] = task;
          });
          
          set({ 
            tasks: normalizedTasks, 
            isLoading: false,
            lastSyncTime: Date.now(),
            error: null // Clear previous errors on successful fetch
          });
        } catch (error) {
          set({ 
            error: error instanceof Error ? error : new Error(String(error)),
            isLoading: false
          });
        }
      },
      
      // Create a task locally with optimistic UI update
      createTask: (taskData) => {
        const userId = useAuthStore.getState().user?.id;
        if (!userId) {
          // This should ideally not happen if UI prevents action
          // Consider logging this error or showing a persistent notification
          console.error("Create task attempted without authenticated user.");
          toast.error("User not authenticated. Please log in.");
          set({ error: new Error('User not authenticated') }); 
          return '';
        }
        
        // Generate temporary ID for optimistic UI
        const tempId = `temp_${Date.now()}`;
        
        // Create task with temporary ID
        const newTask: Task = {
          id: tempId,
          user_id: userId,
          title: taskData.title || '',
          description: taskData.description || null,
          notes: taskData.notes || null,
          status: taskData.status || 'pending',
          priority: taskData.priority || 0,
          category: taskData.category || null,
          due_date: taskData.due_date || null,
          completed: taskData.status === 'completed',
          parent_task_id: taskData.parent_task_id || null,
          position: taskData.position || null,
          subtask_position: taskData.subtask_position || null,
          created_at: new Date().toISOString(),
          updated_at: new Date().toISOString(),
        };
        
        // Update local state with the new task
        set(state => {
          // Add task to tasks collection
          state.tasks[tempId] = newTask;
          
          // Add to pending changes for sync
          state.pendingChanges[tempId] = {
            action: 'create',
            data: newTask,
            retryCount: 0
          };
        });
        
        // Schedule a sync soon after create
        setTimeout(() => {
          get().syncWithServer();
        }, 800);
        
        return tempId;
      },
      
      // Update a task locally with optimistic UI
      updateTask: (id, updates) => {
        set(state => {
          // Only update if the task exists
          if (!state.tasks[id]) return;
          
          // Apply updates to local state
          state.tasks[id] = {
            ...state.tasks[id],
            ...updates,
            updated_at: new Date().toISOString()
          };
          
          // Add or update in pending changes
          // If it was a 'create' and hasn't synced, keep it as create but with updated data
          const currentPendingChange = state.pendingChanges[id];
          if (currentPendingChange && currentPendingChange.action === 'create') {
            state.pendingChanges[id] = {
              ...currentPendingChange,
              data: { ...currentPendingChange.data, ...updates }
            };
          } else {
            state.pendingChanges[id] = {
              action: 'update',
              data: {
                ...(currentPendingChange?.data || {}), // Preserve other pending updates if any
                ...updates
              },
              retryCount: 0
            };
          }
        });
        
        // Schedule a sync after update
        setTimeout(() => {
          get().syncWithServer();
        }, 800);
      },
      
      // Delete a task locally with optimistic UI
      deleteTask: (id) => {
        set(state => {
          // Check if task exists
          if (!state.tasks[id]) return;
          
          // If this is a temporary task that hasn't been synced yet (pending create)
          if (id.startsWith('temp_') && state.pendingChanges[id]?.action === 'create') {
            // Remove from pending changes to prevent unnecessary API call
            delete state.pendingChanges[id];
          } else {
            // Mark for deletion on next sync
            state.pendingChanges[id] = {
              action: 'delete',
              data: { id }, // Only need ID for delete
              retryCount: 0
            };
          }
          
          // Remove from local state 
          delete state.tasks[id];
        });
        
        // Schedule a sync
        setTimeout(() => {
          get().syncWithServer();
        }, 800);
      },
      
      // Sync pending changes with the server
      syncWithServer: async () => {
        const state = get();
        const userId = useAuthStore.getState().user?.id;
        
        // Don't sync if already syncing or no pending changes or not authenticated
        if (state.isSyncing || !userId || Object.keys(state.pendingChanges).length === 0) {
          return;
        }
        
        set({ isSyncing: true });
        
        try {
          // Clone pending changes to process
          const changesToProcess = { ...state.pendingChanges };
          let newPendingChanges = { ...state.pendingChanges }; // Start with current pending changes
          
          // Process each change
          for (const [id, change] of Object.entries(changesToProcess)) {
            try {
              if (change.action === 'create') {
                // For temporary IDs, create in the database
                if (id.startsWith('temp_')) {
                  // Ensure user_id is correctly set from auth, not from potentially stale pending change data
                  const taskToInsert = { ...change.data, id: undefined, user_id: userId };
                  const { data: createdTask, error } = await supabase
                    .from('tasks')
                    .insert([taskToInsert])
                    .select()
                    .single();
                    
                  if (error) throw error;
                  
                  if (createdTask) {
                    // Replace temporary task with real one
                    set(s => {
                      delete s.tasks[id]; // Remove temp task
                      s.tasks[createdTask.id] = createdTask; // Add real task
                      delete newPendingChanges[id]; // Remove from pending changes
                    });
                  }
                }
              } else if (change.action === 'update') {
                // Skip updates for temporary IDs if they are still marked as 'create' (should be handled by create logic)
                if (id.startsWith('temp_')) continue;
                
                // Ensure user_id is for authorization, but don't include it in the update payload unless it's a field to be changed.
                const updatePayload = { ...change.data };
                delete updatePayload.user_id; // Avoid trying to update user_id typically
                delete updatePayload.id; // Cannot update ID

                const { error } = await supabase
                  .from('tasks')
                  .update(updatePayload)
                  .eq('id', id)
                  .eq('user_id', userId);
                  
                if (error) throw error;
                set(s => { delete newPendingChanges[id]; });

              } else if (change.action === 'delete') {
                // Skip deletes for temporary IDs that were never created on server
                if (id.startsWith('temp_')) {
                  set(s => { delete newPendingChanges[id]; });
                  continue;
                }

                const { error } = await supabase
                  .from('tasks')
                  .delete()
                  .eq('id', id)
                  .eq('user_id', userId);
                
                if (error) throw error;
                set(s => { delete newPendingChanges[id]; });
              }
            } catch (error: any) {
              console.error(`Failed to sync change for ID ${id}:`, error);
              toast.error(`Failed to sync task: ${change.action} ${state.tasks[id]?.title || id}`);
              set(s => {
                if (newPendingChanges[id]) {
                  newPendingChanges[id].retryCount = (newPendingChanges[id].retryCount || 0) + 1;
                  if (newPendingChanges[id].retryCount! >= MAX_RETRY_COUNT) {
                    // Too many retries, remove from pending and log as critical failure
                    console.error(`CRITICAL: Failed to sync task ${id} after ${MAX_RETRY_COUNT} retries. Giving up.`);
                    toast.error(`Failed to sync task ${state.tasks[id]?.title || id} after multiple retries. Data may be out of sync.`);
                    delete newPendingChanges[id];
                  } else {
                    // Optionally, implement backoff for retries here
                  }
                }
              });
            }
          }
          
          // Update pendingChanges state with what's left (failed items to be retried)
          set({
            pendingChanges: newPendingChanges,
            lastSyncTime: Date.now(),
            isSyncing: false,
            error: null // Clear previous global sync errors if any operations succeeded or were processed
          });

        } catch (error: any) {
          // Catch any unexpected errors during the sync batch itself
          console.error("Error during sync process:", error);
          toast.error("An unexpected error occurred during data synchronization.");
          set({ 
            error: error instanceof Error ? error : new Error(String(error)),
            isSyncing: false 
          });
        }
      },
      
      // Selectors
      getTaskById: (id) => {
        return get().tasks[id];
      },
      getSubtasksByParentId: (parentId) => {
        return Object.values(get().tasks).filter(task => task.parent_task_id === parentId);
      },
    })),
    { name: 'taskStore' }
  );

// Automatic background synchronization setup
// This should only run in the browser environment
let syncIntervalId: NodeJS.Timeout | null = null;

const setupSyncInterval = () => {
  if (typeof window !== 'undefined') {
    if (syncIntervalId) clearInterval(syncIntervalId);
    syncIntervalId = setInterval(() => {
      const { pendingChanges, isSyncing } = useTaskStore.getState();
      if (Object.keys(pendingChanges).length > 0 && !isSyncing) {
        useTaskStore.getState().syncWithServer();
      }
    }, 10000); // Sync every 10 seconds if there are pending changes
  }
};

// Initialize the sync interval when the store is first used or app loads
setupSyncInterval();

// Optionally, listen to auth changes to re-fetch tasks or clear store
if (typeof window !== 'undefined') {
  useAuthStore.subscribe(
    (state, prevState) => {
      // On login, fetch tasks
      if (state.user && !prevState.user) {
        useTaskStore.getState().fetchTasks();
      }
      // On logout, clear tasks and pending changes
      if (!state.user && prevState.user) {
        useTaskStore.setState({
          tasks: {},
          pendingChanges: {},
          isLoading: false,
          error: null,
          lastSyncTime: 0
        });
      }
    }
  );
}

// TODO: Add a note about react-hot-toast being deprecated in favor of Radix Toast.
// This example uses react-hot-toast for now but should be updated. 