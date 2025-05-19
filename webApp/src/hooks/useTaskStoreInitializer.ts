import { useEffect } from 'react';
import { useTaskStore } from '@/stores/useTaskStore';
import { Task } from '@/api/types';

/**
 * Hook to ensure the task store is initialized for any component that needs tasks.
 * 
 * This hook should be used in components that need access to tasks to ensure
 * the store is properly hydrated before rendering. It helps maintain consistent
 * initialization patterns across components.
 * 
 * @returns The tasks from the store
 */
export const useTaskStoreInitializer = () => {
  const { 
    tasks, 
    isLoading, 
    error, 
    initialized,
    initializeStore 
  } = useTaskStore(state => ({
    tasks: state.tasks,
    isLoading: state.isLoading,
    error: state.error,
    initialized: state.initialized,
    initializeStore: state.initializeStore
  }));
  
  // Initialize the store on component mount
  useEffect(() => {
    console.log('[useTaskStoreInitializer] Starting initialization check');
    
    // Only run initialization if not already initialized
    if (!initialized && !isLoading) {
      console.log('[useTaskStoreInitializer] Calling initializeStore()');
      initializeStore().catch(err => {
        console.error('[useTaskStoreInitializer] Error initializing store:', err);
      });
    } else {
      console.log(`[useTaskStoreInitializer] Store ${initialized ? 'already initialized' : 'is loading'}, skipping initialization`);
    }
  }, [initialized, isLoading, initializeStore]);
  
  return { 
    tasks, 
    isLoading, 
    error,
    initialized
  };
};

/**
 * Hook to access and manage subtasks for a specific parent task
 * 
 * @param parentId The ID of the parent task
 * @returns Subtasks and methods to manage them
 */
export const useSubtasks = (parentId: string) => {
  // Use direct selectors instead of calling useTaskStoreInitializer
  const isLoading = useTaskStore(state => state.isLoading);
  const error = useTaskStore(state => state.error);
  
  // Initialize the store on component mount
  const initializeStore = useTaskStore(state => state.initializeStore);
  useEffect(() => {
    initializeStore();
  }, [initializeStore]);
  
  const getSubtasksByParentId = useTaskStore(state => state.getSubtasksByParentId);
  const createTask = useTaskStore(state => state.createTask);
  const updateTask = useTaskStore(state => state.updateTask);
  const deleteTask = useTaskStore(state => state.deleteTask);
  
  // Get subtasks for this parent
  const subtasks = getSubtasksByParentId(parentId);
  
  // Create a new subtask
  const addSubtask = (title: string, status: "pending" | "in_progress" | "completed" = "pending") => {
    return createTask({
      title,
      status,
      priority: 0,
      parent_task_id: parentId,
      subtask_position: subtasks.length, // Add to the end
    });
  };
  
  // Update a subtask
  const updateSubtask = (id: string, updates: Partial<Task>) => {
    updateTask(id, updates);
  };
  
  // Delete a subtask
  const deleteSubtask = (id: string) => {
    deleteTask(id);
  };
  
  // Reorder subtasks
  const reorderSubtasks = (sourceIndex: number, destinationIndex: number) => {
    if (sourceIndex === destinationIndex) return;
    
    // Get the task being moved
    const taskToMove = subtasks[sourceIndex];
    if (!taskToMove) return;
    
    // Create new order of subtask IDs
    const newOrder = [...subtasks];
    const [removed] = newOrder.splice(sourceIndex, 1);
    newOrder.splice(destinationIndex, 0, removed);
    
    // Update each task's subtask_position to match the new order
    newOrder.forEach((task, index) => {
      if (task.subtask_position !== index) {
        updateTask(task.id, { subtask_position: index });
      }
    });
  };
  
  return {
    subtasks,
    isLoading,
    error,
    addSubtask,
    updateSubtask,
    deleteSubtask,
    reorderSubtasks
  };
};

// Add other specialized hooks for tasks as needed 