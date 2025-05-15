import { useQuery, useMutation, useQueryClient, QueryKey } from '@tanstack/react-query';
import { supabase } from '../../lib/supabaseClient';
import { useAuthStore } from '../../features/auth/useAuthStore';
import type { Task, NewTaskData, UpdateTaskData } from '../types';

const TASKS_QUERY_KEY_PREFIX = 'tasks';

/**
 * Fetches tasks for the current authenticated user.
 */
export function useFetchTasks() {
  const user = useAuthStore((state) => state.user);
  const queryKey: QueryKey = [TASKS_QUERY_KEY_PREFIX, user?.id];

  return useQuery<Task[], Error, Task[], QueryKey>({
    queryKey: queryKey,
    queryFn: async () => {
      if (!user) throw new Error('User not authenticated');

      const { data, error } = await supabase
        .from('tasks')
        .select('*')
        .eq('user_id', user.id)
        .order('created_at', { ascending: false });

      if (error) throw error;
      return data || [];
    },
    enabled: !!user, // Only run the query if the user is authenticated
  });
}

/**
 * Creates a new task for the current authenticated user.
 */
export function useCreateTask() {
  const queryClient = useQueryClient();
  const user = useAuthStore((state) => state.user);

  return useMutation<Task, Error, Omit<NewTaskData, 'user_id'>>({
    mutationFn: async (newTaskData: Omit<NewTaskData, 'user_id'>) => {
      if (!user) throw new Error('User not authenticated');

      const taskWithUser: NewTaskData = {
        ...newTaskData,
        user_id: user.id,
      };

      const { data, error } = await supabase
        .from('tasks')
        .insert([taskWithUser])
        .select()
        .single();

      if (error) throw error;
      if (!data) throw new Error('Failed to create task: no data returned');
      return data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: [TASKS_QUERY_KEY_PREFIX] });
    },
  });
}

/**
 * Updates an existing task.
 */
export function useUpdateTask() {
  const queryClient = useQueryClient();

  return useMutation<Task, Error, { id: string; updates: UpdateTaskData }>({
    mutationFn: async ({ id, updates }: { id: string; updates: UpdateTaskData }) => {
      const { data, error } = await supabase
        .from('tasks')
        .update(updates)
        .eq('id', id)
        .select()
        .single();

      if (error) throw error;
      if (!data) throw new Error('Failed to update task: no data returned');
      return data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: [TASKS_QUERY_KEY_PREFIX] });
    },
  });
}

/**
 * Deletes a task.
 */
export function useDeleteTask() {
  const queryClient = useQueryClient();

  return useMutation<void, Error, string>({
    mutationFn: async (taskId: string) => {
      const { error } = await supabase
        .from('tasks')
        .delete()
        .eq('id', taskId);

      if (error) throw error;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: [TASKS_QUERY_KEY_PREFIX] });
    },
  });
} 