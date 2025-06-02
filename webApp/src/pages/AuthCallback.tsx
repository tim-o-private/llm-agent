import React, { useEffect, useState } from 'react';
import { useSearchParams, useNavigate } from 'react-router-dom';
import { supabase } from '@/lib/supabaseClient';
import { useStoreTokens } from '@/api/hooks/useExternalConnectionsHooks';
import { Card } from '../components/ui/Card';
import { Button } from '../components/ui/Button';
import { CheckCircle, AlertCircle, Loader2, Mail, ArrowLeft } from 'lucide-react';

interface CallbackStatus {
  isProcessing: boolean;
  isComplete: boolean;
  isError: boolean;
  message: string;
  service?: string;
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
    : 'border-green-200 bg-green-50 text-green-800';
  
  return (
    <div className={`${baseClasses} ${variantClasses} ${className}`}>
      {children}
    </div>
  );
};

const AlertDescription: React.FC<{ children: React.ReactNode; className?: string }> = ({ 
  children, 
  className = '' 
}) => (
  <div className={`text-sm ${className}`}>{children}</div>
);

export const AuthCallback: React.FC = () => {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const [status, setStatus] = useState<CallbackStatus>({
    isProcessing: true,
    isComplete: false,
    isError: false,
    message: 'Processing authentication...'
  });
  const [hasProcessed, setHasProcessed] = useState(false);

  const storeTokensMutation = useStoreTokens();

  useEffect(() => {
    // Prevent duplicate processing
    if (hasProcessed) return;
    
    handleAuthCallback();
  }, [hasProcessed]); // Only depend on hasProcessed

  const handleAuthCallback = async () => {
    // Mark as processed immediately to prevent duplicates
    setHasProcessed(true);
    
    try {
      const service = searchParams.get('service');
      
      setStatus(prev => ({
        ...prev,
        message: 'Verifying authentication...'
      }));

      // Handle Gmail OAuth callback
      if (service === 'gmail') {
        setStatus(prev => ({
          ...prev,
          message: 'Processing Gmail authentication...',
          service: 'gmail'
        }));

        // First, let Supabase handle the OAuth callback
        const { data, error } = await supabase.auth.getSession();
        
        if (error) {
          throw new Error(`Session error: ${error.message}`);
        }

        // Wait a moment for the session to be fully established
        await new Promise(resolve => setTimeout(resolve, 1000));
        
        // Get the updated session
        const { data: { session }, error: sessionError } = await supabase.auth.getSession();
        
        if (sessionError) {
          throw new Error(`Session error: ${sessionError.message}`);
        }

        if (!session) {
          throw new Error('No authentication session found');
        }

        console.log('Session data:', {
          hasProviderToken: !!session.provider_token,
          hasProviderRefreshToken: !!session.provider_refresh_token,
          expiresAt: session.expires_at,
          userEmail: session.user?.email,
          providerId: session.user?.user_metadata?.provider_id
        });

        // Check if we have provider tokens
        if (!session.provider_token) {
          throw new Error('No Gmail access token received from Google. Please try connecting again.');
        }

        setStatus(prev => ({
          ...prev,
          message: 'Storing Gmail tokens securely...'
        }));

        // Store Gmail tokens using RPC function
        await storeTokensMutation.mutateAsync({
          serviceName: 'gmail',
          accessToken: session.provider_token,
          refreshToken: session.provider_refresh_token || undefined,
          expiresAt: session.expires_at ? new Date(session.expires_at * 1000) : undefined,
          scopes: ['https://www.googleapis.com/auth/gmail.readonly'],
          serviceUserId: session.user?.user_metadata?.provider_id || undefined,
          serviceUserEmail: session.user?.email || undefined
        });

        setStatus({
          isProcessing: false,
          isComplete: true,
          isError: false,
          message: 'Gmail connected successfully! You can now access your email digest.',
          service: 'gmail'
        });

        // Redirect to today view after a short delay
        setTimeout(() => {
          navigate('/today');
        }, 2000);

      } else {
        // Handle regular login callback
        setStatus({
          isProcessing: false,
          isComplete: true,
          isError: false,
          message: 'Authentication successful! Redirecting...'
        });

        setTimeout(() => {
          navigate('/today');
        }, 1000);
      }

    } catch (error) {
      console.error('Auth callback error:', error);
      setStatus({
        isProcessing: false,
        isComplete: false,
        isError: true,
        message: error instanceof Error ? error.message : 'Authentication failed'
      });
    }
  };

  const getIcon = () => {
    if (status.isProcessing) {
      return <Loader2 className="h-8 w-8 animate-spin text-blue-600" />;
    }
    if (status.isError) {
      return <AlertCircle className="h-8 w-8 text-red-600" />;
    }
    if (status.service === 'gmail') {
      return <Mail className="h-8 w-8 text-green-600" />;
    }
    return <CheckCircle className="h-8 w-8 text-green-600" />;
  };

  const getStatusColor = () => {
    if (status.isError) return 'text-red-600';
    if (status.isComplete) return 'text-green-600';
    return 'text-blue-600';
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50 px-4">
      <Card className="w-full max-w-md p-8 text-center">
        <div className="mb-6">
          {getIcon()}
        </div>
        
        <h1 className="text-2xl font-bold mb-4">
          {status.service === 'gmail' ? 'Gmail Integration' : 'Authentication'}
        </h1>
        
        <p className={`text-lg mb-6 ${getStatusColor()}`}>
          {status.message}
        </p>

        {status.isError && (
          <div className="space-y-4">
            <div className="text-sm text-gray-600">
              If this error persists, please try again or contact support.
            </div>
            <Button 
              onClick={() => navigate('/today')}
              variant="outline"
              className="w-full"
            >
              <ArrowLeft className="mr-2 h-4 w-4" />
              Return to Dashboard
            </Button>
          </div>
        )}

        {status.isProcessing && (
          <div className="text-sm text-gray-600">
            Please wait while we complete the authentication process...
          </div>
        )}

        {status.isComplete && !status.isError && (
          <div className="text-sm text-gray-600">
            {status.service === 'gmail' 
              ? 'You will be redirected to your dashboard shortly...'
              : 'Redirecting to your dashboard...'
            }
          </div>
        )}
      </Card>
    </div>
  );
}; 