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
import { toast } from '@/components/ui/toast';
import { useTaskStore } from '@/stores/useTaskStore';

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
 * Fetches subtasks for a given parent task ID for the current authenticated user.
 */
export function useFetchSubtasks(parentTaskId: string | undefined | null) {
  const user = useAuthStore((state) => state.user);
  const queryKey: QueryKey = [TASKS_QUERY_KEY_PREFIX, user?.id, 'subtasks', parentTaskId];

  return useQuery<Task[], Error, Task[], QueryKey>({
    queryKey: queryKey,
    queryFn: async () => {
      if (!user) throw new Error('User not authenticated');
      if (!parentTaskId) return [];

      const { data, error } = await supabase
        .from('tasks')
        .select('*')
        .eq('user_id', user.id)
        .eq('parent_task_id', parentTaskId)
        .order('subtask_position', { ascending: true, nullsFirst: true })
        .order('created_at', { ascending: true });

      if (error) throw error;
      return data || [];
    },
    enabled: !!user && !!parentTaskId,
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
        .insert([taskWithUser] as any)
        .select()
        .single();

      if (error) throw error;
      if (!data) throw new Error('Failed to create task: no data returned');
      return data as Task;
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
        .update(updates as any)
        .eq('id', id)
        .select()
        .single();

      if (error) throw error;
      if (!data) throw new Error('Failed to update task: no data returned');
      return data as Task;
    },
    onSuccess: (updatedTaskFromServer, variables) => {
      console.log('[useUpdateTask] onSuccess - Calling useTaskStore.updateTask with:', updatedTaskFromServer);
      useTaskStore.getState().updateTask(variables.id, updatedTaskFromServer);

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
      
      const results = await Promise.all(updates.map(async (updatePromise) => {
        console.log('[useUpdateTaskOrder] Processing one update promise...');
        const { data, error } = await updatePromise;
        if (error) {
          console.error('[useUpdateTaskOrder] Supabase error during one task order update:', error);
          throw error; 
        }
        console.log('[useUpdateTaskOrder] One task update successful, data:', data);
        return data;
      }));
      console.log('[useUpdateTaskOrder] All Supabase update results:', results);
      return results; 
    },
    onSuccess: (_data, _variables, _context) => {
      toast.success('Task order updated successfully!');
      if (user) {
        queryClient.invalidateQueries({ queryKey: [TASKS_QUERY_KEY_PREFIX, user.id] });
      } else {
        queryClient.invalidateQueries({ queryKey: [TASKS_QUERY_KEY_PREFIX] });
      }
    },
    onError: (error: Error, _variables, _context) => {
      toast.error('Failed to update task order', error.message);
    },
  });
};

/**
 * Hook to update the order (subtask_position) of multiple subtasks for a specific parent.
 * Accepts an array of objects, each with id and new subtask_position.
 */
interface SubtaskOrderUpdate {
  id: string;
  subtask_position: number;
}

