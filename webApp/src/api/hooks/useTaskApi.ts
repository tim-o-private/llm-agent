// webApp/src/api/hooks/useTaskApi.ts

// Note: These hooks are primarily intended for initial data hydration of Zustand stores
// and for use by the background server synchronization logic within those stores.
// UI components should typically interact with Zustand store actions for optimistic updates
// and data manipulation, rather than calling these mutation hooks directly for form saves.

import { useQuery, useMutation, useQueryClient, UseQueryResult, UseMutationResult, QueryKey } from '@tanstack/react-query';
import { Task, TaskCreatePayload, TaskUpdatePayload } from '@/api/types'; // Ensure these types exist or adjust path
import { AppError } from '@/types/error'; // Ensure AppError is correctly typed and path is correct

// --- Query Keys ---
export const taskQueryKeys = {
  all: ['tasks'] as const,
  lists: () => [...taskQueryKeys.all, 'list'] as const,
  list: (filters?: string | Record<string, unknown>): QueryKey => [...taskQueryKeys.lists(), filters ? { filters } : 'all'] as const,
  details: () => [...taskQueryKeys.all, 'detail'] as const,
  detail: (id: string | undefined): QueryKey => [...taskQueryKeys.details(), id] as const,
};

// --- API Service Function Placeholders ---
// These would typically call your actual API endpoints (e.g., using fetch or axios)
// For now, these are placeholders and should be implemented to interact with your backend.

const apiClient = {
  fetchTasks: async (filters?: Record<string, unknown>): Promise<Task[]> => {
    console.log('[apiClient.fetchTasks] Fetching tasks with filters:', filters);
    // Replace with actual API call
    // Example: const response = await fetch('/api/tasks'); return response.json();
    return Promise.resolve([]); // Placeholder
  },
  fetchTaskById: async (id: string): Promise<Task | null> => {
    console.log(`[apiClient.fetchTaskById] Fetching task with id: ${id}`);
    // Replace with actual API call
    // Example: const response = await fetch(`/api/tasks/${id}`); return response.json();
    return Promise.resolve(null); // Placeholder
  },
  createTask: async (payload: TaskCreatePayload): Promise<Task> => {
    console.log('[apiClient.createTask] Creating task with payload:', payload);
    // Replace with actual API call
    // Example: const response = await fetch('/api/tasks', { method: 'POST', body: JSON.stringify(payload) }); return response.json();
    // @ts-expect-error Mock implementation for placeholder
    return Promise.resolve({ id: String(Date.now()), ...payload, created_at: new Date().toISOString(), subtasks: [], user_id: 'mock-user' }); // Placeholder
  },
  updateTask: async (id: string, payload: TaskUpdatePayload): Promise<Task> => {
    console.log(`[apiClient.updateTask] Updating task ${id} with payload:`, payload);
    // Replace with actual API call
    // Example: const response = await fetch(`/api/tasks/${id}', { method: 'PUT', body: JSON.stringify(payload) }); return response.json();
    // @ts-expect-error Mock implementation for placeholder
    return Promise.resolve({ id, ...payload, created_at: new Date().toISOString(), subtasks: [], user_id: 'mock-user' }); // Placeholder
  },
  deleteTask: async (id: string): Promise<void> => {
    console.log(`[apiClient.deleteTask] Deleting task with id: ${id}`);
    // Replace with actual API call
    // Example: await fetch(`/api/tasks/${id}', { method: 'DELETE' });
    return Promise.resolve(); // Placeholder
  },
};

// --- React Query Hooks ---

/**
 * Hook to fetch a list of tasks.
 */
export const useFetchTasks = (filters?: Record<string, unknown>): UseQueryResult<Task[], AppError | Error> => {
  return useQuery({
    queryKey: taskQueryKeys.list(filters),
    queryFn: () => apiClient.fetchTasks(filters),
    // Add any options like staleTime, cacheTime, onSuccess for Zustand hydration, etc.
  });
};

/**
 * Hook to fetch a single task by its ID.
 */
export const useFetchTaskById = (taskId: string | undefined): UseQueryResult<Task | null, AppError | Error> => {
  return useQuery({
    queryKey: taskQueryKeys.detail(taskId),
    queryFn: () => (taskId ? apiClient.fetchTaskById(taskId) : Promise.resolve(null)),
    enabled: !!taskId,
    // Add any options
  });
};

/**
 * Hook for creating a new task.
 * Used by Zustand store for background sync.
 */
export const useCreateTaskMutation = (): UseMutationResult<Task, AppError | Error, TaskCreatePayload> => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (payload: TaskCreatePayload) => apiClient.createTask(payload),
    onSuccess: (data: Task) => {
      queryClient.invalidateQueries({ queryKey: taskQueryKeys.lists() });
      queryClient.setQueryData(taskQueryKeys.detail(data.id), data);
    },
    // onError, onSettled, etc. can be handled here or by the calling Zustand action
  });
};

/**
 * Hook for updating an existing task.
 * Used by Zustand store for background sync.
 */
export const useUpdateTaskMutation = (): UseMutationResult<Task, AppError | Error, { id: string; payload: TaskUpdatePayload }> => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ id, payload }: { id: string; payload: TaskUpdatePayload }) => apiClient.updateTask(id, payload),
    onSuccess: (data: Task, variables) => {
      queryClient.invalidateQueries({ queryKey: taskQueryKeys.lists() });
      queryClient.setQueryData(taskQueryKeys.detail(variables.id), data);
      // Optimistically update all lists containing this task if more granular control is needed
    },
  });
};

/**
 * Hook for deleting a task.
 * Used by Zustand store for background sync.
 */
export const useDeleteTaskMutation = (): UseMutationResult<void, AppError | Error, string> => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => apiClient.deleteTask(id),
    onSuccess: (_data: void, id: string) => {
      queryClient.invalidateQueries({ queryKey: taskQueryKeys.lists() });
      queryClient.removeQueries({ queryKey: taskQueryKeys.detail(id) });
    },
  });
}; 