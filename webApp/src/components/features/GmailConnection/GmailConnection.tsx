import React, { useState, useEffect } from 'react';
import { Button } from '../../ui/Button';
import { Card } from '../../ui/Card';
import { Badge } from '../../ui/Badge';
import { CheckCircle, Mail, AlertCircle, Loader2, Plus, Trash2 } from 'lucide-react';
import { supabase } from '@/lib/supabaseClient';
import { useAuthStore } from '@/features/auth/useAuthStore';
import {
  useConnectionStatus,
  useGmailConnections,
  useDisconnectConnection,
  useRevokeTokens,
} from '@/api/hooks/useExternalConnectionsHooks';

const MAX_GMAIL_ACCOUNTS = 5;

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || '';

interface GmailConnectionProps {
  onConnectionChange?: (isConnected: boolean) => void;
  className?: string;
}

export const GmailConnection: React.FC<GmailConnectionProps> = ({ onConnectionChange, className = '' }) => {
  const [isConnecting, setIsConnecting] = useState(false);
  const { signInWithProvider } = useAuthStore();

  const {
    data: connectionStatus,
    isLoading: isCheckingStatus,
    error: statusError,
    refetch: refetchStatus,
  } = useConnectionStatus('gmail');

  const {
    data: gmailAccounts,
    isLoading: isLoadingAccounts,
    refetch: refetchAccounts,
  } = useGmailConnections();

  const disconnectMutation = useDisconnectConnection();
  const revokeAllMutation = useRevokeTokens();

  const accountCount = connectionStatus?.count ?? gmailAccounts?.length ?? 0;
  const hasAccounts = accountCount > 0;
  const canAddMore = accountCount < MAX_GMAIL_ACCOUNTS;

  useEffect(() => {
    if (connectionStatus) {
      onConnectionChange?.(connectionStatus.connected);
    }
  }, [connectionStatus?.connected, onConnectionChange]);

  const connectFirstGmail = async () => {
    setIsConnecting(true);
    try {
      await signInWithProvider('google', true);
    } catch (error) {
      console.error('Gmail connection failed:', error);
      setIsConnecting(false);
    }
  };

  const connectAdditionalGmail = async () => {
    setIsConnecting(true);
    try {
      const { data: { session } } = await supabase.auth.getSession();
      if (!session) {
        console.error('No active session for standalone OAuth');
        setIsConnecting(false);
        return;
      }

      const response = await fetch(`${API_BASE_URL}/oauth/gmail/connect`, {
        headers: { Authorization: `Bearer ${session.access_token}` },
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({ detail: 'Failed to start OAuth flow' }));
        throw new Error(errorData.detail || `HTTP ${response.status}`);
      }

      const { auth_url } = await response.json();
      window.location.href = auth_url;
    } catch (error) {
      console.error('Failed to initiate additional Gmail OAuth:', error);
      setIsConnecting(false);
    }
  };

  const disconnectAccount = async (connectionId: string) => {
    await disconnectMutation.mutateAsync(connectionId);
    refetchAccounts();
    refetchStatus();
  };

  const getStatusBadge = () => {
    if (isCheckingStatus || disconnectMutation.isPending || revokeAllMutation.isPending) {
      return (
        <Badge className="flex items-center gap-1 bg-gray-100 text-gray-700">
          <Loader2 className="h-3 w-3 animate-spin" />
          {disconnectMutation.isPending || revokeAllMutation.isPending ? 'Disconnecting...' : 'Checking...'}
        </Badge>
      );
    }

    if (hasAccounts) {
      return (
        <Badge className="flex items-center gap-1 bg-green-100 text-green-800">
          <CheckCircle className="h-3 w-3" />
          {accountCount} of {MAX_GMAIL_ACCOUNTS} connected
        </Badge>
      );
    }

    return (
      <Badge className="flex items-center gap-1 bg-yellow-100 text-yellow-800">
        <AlertCircle className="h-3 w-3" />
        Not Connected
      </Badge>
    );
  };

  const hasError = statusError || disconnectMutation.error || revokeAllMutation.error;
  const errorMessage =
    statusError?.message || disconnectMutation.error?.message || revokeAllMutation.error?.message;

  return (
    <Card className={`p-6 ${className}`}>
      <div className="mb-4">
        <div className="flex items-center justify-between mb-2">
          <div className="flex items-center gap-2">
            <Mail className="h-5 w-5 text-blue-600" />
            <h3 className="text-lg font-semibold">Gmail Accounts</h3>
          </div>
          {getStatusBadge()}
        </div>
        <p className="text-gray-600 text-sm">
          Connect up to {MAX_GMAIL_ACCOUNTS} Gmail accounts for comprehensive email digest and search.
        </p>
      </div>

      <div className="space-y-4">
        {hasError && (
          <div className="p-4 rounded-lg border border-red-200 bg-red-50 text-red-800 flex items-start gap-3">
            <AlertCircle className="h-4 w-4 mt-0.5" />
            <div className="text-sm">{errorMessage}</div>
          </div>
        )}

        {/* Connected accounts list */}
        {hasAccounts && gmailAccounts && gmailAccounts.length > 0 && (
          <div className="space-y-2">
            {gmailAccounts.map((account) => (
              <div
                key={account.id}
                className="flex items-center justify-between p-3 rounded-lg border border-gray-200 bg-gray-50"
              >
                <div className="flex items-center gap-2">
                  <Mail className="h-4 w-4 text-gray-500" />
                  <div>
                    <div className="text-sm font-medium">{account.service_user_email || 'Unknown email'}</div>
                    <div className="text-xs text-gray-500">
                      Connected {new Date(account.created_at).toLocaleDateString()}
                    </div>
                  </div>
                </div>
                <Button
                  variant="ghost"
                  color="red"
                  size="1"
                  onClick={() => disconnectAccount(account.id)}
                  disabled={disconnectMutation.isPending}
                >
                  {disconnectMutation.isPending ? (
                    <Loader2 className="h-3 w-3 animate-spin" />
                  ) : (
                    <Trash2 className="h-3 w-3" />
                  )}
                </Button>
              </div>
            ))}
          </div>
        )}

        {/* Loading state */}
        {isLoadingAccounts && hasAccounts && (
          <div className="flex items-center gap-2 text-sm text-gray-500">
            <Loader2 className="h-4 w-4 animate-spin" />
            Loading accounts...
          </div>
        )}

        {/* Actions */}
        <div className="flex flex-col gap-2">
          {!hasAccounts ? (
            <Button onClick={connectFirstGmail} disabled={isConnecting || isCheckingStatus} className="w-full">
              {isConnecting ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  Connecting...
                </>
              ) : (
                <>
                  <Mail className="mr-2 h-4 w-4" />
                  Connect Gmail
                </>
              )}
            </Button>
          ) : (
            <div className="flex gap-2">
              {canAddMore && (
                <Button
                  variant="outline"
                  onClick={connectAdditionalGmail}
                  disabled={isConnecting}
                  size="1"
                  className="flex-1"
                >
                  <Plus className="mr-1 h-3 w-3" />
                  Add Gmail Account
                </Button>
              )}
              <Button
                variant="outline"
                onClick={() => { refetchStatus(); refetchAccounts(); }}
                disabled={isCheckingStatus || isLoadingAccounts}
                size="1"
              >
                {isCheckingStatus ? <Loader2 className="h-3 w-3 animate-spin" /> : 'Refresh'}
              </Button>
            </div>
          )}
        </div>
      </div>
    </Card>
  );
};
