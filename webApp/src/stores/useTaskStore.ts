import { create } from 'zustand';
import { devtools } from 'zustand/middleware';
import { immer } from 'zustand/middleware/immer';
import { useAuthStore } from '@/features/auth/useAuthStore';
import { supabase } from '@/lib/supabaseClient';
import { toast } from '@/components/ui/toast';
import { Task, NewTaskData, UpdateTaskData, TaskStatus } from '@/api/types';
import { useEffect } from 'react';

// Define pending change structure
interface PendingChange {
  action: 'create' | 'update' | 'delete';
  data: Partial<Task>;
  retryCount?: number;
  timestamp?: number;
}

// Define the task store interface
export interface TaskStore {
  // Data
  tasks: Record<string, Task>;
  isLoading: boolean;
  error: Error | null;
  initialized: boolean; // Flag to track if store has been initialized
  
  // Sync state
  pendingChanges: Record<string, PendingChange>;
  lastSyncTime: number;
  isSyncing: boolean;
  
  // Actions
  fetchTasks: () => Promise<void>;
  initializeStore: () => Promise<void>;
  createTask: (task: Omit<NewTaskData, 'user_id'>) => string;
  updateTask: (id: string, updates: Partial<Task>) => void;
  deleteTask: (id: string) => void;
  syncWithServer: () => Promise<void>;
  
  // Selectors
  getTaskById: (id: string) => Task | undefined;
  getSubtasksByParentId: (parentId: string) => Task[];
  getTopLevelTasks: () => Task[];
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
      initialized: false,
      pendingChanges: {},
      lastSyncTime: 0,
      isSyncing: false,
      
      /**
       * Initialize the store, loading data if needed
       */
      initializeStore: async () => {
        // If already initialized or loading, don't initialize again
        if (get().initialized || get().isLoading) {
          return Promise.resolve();
        }
        
        const tasks = get().tasks;
        // Only fetch if we don't have data
        if (Object.keys(tasks).length === 0) {
          // Return the promise from fetchTasks
          return get().fetchTasks();
        }
        
        // If we already have tasks but aren't marked as initialized
        set({ initialized: true });
        return Promise.resolve();
      },
      
      /**
       * Fetch tasks from the server and initialize the store
       */
      fetchTasks: async () => {
        console.log('[useTaskStore] fetchTasks called');
        
        const userId = useAuthStore.getState().user?.id;
        if (!userId) {
          console.error('[useTaskStore] fetchTasks failed: User not authenticated');
          set({ 
            error: new Error('User not authenticated'),
            initialized: true // Even on error, mark as initialized to prevent retries
          });
          return Promise.reject(new Error('User not authenticated'));
        }
        
        console.log('[useTaskStore] Fetching tasks for user:', userId);
        set({ isLoading: true });
        
        try {
          console.log('[useTaskStore] Calling supabase.from("tasks").select()');
          const { data, error } = await supabase
            .from('tasks')
            .select('*')
            .eq('user_id', userId)
            .eq('deleted', false)
            .order('position', { ascending: true, nullsFirst: true })
            .order('priority', { ascending: false })
            .order('created_at', { ascending: false });
            
          if (error) {
            console.error('[useTaskStore] Supabase error:', error);
            throw error;
          }
          
          console.log(`[useTaskStore] Supabase returned ${data?.length || 0} tasks`);
          
          // Normalize the data into a record
          const normalizedTasks: Record<string, Task> = {};
          (data || []).forEach((task: Task) => {
            normalizedTasks[task.id] = task;
          });
          
          console.log('[useTaskStore] Updating store with tasks');
          set({ 
            tasks: normalizedTasks, 
            isLoading: false,
            lastSyncTime: Date.now(),
            initialized: true // Mark as initialized on success
          });
          
          console.log('[useTaskStore] Store updated, tasks count:', Object.keys(normalizedTasks).length);
          return Promise.resolve();
        } catch (error) {
          console.error('[useTaskStore] Error fetching tasks:', error);
          set({ 
            error: error instanceof Error ? error : new Error(String(error)),
            isLoading: false,
            initialized: true // Even on error, mark as initialized to prevent retries
          });
          
          toast.error('Failed to load tasks');
          return Promise.reject(error);
        }
      },
      
