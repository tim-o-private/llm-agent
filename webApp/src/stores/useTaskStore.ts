import { create } from 'zustand';
import { devtools } from 'zustand/middleware';
import { immer } from 'zustand/middleware/immer';
import { useAuthStore } from '@/features/auth/useAuthStore';
import { apiClient } from '@/lib/apiClient';
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
  reorderTasks: (oldIndex: number, newIndex: number) => void;
  reorderSubtasks: (parentId: string, oldIndex: number, newIndex: number) => void;
  _reorderWithFractionalPositioning: (
    oldIndex: number, 
    newIndex: number, 
    positionField: 'position' | 'subtask_position',
    filterFn: (task: Task) => boolean,
    sortFallback?: (a: Task, b: Task) => number
  ) => void;
  
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
        
        console.log('[useTaskStore] Fetching tasks via router for user:', userId);
        set({ isLoading: true });
        
        try {
          // Router-proxied PostgREST call
          const query = `user_id=eq.${userId}&deleted=eq.false&order=position.asc.nullsfirst,priority.desc,created_at.desc&limit=100`;
          console.log('[useTaskStore] Calling apiClient.select with query:', query);
          
          const data = await apiClient.select<Task>('tasks', query);
          console.log(`[useTaskStore] Router returned ${data?.length || 0} tasks`);
          
          // Normalize the data into a record
          const normalizedTasks: Record<string, Task> = {};
          (data || []).forEach((task: Task) => {
            normalizedTasks[task.id] = task;
          });
          
          console.log('[useTaskStore] Updating store with tasks');
          console.log('[useTaskStore] Raw data length:', data?.length || 0);
          console.log('[useTaskStore] Normalized tasks count:', Object.keys(normalizedTasks).length);
          console.log('[useTaskStore] Sample task:', data?.[0]);
          
          set({ 
            tasks: normalizedTasks, 
            isLoading: false,
            lastSyncTime: Date.now(),
            initialized: true // Mark as initialized on success
          });
          
          console.log('[useTaskStore] Store updated, tasks count:', Object.keys(normalizedTasks).length);
          
          // Debug: Check top-level tasks after store update
          const topLevelCount = Object.values(normalizedTasks).filter(task => !task.parent_task_id && !task.deleted).length;
          console.log('[useTaskStore] Top-level tasks count:', topLevelCount);
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
        set(state => {
          // Only update if the task exists
          if (!state.tasks[id]) {
            return;
          }
          
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
            },
            timestamp: Date.now()
          };
        });
        
        // Schedule a sync after update (longer delay for batching)
        setTimeout(() => {
          get().syncWithServer();
        }, 2000);
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
        
        // Schedule a sync (longer delay for batching)
        setTimeout(() => {
          get().syncWithServer();
        }, 2000);
      },
      
      /**
       * Sync pending changes with the server using unified caching strategy
       * Batches operations and preserves optimistic state during sync
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
          // Group changes by type for batch processing
          const creates: Array<{ tempId: string; data: NewTaskData }> = [];
          const updates: Array<{ id: string; data: UpdateTaskData }> = [];
          const deletes: Array<string> = [];
          
          // Categorize pending changes
          for (const id of pendingIds) {
            const change = pendingChanges[id];
            
            if (change.action === 'create' && id.startsWith('temp_')) {
              const taskData = { ...change.data };
              delete taskData.id; // Remove temp ID
              
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
              
              creates.push({ tempId: id, data: newTaskData });
            } 
            else if (change.action === 'update' && !id.startsWith('temp_')) {
              updates.push({ id, data: { ...change.data } });
            } 
            else if (change.action === 'delete' && !id.startsWith('temp_')) {
              deletes.push(id);
            }
          }
          
          // Process creates
          for (const { tempId, data } of creates) {
            try {
              const createdTask = await apiClient.insert<Task>('tasks', data);
              
              if (createdTask) {
                set(state => {
                  // Remove the temp task
                  delete state.tasks[tempId];
                  // Add the real task with server-generated ID
                  state.tasks[createdTask.id] = createdTask;
                  // Remove from pending changes
                  delete state.pendingChanges[tempId];
                });
              }
            } catch (error) {
              console.error(`Failed to create task ${tempId}:`, error);
              // Keep in pending changes for retry
            }
          }
          
          // Process updates in batch (preserve optimistic state)
          const successfulUpdates: string[] = [];
          for (const { id, data } of updates) {
            try {
              // Send update to server but don't overwrite optimistic state immediately
              await apiClient.update<Task>('tasks', id, data);
              successfulUpdates.push(id);
            } catch (error) {
              console.error(`Failed to update task ${id}:`, error);
              // Keep in pending changes for retry
            }
          }
          
          // Only remove successfully synced updates from pending changes
          // Keep optimistic state intact - don't overwrite with server response
          set(state => {
            successfulUpdates.forEach(id => {
              delete state.pendingChanges[id];
            });
          });
          
          // Process deletes
          for (const id of deletes) {
            try {
              await apiClient.update<Task>('tasks', id, { deleted: true });
              
              set(state => {
                delete state.pendingChanges[id];
              });
            } catch (error) {
              console.error(`Failed to delete task ${id}:`, error);
              // Keep in pending changes for retry
            }
          }
          
          // Update sync time
          set({ 
            isSyncing: false,
            lastSyncTime: Date.now()
          });
          
          // Show success message if there were changes synced
          const totalChanges = creates.length + successfulUpdates.length + deletes.length;
          if (totalChanges > 0) {
            console.log(`Successfully synced ${totalChanges} task changes`);
          }
          
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
      },
      
      /**
       * Helper function for fractional positioning logic shared by both tasks and subtasks
       */
      _reorderWithFractionalPositioning: (
        oldIndex: number, 
        newIndex: number, 
        positionField: 'position' | 'subtask_position',
        filterFn: (task: Task) => boolean,
        sortFallback?: (a: Task, b: Task) => number
      ) => {
        if (oldIndex === newIndex) return;
        
        set(state => {
          // Get sorted tasks based on filter
          const tasks = Object.values(state.tasks)
            .filter(filterFn)
            .sort((a, b) => {
              const posA = a[positionField] !== undefined ? a[positionField] : null;
              const posB = b[positionField] !== undefined ? b[positionField] : null;
              
              if (posA !== null && posB !== null) {
                return posA - posB;
              }
              // Use custom fallback or default to created_at
              return sortFallback ? sortFallback(a, b) : 
                new Date(a.created_at).getTime() - new Date(b.created_at).getTime();
            });
          
          if (oldIndex >= tasks.length || newIndex >= tasks.length) {
            return; // Invalid indices
          }
          
          const movedTask = tasks[oldIndex];
          let newPosition: number;
          
          if (newIndex === 0) {
            // Moving to first position
            const firstTask = tasks[0];
            const firstPos = firstTask[positionField] || 0;
            newPosition = firstPos - 1000; // Use larger gaps for better precision
          } else if (newIndex >= tasks.length - 1) {
            // Moving to last position
            const lastTask = tasks[tasks.length - 1];
            const lastPos = lastTask[positionField] || 0;
            newPosition = lastPos + 1000; // Use larger gaps
          } else {
            // Moving between two tasks - use fractional positioning
            const targetIndex = newIndex > oldIndex ? newIndex : newIndex;
            const prevTask = tasks[targetIndex - 1];
            const nextTask = tasks[targetIndex];
            
            const prevPos = prevTask[positionField] || 0;
            const nextPos = nextTask[positionField] || 0;
            
            // Calculate midpoint with precision check
            const gap = nextPos - prevPos;
            
            if (gap > 0.001) {
              // Sufficient gap - use midpoint
              newPosition = prevPos + (gap / 2);
            } else {
              // Gap too small - trigger position normalization
              console.log(`${positionField} gap too small, using offset positioning`);
              newPosition = prevPos + 0.5;
              
              // TODO: Consider implementing position normalization here
              // to reset all positions to larger intervals (1000, 2000, 3000...)
            }
          }
          
          // Update only the moved task
          const updatedTask = { 
            ...movedTask, 
            [positionField]: newPosition,
            updated_at: new Date().toISOString()
          };
          
          state.tasks[movedTask.id] = updatedTask;
          
          // Add only this task to pending changes
          state.pendingChanges[movedTask.id] = {
            action: 'update',
            data: { [positionField]: newPosition },
            timestamp: Date.now()
          };
        });
        
        // Schedule sync with shorter delay since it's just one update
        setTimeout(() => {
          get().syncWithServer();
        }, 500);
      },

      /**
       * Reorder top-level tasks using fractional positioning (only updates the moved task)
       * 
       * EFFICIENCY: This approach only updates 1 task instead of N tasks:
       * - Old approach: Move task 3 to position 1 → Update positions of tasks 1,2,3,4,5... (N updates)
       * - New approach: Move task 3 to position 1 → Set task 3 position = 0.5 (1 update)
       */
      reorderTasks: (oldIndex: number, newIndex: number) => {
        get()._reorderWithFractionalPositioning(
          oldIndex,
          newIndex,
          'position',
          (task) => !task.parent_task_id && !task.deleted,
          // Custom sort fallback for top-level tasks (priority then created_at)
          (a, b) => {
            if (a.priority !== b.priority) {
              return b.priority - a.priority; // Higher priority first
            }
            return new Date(b.created_at).getTime() - new Date(a.created_at).getTime(); // Newer first
          }
        );
      },
      
      /**
       * Reorder subtasks using fractional positioning (only updates the moved subtask)
       * 
       * EFFICIENCY: Same algorithm as reorderTasks but for subtasks within a parent.
       * Uses subtask_position field and filters by parent_task_id.
       */
      reorderSubtasks: (parentId: string, oldIndex: number, newIndex: number) => {
        get()._reorderWithFractionalPositioning(
          oldIndex,
          newIndex,
          'subtask_position',
          (task) => task.parent_task_id === parentId && !task.deleted
          // Uses default sort fallback (created_at) for subtasks
        );
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