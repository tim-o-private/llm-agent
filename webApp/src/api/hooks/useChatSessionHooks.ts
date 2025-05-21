import { useQuery, useMutation, useQueryClient, QueryKey } from '@tanstack/react-query';
import { supabase } from '@/lib/supabaseClient';
import { useAuthStore } from '@/features/auth/useAuthStore';
import { toast } from '@/components/ui/toast';
import { v4 as uuidv4 } from 'uuid'; // For generating new session IDs

export interface UserAgentActiveSession {
  user_id: string;
  agent_name: string;
  active_session_id: string;
  last_active_at: string; // ISO string
  created_at: string; // ISO string
}

export interface NewUserAgentActiveSessionData {
  user_id: string;
  agent_name: string;
  active_session_id: string;
}

export interface UpsertUserAgentActiveSessionData {
  user_id: string;
  agent_name: string;
  active_session_id: string;
  last_active_at?: string; // Optional: will default to NOW() on upsert if not provided by client
}


const USER_AGENT_ACTIVE_SESSIONS_QUERY_KEY_PREFIX = 'user_agent_active_sessions';

/**
 * Fetches the active chat session for a given user and agent.
 */
export function useFetchActiveChatSession(agentName: string | null | undefined) {
  const user = useAuthStore((state) => state.user);
  const queryKey: QueryKey = [USER_AGENT_ACTIVE_SESSIONS_QUERY_KEY_PREFIX, user?.id, agentName];

  return useQuery<UserAgentActiveSession | null, Error, UserAgentActiveSession | null, QueryKey>({
    queryKey: queryKey,
    queryFn: async () => {
      if (!user || !agentName) return null;

      const { data, error } = await supabase
        .from('user_agent_active_sessions')
        .select('*')
        .eq('user_id', user.id)
        .eq('agent_name', agentName)
        .single(); // Expects at most one row

      if (error) {
        if (error.code === 'PGRST116') { // PostgREST error: Row not found
          return null; // No active session found, not an actual error
        }
        console.error('Error fetching active chat session:', error);
        throw error;
      }
      return data as UserAgentActiveSession | null;
    },
    enabled: !!user && !!agentName,
    retry: (failureCount, error) => {
      if (error.message.includes('PGRST116')) { // Do not retry if "Row not found"
        return false;
      }
      return failureCount < 3; // Standard retry for other errors
    },
  });
}

/**
 * Creates or updates (upserts) an active chat session record.
 * If a record with the composite key (user_id, agent_name) exists, it updates active_session_id and last_active_at.
 * Otherwise, it inserts a new record.
 */
export function useUpsertActiveChatSession() {
  const queryClient = useQueryClient();
  const user = useAuthStore((state) => state.user);

  return useMutation<UserAgentActiveSession, Error, Omit<UpsertUserAgentActiveSessionData, 'user_id'>>({
    mutationFn: async (sessionData: Omit<UpsertUserAgentActiveSessionData, 'user_id'>) => {
      if (!user) throw new Error('User not authenticated');

      const dataToUpsert: UpsertUserAgentActiveSessionData = {
        ...sessionData,
        user_id: user.id,
        last_active_at: sessionData.last_active_at || new Date().toISOString(), // Default to now if not provided
      };

      const { data, error } = await supabase
        .from('user_agent_active_sessions')
        .upsert(dataToUpsert, { 
            onConflict: 'user_id, agent_name', // Specify conflict target for Supabase
            // defaultToNull: false, // Ensure fields not in upsert data are not nulled if that's the desired behavior
         })
        .select()
        .single();

      if (error) {
        console.error('Error upserting active chat session:', error);
        toast.error('Failed to update active session', error.message);
        throw error;
      }
      if (!data) {
        const errMsg = 'Failed to upsert active session: no data returned';
        console.error(errMsg);
        toast.error(errMsg);
        throw new Error(errMsg);
      }
      return data as UserAgentActiveSession;
    },
    onSuccess: (data) => {
      // Invalidate queries related to this specific user-agent session
      queryClient.invalidateQueries({ queryKey: [USER_AGENT_ACTIVE_SESSIONS_QUERY_KEY_PREFIX, data.user_id, data.agent_name] });
      // Optionally, update the query cache directly if needed for immediate UI feedback
      queryClient.setQueryData([USER_AGENT_ACTIVE_SESSIONS_QUERY_KEY_PREFIX, data.user_id, data.agent_name], data);
      // toast.success(`Session for ${data.agent_name} updated.`); // Optional success toast
    },
    onError: (error: Error) => {
        // Error already toasted in mutationFn, but can add more specific handling here if needed
        console.error('Mutation error in useUpsertActiveChatSession:', error);
    }
  });
}

/**
 * Generates a new unique session ID.
 */
export function generateNewSessionId(): string {
  return uuidv4();
} 