import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { supabase } from '@/lib/supabaseClient';
import { toast } from '@/components/ui/toast';
import type { ExternalConnection } from '@/stores/useExternalConnectionsStore';

const EXTERNAL_CONNECTIONS_QUERY_KEY = 'external_connections';
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || '';

// Types
interface StoreTokensParams {
  serviceName: string;
  accessToken: string;
  refreshToken?: string;
  expiresAt?: Date;
  scopes?: string[];
  serviceUserId?: string;
  serviceUserEmail?: string;
}

interface ConnectionStatusResponse {
  connected: boolean;
  count: number;
  service: string;
}

interface ConnectionInfoResponse {
  found: boolean;
  id?: string;
  service_name?: string;
  service_user_id?: string;
  service_user_email?: string;
  scopes?: string[];
  token_expires_at?: string;
  is_active?: boolean;
  created_at?: string;
  updated_at?: string;
}

interface ListConnectionsResponse {
  connections: ExternalConnection[];
}

/** Get current session or throw. Per A5, auth comes from supabase.auth.getSession(). */
async function getSession() {
  const { data: { session } } = await supabase.auth.getSession();
  if (!session) throw new Error('User not authenticated');
  return session;
}

/**
 * Hook to store OAuth tokens via backend endpoint.
 * The backend handles Vault encryption and enqueues the email onboarding job.
 */
export function useStoreTokens() {
  const queryClient = useQueryClient();

  return useMutation<unknown, Error, StoreTokensParams>({
    mutationFn: async (params) => {
      const session = await getSession();

      const response = await fetch(`${API_BASE_URL}/oauth/gmail/store-tokens`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${session.access_token}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          access_token: params.accessToken,
          refresh_token: params.refreshToken || null,
          expires_at: params.expiresAt?.toISOString() || null,
          scopes: params.scopes || [],
          service_user_id: params.serviceUserId || null,
          service_user_email: params.serviceUserEmail || null,
        }),
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({ detail: 'Failed to store tokens' }));
        throw new Error(errorData.detail || `HTTP ${response.status}`);
      }

      return response.json();
    },
    onSuccess: (_data, variables) => {
      toast.success(`${variables.serviceName} connected successfully`);
      queryClient.invalidateQueries({ queryKey: [EXTERNAL_CONNECTIONS_QUERY_KEY] });
    },
    onError: (error) => {
      toast.error('Failed to store tokens', error.message);
    },
  });
}

/**
 * Hook to check connection status for a service
 */
export function useConnectionStatus(serviceName: string) {
  return useQuery<ConnectionStatusResponse, Error>({
    queryKey: [EXTERNAL_CONNECTIONS_QUERY_KEY, 'status', serviceName],
    queryFn: async () => {
      const session = await getSession();

      const { data, error } = await supabase.rpc('check_connection_status', {
        p_user_id: session.user.id,
        p_service_name: serviceName,
      });

      if (error) throw error;
      return data as ConnectionStatusResponse;
    },
    enabled: !!serviceName,
    staleTime: 30000,
  });
}

/**
 * Hook to get detailed connection info for a service
 */
export function useConnectionInfo(serviceName: string) {
  return useQuery<ConnectionInfoResponse, Error>({
    queryKey: [EXTERNAL_CONNECTIONS_QUERY_KEY, 'info', serviceName],
    queryFn: async () => {
      const session = await getSession();

      const { data, error } = await supabase.rpc('get_connection_info', {
        p_user_id: session.user.id,
        p_service_name: serviceName,
      });

      if (error) throw error;
      return data as ConnectionInfoResponse;
    },
    enabled: !!serviceName,
  });
}

/**
 * Hook to list all user connections
 */
export function useListConnections() {
  return useQuery<ExternalConnection[], Error>({
    queryKey: [EXTERNAL_CONNECTIONS_QUERY_KEY],
    queryFn: async () => {
      const session = await getSession();

      const { data, error } = await supabase.rpc('list_user_connections', {
        p_user_id: session.user.id,
      });

      if (error) throw error;

      const response = data as ListConnectionsResponse;
      return response.connections || [];
    },
  });
}

/**
 * Hook to revoke tokens for a service (all connections)
 */
export function useRevokeTokens() {
  const queryClient = useQueryClient();

  return useMutation<unknown, Error, string>({
    mutationFn: async (serviceName) => {
      const session = await getSession();

      const { data, error } = await supabase.rpc('revoke_oauth_tokens', {
        p_user_id: session.user.id,
        p_service_name: serviceName,
      });

      if (error) throw error;
      return data;
    },
    onSuccess: (_data, serviceName) => {
      toast.success(`${serviceName} disconnected successfully`);
      queryClient.invalidateQueries({ queryKey: [EXTERNAL_CONNECTIONS_QUERY_KEY] });
    },
    onError: (error) => {
      toast.error('Failed to revoke tokens', error.message);
    },
  });
}

/**
 * Hook to list all Gmail connections for the current user.
 * Filters list_user_connections to service_name='gmail'.
 */
export function useGmailConnections() {
  return useQuery<ExternalConnection[], Error>({
    queryKey: [EXTERNAL_CONNECTIONS_QUERY_KEY, 'gmail', 'all'],
    queryFn: async () => {
      const session = await getSession();

      const { data, error } = await supabase.rpc('list_user_connections', {
        p_user_id: session.user.id,
      });

      if (error) throw error;

      const response = data as ListConnectionsResponse;
      return (response.connections || []).filter(
        (c) => c.service_name === 'gmail' && c.is_active
      );
    },
    staleTime: 30000,
  });
}

/**
 * Hook to disconnect a specific connection by ID.
 * Used for multi-account services like Gmail.
 */
export function useDisconnectConnection() {
  const queryClient = useQueryClient();

  return useMutation<unknown, Error, string>({
    mutationFn: async (connectionId) => {
      const session = await getSession();

      const { data, error } = await supabase.rpc('revoke_oauth_tokens', {
        p_user_id: session.user.id,
        p_service_name: 'gmail',
        p_connection_id: connectionId,
      });

      if (error) throw error;
      return data;
    },
    onSuccess: () => {
      toast.success('Gmail account disconnected');
      queryClient.invalidateQueries({ queryKey: [EXTERNAL_CONNECTIONS_QUERY_KEY] });
    },
    onError: (error) => {
      toast.error('Failed to disconnect account', error.message);
    },
  });
}
