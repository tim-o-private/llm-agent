import React, { useState, useEffect } from 'react';
import { Button } from '../../ui/Button';
import { Card } from '../../ui/Card';
import { Badge } from '../../ui/Badge';
import { CheckCircle, Mail, AlertCircle, Loader2 } from 'lucide-react';
import { useAuthStore } from '@/features/auth/useAuthStore';
import { useConnectionStatus, useRevokeTokens } from '@/api/hooks/useExternalConnectionsHooks';

interface GmailConnectionProps {
  onConnectionChange?: (isConnected: boolean) => void;
  className?: string;
}

// Simple Alert component using existing styles
const Alert: React.FC<{ 
  variant?: 'default' | 'destructive'; 
  className?: string; 
  children: React.ReactNode 
}> = ({ variant = 'default', className = '', children }) => {
  const baseClasses = 'p-4 rounded-lg border flex items-start gap-3';
  const variantClasses = variant === 'destructive' 
    ? 'border-red-200 bg-red-50 text-red-800' 
    : 'border-blue-200 bg-blue-50 text-blue-800';
  
  return (
    <div className={`${baseClasses} ${variantClasses} ${className}`}>
      {children}
    </div>
  );
};

const AlertDescription: React.FC<{ children: React.ReactNode }> = ({ children }) => (
  <div className="text-sm">{children}</div>
);

export const GmailConnection: React.FC<GmailConnectionProps> = ({
  onConnectionChange,
  className = ''
}) => {
  const [isConnecting, setIsConnecting] = useState(false);
  const { signInWithProvider } = useAuthStore();
  
  // Use React Query hooks for connection management
  const { 
    data: connectionStatus, 
    isLoading: isCheckingStatus, 
    error: statusError,
    refetch: refetchStatus 
  } = useConnectionStatus('gmail');
  
  const revokeTokensMutation = useRevokeTokens();

  // Notify parent component of connection changes
  useEffect(() => {
    if (connectionStatus) {
      onConnectionChange?.(connectionStatus.connected);
    }
  }, [connectionStatus?.connected, onConnectionChange]);

  const connectGmail = async () => {
    setIsConnecting(true);

    try {
      // Use the same OAuth pattern as working login, with Gmail scopes
      await signInWithProvider('google', true);
      
      // OAuth redirect will happen automatically
      // The callback handler will process the tokens
      
    } catch (error) {
      console.error('Gmail connection failed:', error);
      setIsConnecting(false);
    }
  };

  const disconnectGmail = async () => {
    try {
      await revokeTokensMutation.mutateAsync('gmail');
      // The mutation will automatically invalidate queries and update UI
    } catch (error) {
      console.error('Failed to disconnect Gmail:', error);
    }
  };

  const getStatusBadge = () => {
    if (isCheckingStatus || revokeTokensMutation.isPending) {
      return (
        <Badge className="flex items-center gap-1 bg-gray-100 text-gray-700">
          <Loader2 className="h-3 w-3 animate-spin" />
          {revokeTokensMutation.isPending ? 'Disconnecting...' : 'Checking...'}
        </Badge>
      );
    }

    if (connectionStatus?.connected) {
      return (
        <Badge className="flex items-center gap-1 bg-green-100 text-green-800">
          <CheckCircle className="h-3 w-3" />
          Connected
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

  const hasError = statusError || revokeTokensMutation.error;
  const errorMessage = statusError?.message || revokeTokensMutation.error?.message;

  return (
    <Card className={`p-6 ${className}`}>
      <div className="mb-4">
        <div className="flex items-center justify-between mb-2">
          <div className="flex items-center gap-2">
            <Mail className="h-5 w-5 text-blue-600" />
            <h3 className="text-lg font-semibold">Gmail Connection</h3>
          </div>
          {getStatusBadge()}
        </div>
        <p className="text-gray-600 text-sm">
          Connect your Gmail account to enable email digest and search functionality.
        </p>
      </div>

      <div className="space-y-4">
        {hasError && (
          <Alert variant="destructive">
            <AlertCircle className="h-4 w-4" />
            <AlertDescription>{errorMessage}</AlertDescription>
          </Alert>
        )}

        <div className="flex flex-col gap-3">
          {!connectionStatus?.connected ? (
            <Button 
              onClick={connectGmail}
              disabled={isConnecting || isCheckingStatus}
              className="w-full"
            >
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
            <div className="space-y-2">
              <div className="flex items-center gap-2 text-sm text-green-600">
                <CheckCircle className="h-4 w-4" />
                Gmail is connected and ready to use
              </div>
              <div className="flex gap-2">
                <Button 
                  variant="outline" 
                  onClick={() => refetchStatus()}
                  disabled={isCheckingStatus}
                  size="1"
                >
                  {isCheckingStatus ? (
                    <Loader2 className="h-3 w-3 animate-spin" />
                  ) : (
                    'Refresh Status'
                  )}
                </Button>
                <Button 
                  variant="soft" 
                  color="red"
                  onClick={disconnectGmail}
                  disabled={revokeTokensMutation.isPending}
                  size="1"
                >
                  {revokeTokensMutation.isPending ? (
                    <>
                      <Loader2 className="mr-1 h-3 w-3 animate-spin" />
                      Disconnecting...
                    </>
                  ) : (
                    'Disconnect'
                  )}
                </Button>
              </div>
            </div>
          )}
        </div>
      </div>
    </Card>
  );
}; 