export const useUpdateSubtaskOrder = () => {
  const queryClient = useQueryClient();
  const user = useAuthStore((state) => state.user);

  return useMutation<Task[], Error, { parentTaskId: string; orderedSubtasks: SubtaskOrderUpdate[] }, { previousTasks?: Task[] }>({ 
    mutationFn: async ({ parentTaskId, orderedSubtasks }) => {
      console.log('[useUpdateSubtaskOrder] mutationFn started. Parent:', parentTaskId, 'Ordered Subtasks:', JSON.stringify(orderedSubtasks));
      if (!user) throw new Error('User not authenticated');
      if (!parentTaskId) throw new Error('Parent task ID is required to update subtask order');

      const updates = orderedSubtasks.map(subtask =>
        supabase
          .from('tasks')
          .update({ subtask_position: subtask.subtask_position })
          .eq('id', subtask.id)
          .eq('user_id', user.id)
          .eq('parent_task_id', parentTaskId)
          .select()
      );
      
      const results = await Promise.all(updates.map(async (updatePromise) => {
        const { data, error } = await updatePromise;
        if (error) {
          console.error('[useUpdateSubtaskOrder] Supabase error during one subtask order update:', error);
          throw error; 
        }
        return data?.[0] || null; 
      }));
      console.log('[useUpdateSubtaskOrder] Raw results from Supabase:', JSON.stringify(results));
      
      const filteredResults = results.filter((r: Task | null): r is Task => r !== null);
      console.log('[useUpdateSubtaskOrder] Filtered results (returned by mutationFn):_filteredResults');
      return filteredResults; // Return the updated subtasks from the server
    },
    onMutate: async (variables) => {
      console.log('[useUpdateSubtaskOrder] onMutate. Variables:', variables);
      if (!user?.id) return;
      const allTasksQueryKey = [TASKS_QUERY_KEY_PREFIX, user.id];

      await queryClient.cancelQueries({ queryKey: allTasksQueryKey });

      const previousTasks = queryClient.getQueryData<Task[]>(allTasksQueryKey);
      console.log('[useUpdateSubtaskOrder] onMutate. Previous tasks from cache:', JSON.stringify(previousTasks?.map(t => t.id)));

      if (previousTasks) {
        const newOptimisticTasks = previousTasks.map((task: Task) => {
          if (task.id === variables.parentTaskId) {
            const newSubtaskPositions = new Map(variables.orderedSubtasks.map((st: SubtaskOrderUpdate) => [st.id, st.subtask_position]));
            // Ensure task.subtasks is treated as Task[] or empty array for mapping
            const currentSubtasks: Task[] = task.subtasks || [];
            const updatedParentSubtasks = currentSubtasks
              .map((st: Task) => ({ ...st, subtask_position: newSubtaskPositions.get(st.id) || st.subtask_position }))
              .sort((a: Task, b: Task) => (a.subtask_position ?? Infinity) - (b.subtask_position ?? Infinity));
            
            return { ...task, subtasks: updatedParentSubtasks };
          }
          return task;
        });
        const parentForLog = newOptimisticTasks.find(t => t.id === variables.parentTaskId);
        console.log('[useUpdateSubtaskOrder] onMutate. Setting optimistic tasks to cache:', JSON.stringify(parentForLog?.subtasks?.map((st: Task) => ({id: st.id, pos: st.subtask_position}))));
        queryClient.setQueryData<Task[]>(allTasksQueryKey, newOptimisticTasks);
      }
      return { previousTasks }; 
    },
    onError: (err, variables, context) => {
      console.error('[useUpdateSubtaskOrder] onError. Error:', err, 'Variables:', variables);
      toast.error('Failed to update subtask order', `${err.message}. Reverting.`);
      if (context?.previousTasks && user?.id) {
        console.log('[useUpdateSubtaskOrder] onError. Reverting to previous tasks:', JSON.stringify(context.previousTasks.map(t => t.id)));
        queryClient.setQueryData([TASKS_QUERY_KEY_PREFIX, user.id], context.previousTasks);
      }
    },
    onSettled: (_data, error, variables) => {
      console.log('[useUpdateSubtaskOrder] onSettled. Variables:', variables, 'Error:', error);
      if (user?.id) {
        queryClient.invalidateQueries({ queryKey: [TASKS_QUERY_KEY_PREFIX, user.id] });
        console.log('[useUpdateSubtaskOrder] onSettled. Invalidated all tasks query key.');
      }
    },
    onSuccess: (updatedSubtasksFromServer, variables) => {
      console.log('[useUpdateSubtaskOrder] onSuccess hook. Parent:', variables.parentTaskId, 'Updated Subtasks from mutationFn:', JSON.stringify(updatedSubtasksFromServer));
      toast.success('Subtask order updated successfully!');
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
    Pick<NewFocusSessionData, 'task_id' | 'planned_duration_minutes'> 
  >({
    mutationFn: async ({ task_id, planned_duration_minutes }) => {
      if (!user) throw new Error('User not authenticated');
      const newSessionData: NewFocusSessionData = {
        user_id: user.id,
        task_id,
        planned_duration_minutes,
      };
      const { data, error } = await supabase
        .from('focus_sessions')
        .insert(newSessionData as any)
        .select()
        .single();

      if (error) {
        console.error('[useCreateFocusSession] Error:', error);
        throw error;
      }
      console.log('[useCreateFocusSession] Success, data:', data);
      return data as FocusSession;
    },
    onSuccess: (_data) => {
      toast.success('Focus session started!');
      queryClient.invalidateQueries({ queryKey: [FOCUS_SESSIONS_QUERY_KEY_PREFIX, user?.id] });
    },
    onError: (error: Error) => {
      toast.error('Failed to start focus session', error.message);
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
    { sessionId: string; reflectionData: Omit<UpdateFocusSessionData, 'end_time'> }
  >({
    mutationFn: async ({ sessionId, reflectionData }) => {
      if (!user) throw new Error('User not authenticated');
      
      const updates: UpdateFocusSessionData & { end_time: string } = {
        ...reflectionData,
        end_time: new Date().toISOString(),
      };

      const { data, error } = await supabase
        .from('focus_sessions')
        .update(updates as any)
        .eq('id', sessionId)
        .eq('user_id', user.id) 
        .select()
        .single();

      if (error) {
        console.error('[useEndFocusSession] Error:', error);
        throw error;
      }
      console.log('[useEndFocusSession] Success, data:', data);
      return data as FocusSession;
    },
    onSuccess: (_data) => {
      toast.success('Focus session ended & reflection saved!');
      queryClient.invalidateQueries({ queryKey: [FOCUS_SESSIONS_QUERY_KEY_PREFIX, user?.id] });
    },
    onError: (error: Error) => {
      toast.error('Failed to save reflection', error.message);
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
        .select('*')
        .eq('user_id', user.id)
        .eq('id', taskId)
        .single();

      if (error && error.code !== 'PGRST116') {
        console.error(`[useFetchTaskById] Error fetching task ${taskId}:`, error);
        throw error;
      }
      return data;
    },
    enabled: !!user && !!taskId,
  });
}

// New hook to delete a task
export const useDeleteTask = () => {
  const queryClient = useQueryClient();
  const { user } = useAuthStore();

  return useMutation<
    Task | null,
    Error,
    { id: string }
  >({
    mutationFn: async ({ id }) => {
      if (!user) throw new Error('User not authenticated');
      
      const { data, error } = await supabase
        .from('tasks')
        .delete()
        .match({ id, user_id: user.id });

      if (error) {
        console.error('Error deleting task from Supabase:', error);
        throw error;
      }
      
      console.log('Task deleted from Supabase:', data );
      return null;
    },
    onSuccess: (_, variables) => {
      toast.success('Task deleted successfully!');
      if (user) {
        queryClient.invalidateQueries({ queryKey: [TASKS_QUERY_KEY_PREFIX, user.id] });
      } else {
        queryClient.invalidateQueries({ queryKey: [TASKS_QUERY_KEY_PREFIX] });
      }
      console.log(`Invalidated queries for tasks after deleting task ID: ${variables.id}`);
    },
    onError: (error: Error, variables) => {
      console.error(`Error deleting task ID ${variables.id}:`, error);
      toast.error('Failed to delete task', 'Please try again.');
    },
  });
}; 