import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { supabase } from '@/lib/supabaseClient';
import { useAuthStore } from '@/features/auth/useAuthStore';
import { toast } from '@/components/ui/toast';
import type { ExternalConnection } from '@/stores/useExternalConnectionsStore';

const EXTERNAL_CONNECTIONS_QUERY_KEY = 'external_connections';

// Types for RPC function parameters
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

/**
 * Hook to store OAuth tokens using Vault
 */
export function useStoreTokens() {
  const queryClient = useQueryClient();
  const user = useAuthStore((state) => state.user);

  return useMutation<any, Error, StoreTokensParams>({
    mutationFn: async (params) => {
      if (!user) throw new Error('User not authenticated');

      const { data, error } = await supabase.rpc('store_oauth_tokens', {
        p_user_id: user.id,
        p_service_name: params.serviceName,
        p_access_token: params.accessToken,
        p_refresh_token: params.refreshToken || null,
        p_expires_at: params.expiresAt?.toISOString() || null,
        p_scopes: params.scopes || [],
        p_service_user_id: params.serviceUserId || null,
        p_service_user_email: params.serviceUserEmail || null,
      });

      if (error) throw error;
      return data;
    },
    onSuccess: (_data, variables) => {
      toast.success(`${variables.serviceName} connected successfully`);
      // Invalidate connections list to refresh UI
      queryClient.invalidateQueries({ queryKey: [EXTERNAL_CONNECTIONS_QUERY_KEY, user?.id] });
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
  const user = useAuthStore((state) => state.user);

  return useQuery<ConnectionStatusResponse, Error>({
    queryKey: [EXTERNAL_CONNECTIONS_QUERY_KEY, user?.id, 'status', serviceName],
    queryFn: async () => {
      if (!user) throw new Error('User not authenticated');

      const { data, error } = await supabase.rpc('check_connection_status', {
        p_user_id: user.id,
        p_service_name: serviceName,
      });

      if (error) throw error;
      return data as ConnectionStatusResponse;
    },
    enabled: !!user && !!serviceName,
    staleTime: 30000, // Consider data fresh for 30 seconds
  });
}

/**
 * Hook to get detailed connection info for a service
 */
export function useConnectionInfo(serviceName: string) {
  const user = useAuthStore((state) => state.user);

  return useQuery<ConnectionInfoResponse, Error>({
    queryKey: [EXTERNAL_CONNECTIONS_QUERY_KEY, user?.id, 'info', serviceName],
    queryFn: async () => {
      if (!user) throw new Error('User not authenticated');

      const { data, error } = await supabase.rpc('get_connection_info', {
        p_user_id: user.id,
        p_service_name: serviceName,
      });

      if (error) throw error;
      return data as ConnectionInfoResponse;
    },
    enabled: !!user && !!serviceName,
  });
}

/**
 * Hook to list all user connections
 */
export function useListConnections() {
  const user = useAuthStore((state) => state.user);

  return useQuery<ExternalConnection[], Error>({
    queryKey: [EXTERNAL_CONNECTIONS_QUERY_KEY, user?.id],
    queryFn: async () => {
      if (!user) throw new Error('User not authenticated');

      const { data, error } = await supabase.rpc('list_user_connections', {
        p_user_id: user.id,
      });

      if (error) throw error;

      const response = data as ListConnectionsResponse;
      return response.connections || [];
    },
    enabled: !!user,
  });
}

/**
 * Hook to revoke tokens for a service (all connections)
 */
export function useRevokeTokens() {
  const queryClient = useQueryClient();
  const user = useAuthStore((state) => state.user);

  return useMutation<any, Error, string>({
    mutationFn: async (serviceName) => {
      if (!user) throw new Error('User not authenticated');

      const { data, error } = await supabase.rpc('revoke_oauth_tokens', {
        p_user_id: user.id,
        p_service_name: serviceName,
      });

      if (error) throw error;
      return data;
    },
    onSuccess: (_data, serviceName) => {
      toast.success(`${serviceName} disconnected successfully`);
      // Invalidate connections list to refresh UI
      queryClient.invalidateQueries({ queryKey: [EXTERNAL_CONNECTIONS_QUERY_KEY, user?.id] });
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
  const user = useAuthStore((state) => state.user);

  return useQuery<ExternalConnection[], Error>({
    queryKey: [EXTERNAL_CONNECTIONS_QUERY_KEY, user?.id, 'gmail', 'all'],
    queryFn: async () => {
      if (!user) throw new Error('User not authenticated');

      const { data, error } = await supabase.rpc('list_user_connections', {
        p_user_id: user.id,
      });

      if (error) throw error;

      const response = data as ListConnectionsResponse;
      return (response.connections || []).filter(
        (c) => c.service_name === 'gmail' && c.is_active
      );
    },
    enabled: !!user,
    staleTime: 30000,
  });
}

/**
 * Hook to disconnect a specific connection by ID.
 * Used for multi-account services like Gmail.
 */
export function useDisconnectConnection() {
  const queryClient = useQueryClient();
  const user = useAuthStore((state) => state.user);

  return useMutation<any, Error, string>({
    mutationFn: async (connectionId) => {
      if (!user) throw new Error('User not authenticated');

      const { data, error } = await supabase.rpc('revoke_oauth_tokens', {
        p_user_id: user.id,
        p_service_name: 'gmail',
        p_connection_id: connectionId,
      });

      if (error) throw error;
      return data;
    },
    onSuccess: () => {
      toast.success('Gmail account disconnected');
      queryClient.invalidateQueries({ queryKey: [EXTERNAL_CONNECTIONS_QUERY_KEY, user?.id] });
    },
    onError: (error) => {
      toast.error('Failed to disconnect account', error.message);
    },
  });
}
