import { useQuery, useMutation, useQueryClient, QueryKey } from '@tanstack/react-query';
import { supabase } from '@/lib/supabaseClient';
import { useAuthStore } from '@/features/auth/useAuthStore';
import { toast } from '@/components/ui/toast';
import { v4 as uuidv4 } from 'uuid';

// Represents a row in the public.chat_sessions table
export interface ChatSessionInstance {
  id: string; // PK - session instance UUID
  user_id: string;
  agent_name: string;
  chat_id: string; // Persistent Chat ID
  is_active: boolean;
  updated_at: string; // ISO string
  created_at: string; // ISO string
  metadata?: Record<string, unknown> | null;
}

// --- Data types for mutation functions ---

export interface CreateChatSessionInstancePayload {
  agent_name: string;
  chat_id: string; // A new or existing chat_id
  is_active?: boolean; // Defaults to true on creation
  metadata?: Record<string, unknown>;
}

export interface UpdateChatSessionInstancePayload {
  sessionInstanceId: string; // The 'id' (PK) of the chat_sessions row
  is_active?: boolean;
  updated_at?: string; // Typically set to now() by the hook
  metadata?: Record<string, unknown>;
}

const CHAT_SESSIONS_QUERY_KEY_PREFIX = 'chat_sessions';

/**
 * Generates a new unique UUID, suitable for chat_id.
 */
export function generateNewChatId(): string {
  return uuidv4();
}

/**
 * Fetches the latest CHAT_ID for a given user and agent.
 * Priority:
 * 1. Active session's chat_id.
 * 2. Most recent inactive session's chat_id (to continue a previous chat).
 * 3. null if no session history exists for this user/agent.
 */
export function useFetchLatestChatId(agentName: string | null | undefined) {
  const user = useAuthStore((state) => state.user);
  const queryKey: QueryKey = [CHAT_SESSIONS_QUERY_KEY_PREFIX, user?.id, agentName, 'latest_chat_id'];

  return useQuery<string | null, Error, string | null, QueryKey>({
    queryKey: queryKey,
    queryFn: async () => {
      if (!user || !agentName) return null;

      // Try to find an active session first
      const { data: activeSessions, error: activeError } = await supabase
        .from('chat_sessions')
        .select('chat_id')
        .eq('user_id', user.id)
        .eq('agent_name', agentName)
        .eq('is_active', true)
        .order('updated_at', { ascending: false })
        .limit(1);

      if (activeError) {
        console.error('Error fetching active chat_id:', activeError);
        // Don't throw yet, try inactive sessions
      }

      if (activeSessions && activeSessions.length > 0 && activeSessions[0].chat_id) {
        return activeSessions[0].chat_id;
      }

      // If no active session, try to find the most recent inactive session
      const { data: inactiveSessions, error: inactiveError } = await supabase
        .from('chat_sessions')
        .select('chat_id')
        .eq('user_id', user.id)
        .eq('agent_name', agentName)
        .order('updated_at', { ascending: false })
        .limit(1);

      if (inactiveError) {
        console.error('Error fetching latest inactive chat_id:', inactiveError);
        if (!activeError) throw inactiveError; // If active also failed, throw this one.
        // If active search was ok but this one failed, we might still have a problem.
        // For now, if active check was fine and this one fails, we'll proceed as if no chat_id found.
      }

      if (inactiveSessions && inactiveSessions.length > 0 && inactiveSessions[0].chat_id) {
        return inactiveSessions[0].chat_id;
      }

      return null; // No session history found for this user/agent
    },
    enabled: !!user && !!agentName,
    retry: (failureCount) => {
      // Example: Don't retry for specific non-recoverable errors if identified
      // if (error.message.includes('SPECIFIC_ERROR_CODE')) return false;
      return failureCount < 3;
    },
  });
}

/**
 * Manages chat session instances (creation, updates like heartbeat, deactivation).
 */
