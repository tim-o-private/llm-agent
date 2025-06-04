import { create } from 'zustand';
import { devtools } from 'zustand/middleware';
import { immer } from 'zustand/middleware/immer';
import { useAuthStore } from '@/features/auth/useAuthStore';
import { apiClient } from '@/lib/apiClient';
import { pollingManager } from '@/lib/pollingManager';
import { toast } from '@/components/ui/toast';
import { Task, NewTaskData, UpdateTaskData, TaskStatus } from '@/api/types';
import { CacheEntry, StorePollingConfig } from '@/types/polling';

// Define pending change structure
interface PendingChange {
  action: 'create' | 'update' | 'delete';
  data: Partial<Task>;
  retryCount?: number;
  timestamp?: number;
}

// Define the task store interface (maintaining compatibility)
export interface TaskStore {
  // Data
  tasks: Record<string, Task>;
  isLoading: boolean;
  error: Error | null;
  initialized: boolean;
  
  // Sync state
  pendingChanges: Record<string, PendingChange>;
  lastSyncTime: number;
  isSyncing: boolean;
  
  // New: Caching and polling state
  cache: CacheEntry<Task[]> | null;
  pollingConfig: StorePollingConfig;
  
  // Actions (maintaining compatibility)
  fetchTasks: () => Promise<void>;
  initializeStore: () => Promise<void>;
  createTask: (task: Omit<NewTaskData, 'user_id'>) => string;
  updateTask: (id: string, updates: Partial<Task>) => void;
  deleteTask: (id: string) => void;
  syncWithServer: () => Promise<void>;
  
  // New: Cache and polling management
  clearCache: () => void;
  isStale: () => boolean;
  refreshCache: () => Promise<void>;
  startPolling: () => void;
  stopPolling: () => void;
  updatePollingConfig: (config: Partial<StorePollingConfig>) => void;
  
  // Selectors (maintaining compatibility)
  getTaskById: (id: string) => Task | undefined;
  getSubtasksByParentId: (parentId: string) => Task[];
  getTopLevelTasks: () => Task[];
}

/**
 * Store for managing tasks with router-proxied PostgREST calls, polling, and caching
 */
