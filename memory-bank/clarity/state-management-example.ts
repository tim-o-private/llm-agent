import { create } from 'zustand';
import { devtools } from 'zustand/middleware';
import { immer } from 'zustand/middleware/immer';
import { useQueryClient } from '@tanstack/react-query';
import { useAuthStore } from '@/features/auth/useAuthStore';
import { supabase } from '@/lib/supabaseClient';
import { toast } from 'react-hot-toast';
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
            lastSyncTime: Date.now()
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
            data: newTask
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
          state.pendingChanges[id] = {
            ...(state.pendingChanges[id] || {}),
            action: 'update',
            data: {
              ...(state.pendingChanges[id]?.data || {}),
              ...updates
            }
          };
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
          
          // If this is a temporary task that hasn't been synced yet
          if (id.startsWith('temp_') && state.pendingChanges[id]?.action === 'create') {
            // Remove from pending changes to prevent unnecessary API call
            delete state.pendingChanges[id];
          } else {
            // Mark for deletion on next sync
            state.pendingChanges[id] = {
              action: 'delete',
              data: { id }
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
        
        // Don't sync if already syncing or no pending changes
        if (state.isSyncing || !userId || Object.keys(state.pendingChanges).length === 0) {
          return;
        }
        
        set({ isSyncing: true });
        
        try {
          // Clone pending changes to process
          const changesToProcess = { ...state.pendingChanges };
          const processedIds: string[] = [];
          const failedIds: string[] = [];
          
          // Process each change
          for (const [id, change] of Object.entries(changesToProcess)) {
            try {
              if (change.action === 'create') {
                // For temporary IDs, create in the database
                if (id.startsWith('temp_')) {
                  const { data, error } = await supabase
                    .from('tasks')
                    .insert([{ ...change.data, id: undefined, user_id: userId }])
                    .select()
                    .single();
                    
                  if (error) throw error;
                  
                  if (data) {
                    // Replace temporary task with real one
                    set(state => {
                      // Remove the temp task
                      delete state.tasks[id];
                      // Add the real task with server-generated ID
                      state.tasks[data.id] = data;
                    });
                  }
                }
              } else if (change.action === 'update') {
                // Skip updates for temporary IDs, they'll be created with all data
                if (id.startsWith('temp_')) continue;
                
                const { error } = await supabase
                  .from('tasks')
                  .update(change.data)
                  .eq('id', id)
                  .eq('user_id', userId);
                  
                if (error) throw error;
              } else if (change.action === 'delete') {
                // Skip deletes for temporary IDs, they don't exist on server
                if (id.startsWith('temp_')) continue;
                
                const { error } = await supabase
                  .from('tasks')
                  .delete()
                  .eq('id', id)
                  .eq('user_id', userId);
                  
                if (error) throw error;
              }
              
              // Mark as processed
              processedIds.push(id);
            } catch (error) {
              console.error(`Failed to sync task ${id}:`, error);
              failedIds.push(id);
              
              // Update retry count
              set(state => {
                if (state.pendingChanges[id]) {
                  state.pendingChanges[id].retryCount = 
                    (state.pendingChanges[id].retryCount || 0) + 1;
                }
              });
            }
          }
          
          // Clean up processed changes
          if (processedIds.length > 0) {
            set(state => {
              processedIds.forEach(id => {
                delete state.pendingChanges[id];
              });
            });
          }
          
          // Handle failed changes
          if (failedIds.length > 0) {
            // If some changes have been retried too many times, consider removing them
            set(state => {
              failedIds.forEach(id => {
                if ((state.pendingChanges[id]?.retryCount || 0) > 5) {
                  // Too many retries, give up
                  delete state.pendingChanges[id];
                  toast.error(`Failed to sync task after multiple attempts: ${id}`);
                }
              });
            });
          }
          
          // Update sync status
          set({ 
            isSyncing: false,
            lastSyncTime: Date.now() 
          });
          
          // Refresh from server occasionally to ensure consistency
          if (Date.now() - state.lastSyncTime > 60000) { // 1 minute
            get().fetchTasks();
          }
        } catch (error) {
          console.error('Sync error:', error);
          set({ 
            error: error instanceof Error ? error : new Error(String(error)),
            isSyncing: false
          });
        }
      },
      
      // Selector: Get task by ID
      getTaskById: (id) => {
        return get().tasks[id];
      },
      
      // Selector: Get subtasks by parent ID
      getSubtasksByParentId: (parentId) => {
        return Object.values(get().tasks).filter(
          task => task.parent_task_id === parentId
        ).sort((a, b) => {
          // Sort by subtask_position
          const posA = a.subtask_position || 0;
          const posB = b.subtask_position || 0;
          if (posA !== posB) return posA - posB;
          
          // If positions are equal, sort by created_at
          return new Date(a.created_at).getTime() - new Date(b.created_at).getTime();
        });
      }
    })),
    { name: 'taskStore' }
  )
);

// Setup automatic sync with an interval
if (typeof window !== 'undefined') {
  // Only run in browser environment
  let syncInterval: NodeJS.Timeout;
  
  const setupSyncInterval = () => {
    // Clear any existing interval
    if (syncInterval) clearInterval(syncInterval);
    
    // Set up new interval
    syncInterval = setInterval(() => {
      const store = useTaskStore.getState();
      if (Object.keys(store.pendingChanges).length > 0) {
        store.syncWithServer();
      }
    }, 10000); // 10 second sync interval
  };
  
  // Set up interval on module load
  setupSyncInterval();
  
  // Listen for store changes to reset interval if needed
  useTaskStore.subscribe(
    (state) => state.isSyncing,
    (isSyncing) => {
      if (!isSyncing) setupSyncInterval();
    }
  );
}

// Example usage in a component
/*
function TaskComponent() {
  // Get tasks and actions from store
  const { 
    tasks, 
    isLoading, 
    createTask, 
    updateTask, 
    deleteTask,
    getSubtasksByParentId
  } = useTaskStore();
  
  // Initial load - only needed once in app
  useEffect(() => {
    useTaskStore.getState().fetchTasks();
  }, []);
  
  // Get all tasks
  const allTasks = Object.values(tasks);
  
  // Or get subtasks for a specific parent
  const subtasks = getSubtasksByParentId('parent-task-id');
  
  // Use actions for immediate UI updates
  const handleCreateTask = () => {
    const taskId = createTask({ title: 'New Task' });
    console.log('Created task with optimistic ID:', taskId);
  };
  
  // The rest of your component...
}
*/ 