export function useManageChatSessionInstance() {
  const queryClient = useQueryClient();
  const user = useAuthStore((state) => state.user);

  // --- CREATE a new session instance ---
  const createMutation = useMutation<ChatSessionInstance, Error, CreateChatSessionInstancePayload>({
    mutationFn: async (payload) => {
      if (!user) throw new Error('User not authenticated for creating session instance');

      const newSessionData = {
        user_id: user.id,
        agent_name: payload.agent_name,
        chat_id: payload.chat_id,
        is_active: payload.is_active !== undefined ? payload.is_active : true,
        updated_at: new Date().toISOString(),
        // created_at is handled by DB default
        metadata: payload.metadata,
      };

      const { data, error } = await supabase.from('chat_sessions').insert(newSessionData).select().single();

      if (error) {
        console.error('Error creating chat session instance:', error);
        toast.error('Failed to create new session', error.message);
        throw error;
      }
      if (!data) {
        const errMsg = 'Failed to create session instance: no data returned';
        console.error(errMsg);
        toast.error(errMsg);
        throw new Error(errMsg);
      }
      return data as ChatSessionInstance;
    },
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: [CHAT_SESSIONS_QUERY_KEY_PREFIX, data.user_id, data.agent_name] });
      // Optionally update specific queries if needed
      // For example, update the 'latest_chat_id' query
      queryClient.setQueryData(
        [CHAT_SESSIONS_QUERY_KEY_PREFIX, data.user_id, data.agent_name, 'latest_chat_id'],
        data.chat_id,
      );
      // Update cache for queries that fetch full session instances
      queryClient.setQueryData([CHAT_SESSIONS_QUERY_KEY_PREFIX, 'instance', data.id], data);

      // toast.success(`Session for ${data.agent_name} started.`);
    },
  });

  // --- UPDATE an existing session instance (e.g., heartbeat, deactivate) ---
  const updateMutation = useMutation<ChatSessionInstance, Error, UpdateChatSessionInstancePayload>({
    mutationFn: async (payload) => {
      if (!user) throw new Error('User not authenticated for updating session instance');

      const updateData: Partial<ChatSessionInstance> = {
        // user_id and agent_name are not typically changed on update of an existing instance
      };
      if (payload.is_active !== undefined) updateData.is_active = payload.is_active;
      updateData.updated_at = payload.updated_at || new Date().toISOString(); // Always update timestamp
      if (payload.metadata !== undefined) updateData.metadata = payload.metadata;

      const { data, error } = await supabase
        .from('chat_sessions')
        .update(updateData)
        .eq('id', payload.sessionInstanceId)
        .eq('user_id', user.id) // Ensure user owns the session they are updating
        .select()
        .single();

      if (error) {
        console.error('Error updating chat session instance:', error);
        toast.error('Failed to update session', error.message);
        throw error;
      }
      if (!data) {
        const errMsg = 'Failed to update session instance: no data returned or row not found/not permitted';
        console.error(errMsg);
        toast.error(errMsg);
        throw new Error(errMsg);
      }
      return data as ChatSessionInstance;
    },
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: [CHAT_SESSIONS_QUERY_KEY_PREFIX, data.user_id, data.agent_name] });
      // Update specific query for this instance
      queryClient.setQueryData([CHAT_SESSIONS_QUERY_KEY_PREFIX, 'instance', data.id], data);
      if (data.is_active) {
        // If it was made active, ensure latest_chat_id reflects this if it's the most recent
        queryClient.invalidateQueries({
          queryKey: [CHAT_SESSIONS_QUERY_KEY_PREFIX, data.user_id, data.agent_name, 'latest_chat_id'],
        });
      }
      // toast.info(`Session for ${data.agent_name} updated.`);
    },
  });

  return {
    createChatSessionInstance: createMutation.mutateAsync,
    updateChatSessionInstance: updateMutation.mutateAsync,
    isLoadingCreate: createMutation.isPending,
    isLoadingUpdate: updateMutation.isPending,
    errorCreate: createMutation.error,
    errorUpdate: updateMutation.error,
  };
}