export const useTaskStore = create<TaskStore>()(
  devtools(
    immer((set, get) => {
      const POLLING_KEY = 'tasks';
      
      const defaultPollingConfig: StorePollingConfig = {
        enabled: true,
        interval: 30000,        // 30 seconds
        staleThreshold: 300000, // 5 minutes
        queryLimit: 100,
      };

      return {
        // Initial state
        tasks: {},
        isLoading: false,
        error: null,
        initialized: false,
        pendingChanges: {},
        lastSyncTime: 0,
        isSyncing: false,
        
        // New: Caching and polling state
        cache: null,
        pollingConfig: defaultPollingConfig,
        
        /**
         * Initialize the store, loading data if needed
         */
        initializeStore: async () => {
          if (get().initialized || get().isLoading) {
            return Promise.resolve();
          }
          
          const tasks = get().tasks;
          if (Object.keys(tasks).length === 0) {
            return get().fetchTasks();
          }
          
          set({ initialized: true });
          return Promise.resolve();
        },
        
        /**
         * Fetch tasks from the server via router with caching
         */
        fetchTasks: async () => {
          console.log('[useTaskStore_v2] fetchTasks called');
          
          const userId = useAuthStore.getState().user?.id;
          if (!userId) {
            console.error('[useTaskStore_v2] fetchTasks failed: User not authenticated');
            set({ 
              error: new Error('User not authenticated'),
              initialized: true
            });
            return Promise.reject(new Error('User not authenticated'));
          }
          
          // Check cache first
          const { cache, isStale, pollingConfig } = get();
          if (cache && !isStale()) {
            console.log('[useTaskStore_v2] Using cached data');
            const normalizedTasks: Record<string, Task> = {};
            cache.data.forEach((task: Task) => {
              normalizedTasks[task.id] = task;
            });
            set({ 
              tasks: normalizedTasks,
              initialized: true
            });
            return Promise.resolve();
          }
          
          console.log('[useTaskStore_v2] Fetching tasks via router for user:', userId);
          set({ isLoading: true });
          
          try {
            // Router-proxied PostgREST call with query limits
            const query = `user_id=eq.${userId}&deleted=eq.false&order=position.asc.nullsfirst,priority.desc,created_at.desc&limit=${pollingConfig.queryLimit}`;
            console.log('[useTaskStore_v2] Calling apiClient.select with query:', query);
            
            const data = await apiClient.select<Task>('tasks', query);
            console.log(`[useTaskStore_v2] Router returned ${data?.length || 0} tasks`);
            
            // Create cache entry
            const newCache: CacheEntry<Task[]> = {
              data: data || [],
              timestamp: new Date(),
              lastFetch: new Date(),
              isStale: false,
              retryCount: 0,
            };
            
            // Normalize the data into a record
            const normalizedTasks: Record<string, Task> = {};
            (data || []).forEach((task: Task) => {
              normalizedTasks[task.id] = task;
            });
            
            console.log('[useTaskStore_v2] Updating store with tasks');
            set({ 
              tasks: normalizedTasks, 
              isLoading: false,
              lastSyncTime: Date.now(),
              initialized: true,
              cache: newCache,
            });
            
            console.log('[useTaskStore_v2] Store updated, tasks count:', Object.keys(normalizedTasks).length);
            return Promise.resolve();
          } catch (error) {
            console.error('[useTaskStore_v2] Error fetching tasks:', error);
            set({ 
              error: error instanceof Error ? error : new Error(String(error)),
              isLoading: false,
              initialized: true
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
            
            // Update cache if it exists
            if (state.cache) {
              state.cache.data.push(newTask);
              state.cache.timestamp = new Date();
            }
            
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
          console.log(`[useTaskStore_v2] updateTask called for ID: ${id}, Updates:`, JSON.stringify(updates, null, 2));
          set(state => {
            // Only update if the task exists
            if (!state.tasks[id]) {
              console.warn(`[useTaskStore_v2] Task with ID: ${id} not found for update.`);
              return;
            }
            
            const oldTask = JSON.parse(JSON.stringify(state.tasks[id]));
            
            // Apply updates to local state
            state.tasks[id] = {
              ...state.tasks[id],
              ...updates,
              updated_at: new Date().toISOString()
            };
            
            // Update cache if it exists
            if (state.cache) {
              const cacheIndex = state.cache.data.findIndex(task => task.id === id);
              if (cacheIndex !== -1) {
                state.cache.data[cacheIndex] = state.tasks[id];
                state.cache.timestamp = new Date();
              }
            }
            
            console.log(`[useTaskStore_v2] Task ID: ${id} - Before:`, oldTask, 'After:', JSON.parse(JSON.stringify(state.tasks[id])));
            
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
            
            // Update cache if it exists
            if (state.cache) {
              state.cache.data = state.cache.data.filter(task => task.id !== id);
              state.cache.timestamp = new Date();
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
         * Sync pending changes with the server via router
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
            // Process each pending change via router
            for (const id of pendingIds) {
              const change = pendingChanges[id];
              
              if (change.action === 'create') {
                // For create, we need to remove the temp ID and let the DB generate a real one
                const taskData = { ...change.data };
                delete taskData.id; // Remove temp ID
                
                // Convert to NewTaskData format
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
                
                // Router-proxied PostgREST call
                const data = await apiClient.insert<Task>('tasks', newTaskData);
                
                if (data) {
                  set(state => {
                    // Remove the temp task
                    delete state.tasks[id];
                    // Add the real task
                    state.tasks[data.id] = data;
                    // Update cache
                    if (state.cache) {
                      const tempIndex = state.cache.data.findIndex(task => task.id === id);
                      if (tempIndex !== -1) {
                        state.cache.data[tempIndex] = data;
                      }
                      state.cache.timestamp = new Date();
                    }
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
                
                // Router-proxied PostgREST call
                const updatedTask = await apiClient.update<Task>('tasks', id, updateData);
                
                set(state => {
                  if (updatedTask) {
                    // Update the local task with the confirmed data from the server
                    state.tasks[id] = updatedTask;
                    // Update cache
                    if (state.cache) {
                      const cacheIndex = state.cache.data.findIndex(task => task.id === id);
                      if (cacheIndex !== -1) {
                        state.cache.data[cacheIndex] = updatedTask;
                        state.cache.timestamp = new Date();
                      }
                    }
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
                
                // Router-proxied PostgREST call (soft delete)
                await apiClient.update<Task>('tasks', id, { deleted: true });
                
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
            console.error('[useTaskStore_v2] Sync error:', error);
            
            set({ 
              error: error instanceof Error ? error : new Error(String(error)),
              isSyncing: false
            });
            
            toast.error('Failed to sync tasks');
          }
        },
        
        // New: Cache management
        clearCache: () => set({ cache: null, tasks: {} }),
        
        isStale: () => {
          const { cache, pollingConfig } = get();
          if (!cache) return true;
          
          const now = Date.now();
          const cacheAge = now - cache.timestamp.getTime();
          return cacheAge > pollingConfig.staleThreshold;
        },
        
        refreshCache: async () => {
          await get().fetchTasks();
        },
        
        // New: Polling management
        startPolling: () => {
          const { pollingConfig, fetchTasks } = get();
          
          if (!pollingConfig.enabled) return;
          
          pollingManager.startPolling(
            POLLING_KEY,
            () => fetchTasks(),
            {
              interval: pollingConfig.interval,
              maxRetries: 3,
              backoffMultiplier: 1.5,
              staleThreshold: pollingConfig.staleThreshold,
            }
          );
        },
        
        stopPolling: () => {
          pollingManager.stopPolling(POLLING_KEY);
        },
        
        updatePollingConfig: (newConfig: Partial<StorePollingConfig>) => {
          set(state => {
            state.pollingConfig = { ...state.pollingConfig, ...newConfig };
          });
          
          // Restart polling with new config if currently active
          if (pollingManager.isPollingActive(POLLING_KEY)) {
            get().stopPolling();
            get().startPolling();
          }
        },
        
        // Selectors (maintaining compatibility)
        getTaskById: (id: string) => {
          return get().tasks[id];
        },
        
        getSubtasksByParentId: (parentId: string) => {
          const tasks = get().tasks;
          return Object.values(tasks).filter(task => task.parent_task_id === parentId);
        },
        
        getTopLevelTasks: () => {
          const tasks = get().tasks;
          return Object.values(tasks).filter(task => !task.parent_task_id);
        },
      };
    }),
    {
      name: 'task-store-v2',
    }
  )
);

// Hook for initializing the store (maintaining compatibility)
export const useInitializeTaskStore = () => {
  const initializeStore = useTaskStore(state => state.initializeStore);
  const startPolling = useTaskStore(state => state.startPolling);
  const stopPolling = useTaskStore(state => state.stopPolling);
  
  return {
    initializeStore: async () => {
      await initializeStore();
      startPolling(); // Start polling after initialization
    },
    startPolling,
    stopPolling,
  };
}; 