      /**
       * Create a task locally with optimistic UI update
       */
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
          deleted: false,
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
            timestamp: Date.now()
          };
        });
        
        // Schedule a sync soon after create
        setTimeout(() => {
          get().syncWithServer();
        }, 800);
        
        toast.success('Task created');
        return tempId;
      },
      
      /**
       * Update a task locally with optimistic UI
       */
      updateTask: (id, updates) => {
        console.log(`[useTaskStore] updateTask called for ID: ${id}, Updates:`, JSON.stringify(updates, null, 2));
        set(state => {
          // Only update if the task exists
          if (!state.tasks[id]) {
            console.warn(`[useTaskStore] Task with ID: ${id} not found for update.`);
            return;
          }
          const oldTask = JSON.parse(JSON.stringify(state.tasks[id])); // Deep copy for logging
          
          // Apply updates to local state
          state.tasks[id] = {
            ...state.tasks[id],
            ...updates,
            updated_at: new Date().toISOString()
          };
          console.log(`[useTaskStore] Task ID: ${id} - Before:`, oldTask, 'After:', JSON.parse(JSON.stringify(state.tasks[id])));
          
          // Add or update in pending changes
          state.pendingChanges[id] = {
            ...(state.pendingChanges[id] || {}),
            action: 'update',
            data: {
              ...(state.pendingChanges[id]?.data || {}),
              ...updates
            },
            timestamp: Date.now()
          };
        });
        
        // Schedule a sync after update
        setTimeout(() => {
          get().syncWithServer();
        }, 800);
      },
      
      /**
       * Delete a task locally with optimistic UI
       */
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
              data: { id },
              timestamp: Date.now()
            };
          }
          
          // Remove from local state 
          delete state.tasks[id];
        });
        
        toast.success('Task deleted');
        
        // Schedule a sync
        setTimeout(() => {
          get().syncWithServer();
        }, 800);
      },
      
      /**
       * Sync pending changes with the server
       */
      syncWithServer: async () => {
        const pendingChanges = get().pendingChanges;
        const pendingIds = Object.keys(pendingChanges);
        
        // If no changes or already syncing, return
        if (pendingIds.length === 0 || get().isSyncing) {
          return;
        }
        
        const userId = useAuthStore.getState().user?.id;
        if (!userId) {
          set({ error: new Error('User not authenticated') });
          return;
        }
        
        set({ isSyncing: true });
        
        try {
          // Process each pending change
          for (const id of pendingIds) {
            const change = pendingChanges[id];
            
            if (change.action === 'create') {
              // For create, we need to remove the temp ID and let the DB generate a real one
              const taskData = { ...change.data };
              delete taskData.id; // Remove temp ID
              
              // Need to convert to NewTaskData format
              const newTaskData: NewTaskData = {
                user_id: userId,
                title: taskData.title || '',
                status: taskData.status as TaskStatus || 'pending',
                priority: taskData.priority || 0,
                description: taskData.description,
                notes: taskData.notes,
                category: taskData.category,
                due_date: taskData.due_date,
                parent_task_id: taskData.parent_task_id,
                position: taskData.position,
                subtask_position: taskData.subtask_position,
              };
              
              const { data, error } = await supabase
                .from('tasks')
                .insert([newTaskData])
                .select()
                .single();
                
              if (error) throw error;
              
              if (data) {
                set(state => {
                  // Remove the temp task
                  delete state.tasks[id];
                  // Add the real task
                  state.tasks[data.id] = data;
                  // Remove from pending changes
                  delete state.pendingChanges[id];
                });
              }
            } 
            else if (change.action === 'update') {
              if (id.startsWith('temp_')) {
                continue; 
              }
              
              const updateData: UpdateTaskData = { ...change.data };
              
              // Get the updated row back by adding .select().single()
              const { data: updatedTaskFromServer, error } = await supabase
                .from('tasks')
                .update(updateData)
                .eq('id', id)
                .eq('user_id', userId)
                .select()
                .single(); // Assuming we expect one row back
                
              if (error) throw error;
              
              set(state => {
                if (updatedTaskFromServer) {
                  // Update the local task with the confirmed data from the server
                  state.tasks[id] = updatedTaskFromServer;
                }
                // Remove from pending changes on success
                delete state.pendingChanges[id];
              });
            } 
            else if (change.action === 'delete') {
              // For delete, we need the real ID (not temp)
              if (id.startsWith('temp_')) {
                continue; // Skip deletes for temp tasks that haven't been created yet
              }
              
              const { error } = await supabase
                .from('tasks')
                .update({ deleted: true })
                .eq('id', id)
                .eq('user_id', userId);
                
              if (error) throw error;
              
              // Remove from pending changes on success
              set(state => {
                delete state.pendingChanges[id];
              });
            }
          }
          
          // Update sync time
          set({ 
            isSyncing: false,
            lastSyncTime: Date.now()
          });
          
        } catch (error) {
          console.error('Sync error:', error);
          
          set({ 
            error: error instanceof Error ? error : new Error(String(error)),
            isSyncing: false
          });
          
          // Increment retry counts for failed changes
          set(state => {
            Object.keys(state.pendingChanges).forEach(id => {
              if (state.pendingChanges[id]) {
                state.pendingChanges[id].retryCount = (state.pendingChanges[id].retryCount || 0) + 1;
              }
            });
          });
          
          toast.error('Failed to sync tasks');
        }
      },
      
      /**
       * Get a task by ID
       */
      getTaskById: (id) => {
        return get().tasks[id];
      },
      
      /**
       * Get subtasks for a parent task
       */
      getSubtasksByParentId: (parentId) => {
        return Object.values(get().tasks).filter(
          task => task.parent_task_id === parentId && !task.deleted
        ).sort((a, b) => {
          // Sort by subtask_position if available
          const posA = a.subtask_position !== undefined ? a.subtask_position : null;
          const posB = b.subtask_position !== undefined ? b.subtask_position : null;
          
          if (posA !== null && posB !== null) {
            return posA - posB;
          }
          // Fallback to created_at
          return new Date(a.created_at).getTime() - new Date(b.created_at).getTime();
        });
      },
      
      /**
       * Get all top-level tasks (no parent)
       */
      getTopLevelTasks: () => {
        return Object.values(get().tasks).filter(
          task => !task.parent_task_id && !task.deleted
        ).sort((a, b) => {
          // Sort by position if available
          const posA = a.position !== undefined ? a.position : null;
          const posB = b.position !== undefined ? b.position : null;
          
          if (posA !== null && posB !== null) {
            return posA - posB;
          }
          // Then by priority (higher first)
          if (a.priority !== b.priority) {
            return b.priority - a.priority;
          }
          // Then by created_at (newer first)
          return new Date(b.created_at).getTime() - new Date(a.created_at).getTime();
        });
      }
    })),
    { name: 'taskStore' }
  )
);

// Set up background sync interval
if (typeof window !== 'undefined') {
  // Run every 10 seconds
  setInterval(() => {
    const store = useTaskStore.getState();
    if (Object.keys(store.pendingChanges).length > 0) {
      store.syncWithServer();
    }
  }, 10000);
}

/**
 * Hook to initialize the task store
 */
export const useInitializeTaskStore = () => {
  const initializeStore = useTaskStore(state => state.initializeStore);
  
  // Initialize store on component mount
  useEffect(() => {
    initializeStore();
  }, [initializeStore]);
}; 