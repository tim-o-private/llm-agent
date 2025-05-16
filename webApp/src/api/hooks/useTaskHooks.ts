import { useQuery, useMutation, useQueryClient, QueryKey } from '@tanstack/react-query';
import { supabase } from '@/lib/supabaseClient';
import { useAuthStore } from '@/features/auth/useAuthStore';
import type { 
  Task, 
  NewTaskData, 
  UpdateTaskData, 
  FocusSession, 
  NewFocusSessionData, 
  UpdateFocusSessionData 
} from '../types';
import { toast } from 'react-hot-toast';

const TASKS_QUERY_KEY_PREFIX = 'tasks';
const FOCUS_SESSIONS_QUERY_KEY_PREFIX = 'focus_sessions';

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
        .order('position', { ascending: true, nullsFirst: true })
        .order('priority', { ascending: false })
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
 * Hook to update the order (position) of multiple tasks.
 * Accepts an array of objects, each with id and new position.
 */
interface TaskOrderUpdate {
  id: string;
  position: number;
}

export const useUpdateTaskOrder = () => {
  const queryClient = useQueryClient();
  const user = useAuthStore((state) => state.user);

  return useMutation({
    mutationFn: async (orderedTasks: TaskOrderUpdate[]) => {
      console.log('[useUpdateTaskOrder] mutationFn started with:', orderedTasks);
      if (!supabase) {
        console.error('[useUpdateTaskOrder] Supabase client is NOT available here!');
        throw new Error('Supabase client not available');
      }
      console.log('[useUpdateTaskOrder] Supabase client seems available.');

      const updates = orderedTasks.map(task =>
        supabase
          .from('tasks')
          .update({ position: task.position })
          .eq('id', task.id)
          .select()
      );
      console.log('[useUpdateTaskOrder] Supabase update promises created:', updates.length);
      
      // Rewrapping Promise.all to ensure errors are thrown correctly for useMutation
      const results = await Promise.all(updates.map(async (updatePromise) => {
        console.log('[useUpdateTaskOrder] Processing one update promise...');
        const { data, error } = await updatePromise;
        if (error) {
          console.error('[useUpdateTaskOrder] Supabase error during one task order update:', error);
          throw error; // Re-throw to be caught by useMutation's onError
        }
        console.log('[useUpdateTaskOrder] One task update successful, data:', data);
        return data;
      }));
      console.log('[useUpdateTaskOrder] All Supabase update results:', results);
      return results; // This will be an array of results from each update, or nulls
    },
    onSuccess: (_data, _variables, _context) => {
      toast.success('Task order updated!');
      if (user) {
        queryClient.invalidateQueries({ queryKey: [TASKS_QUERY_KEY_PREFIX, user.id] });
      } else {
        queryClient.invalidateQueries({ queryKey: [TASKS_QUERY_KEY_PREFIX] });
      }
    },
    onError: (error: Error, _variables, _context) => {
      toast.error(`Failed to update task order: ${error.message}`);
    },
  });
};

/**
 * Hook to create a new focus session when a task execution starts.
 */
export const useCreateFocusSession = () => {
  const queryClient = useQueryClient();
  const user = useAuthStore((state) => state.user);

  return useMutation<
    FocusSession | null, 
    Error,
    Pick<NewFocusSessionData, 'task_id'> 
  >({
    mutationFn: async ({ task_id }) => {
      if (!user) throw new Error('User not authenticated');
      const newSessionData: NewFocusSessionData = {
        user_id: user.id,
        task_id,
      };
      const { data, error } = await supabase
        .from('focus_sessions')
        .insert(newSessionData)
        .select()
        .single();

      if (error) {
        console.error('[useCreateFocusSession] Error:', error);
        throw error;
      }
      console.log('[useCreateFocusSession] Success, data:', data);
      return data;
    },
    onSuccess: (_data) => {
      toast.success('Focus session started!');
      queryClient.invalidateQueries({ queryKey: [FOCUS_SESSIONS_QUERY_KEY_PREFIX, user?.id] });
    },
    onError: (error: Error) => {
      toast.error(`Failed to start focus session: ${error.message}`);
    },
  });
};

/**
 * Hook to update (end) a focus session with reflection data.
 */
export const useEndFocusSession = () => {
  const queryClient = useQueryClient();
  const user = useAuthStore((state) => state.user);

  return useMutation<
    FocusSession | null,
    Error,
    { sessionId: string; reflectionData: UpdateFocusSessionData }
  >({
    mutationFn: async ({ sessionId, reflectionData }) => {
      if (!user) throw new Error('User not authenticated');
      
      const updates: UpdateFocusSessionData = {
        ...reflectionData,
        ended_at: new Date().toISOString(),
      };

      const { data, error } = await supabase
        .from('focus_sessions')
        .update(updates)
        .eq('id', sessionId)
        .eq('user_id', user.id) 
        .select()
        .single();

      if (error) {
        console.error('[useEndFocusSession] Error:', error);
        throw error;
      }
      console.log('[useEndFocusSession] Success, data:', data);
      return data;
    },
    onSuccess: (_data) => {
      toast.success('Focus session ended & reflection saved!');
      queryClient.invalidateQueries({ queryKey: [FOCUS_SESSIONS_QUERY_KEY_PREFIX, user?.id] });
    },
    onError: (error: Error) => {
      toast.error(`Failed to save reflection: ${error.message}`);
    },
  });
};

/**
 * Fetches a single task by its ID for the current authenticated user.
 */
export function useFetchTaskById(taskId: string | null | undefined) {
  const user = useAuthStore((state) => state.user);
  const queryKey: QueryKey = [TASKS_QUERY_KEY_PREFIX, 'detail', taskId];

  return useQuery<Task | null, Error, Task | null, QueryKey>({
    queryKey: queryKey,
    queryFn: async () => {
      if (!user || !taskId) return null;

      const { data, error } = await supabase
        .from('tasks')
        .select('*') // Select all columns for the detail view
        .eq('user_id', user.id)
        .eq('id', taskId)
        .single(); // Expect a single record or null

      if (error && error.code !== 'PGRST116') { // PGRST116: Row to abort not found (ok if task DNE)
        console.error(`[useFetchTaskById] Error fetching task ${taskId}:`, error);
        throw error;
      }
      return data;
    },
    enabled: !!user && !!taskId, // Only run the query if the user is authenticated and taskId is provided
  });
}

// New hook to delete a task
export const useDeleteTask = () => {
  const queryClient = useQueryClient();
  const { user } = useAuthStore();

  return useMutation<
    Task | null, // Supabase delete might return the deleted record or null/count
    Error,
    { id: string } // Variables for the mutation: task ID
  >({ 
    mutationFn: async ({ id }) => {
      if (!user) throw new Error('User not authenticated');
      
      // Perform the delete operation
      const { data, error } = await supabase
        .from('tasks')
        .delete()
        .match({ id, user_id: user.id }); // Ensure user can only delete their own tasks

      if (error) {
        console.error('Error deleting task from Supabase:', error);
        throw error;
      }
      
      console.log('Task deleted from Supabase:', data ); // `data` might be an empty array or count
      return null; // Or adjust based on actual Supabase client return for delete
    },
    onSuccess: (_, variables) => {
      toast.success('Task deleted successfully!');
      // Invalidate tasks query to refetch and update the list
      if (user) {
        queryClient.invalidateQueries({ queryKey: [TASKS_QUERY_KEY_PREFIX, user.id] });
      } else {
        queryClient.invalidateQueries({ queryKey: [TASKS_QUERY_KEY_PREFIX] });
      }
      console.log(`Invalidated queries for tasks after deleting task ID: ${variables.id}`);
    },
    onError: (error: Error, variables) => {
      console.error(`Error deleting task ID ${variables.id}:`, error);
      toast.error('Failed to delete task. Please try again.');
    },
  });
}; 