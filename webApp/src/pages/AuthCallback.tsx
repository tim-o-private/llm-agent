import React, { useEffect, useRef, useState } from 'react';
import { useSearchParams, useNavigate } from 'react-router-dom';
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

export const AuthCallback: React.FC = () => {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const [status, setStatus] = useState<CallbackStatus>({
    isProcessing: true,
    isComplete: false,
    isError: false,
    message: 'Processing authentication...',
  });
  const hasProcessedRef = useRef(false);

  useEffect(() => {
    // Ref guard survives React StrictMode double-effect (state doesn't)
    if (hasProcessedRef.current) return;
    hasProcessedRef.current = true;

    handleAuthCallback();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const handleAuthCallback = async () => {

    try {
      const service = searchParams.get('service');
      const callbackStatus = searchParams.get('status');
      const errorMessage = searchParams.get('error_message');

      setStatus((prev) => ({
        ...prev,
        message: 'Verifying authentication...',
      }));

      // Handle backend OAuth callback (Gmail, Calendar — all via standalone flow)
      if (service === 'gmail' || service === 'google_calendar') {
        const displayService = service === 'google_calendar' ? 'Calendar' : 'Gmail';
        setStatus((prev) => ({
          ...prev,
          message: `Processing ${displayService} account connection...`,
          service,
        }));

        if (callbackStatus === 'success') {
          setStatus({
            isProcessing: false,
            isComplete: true,
            isError: false,
            message: `${displayService} account connected successfully!`,
            service,
          });
        } else {
          throw new Error(
            errorMessage
              ? decodeURIComponent(errorMessage)
              : `Failed to connect ${displayService} account. Please try again.`
          );
        }

        setTimeout(() => {
          navigate('/today');
        }, 2000);
      } else {
        // Handle regular login callback
        setStatus({
          isProcessing: false,
          isComplete: true,
          isError: false,
          message: 'Authentication successful! Redirecting...',
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
        message: error instanceof Error ? error.message : 'Authentication failed',
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
        <div className="mb-6">{getIcon()}</div>

        <h1 className="text-2xl font-bold mb-4">
          {status.service === 'gmail' ? 'Gmail Integration' : 'Authentication'}
        </h1>

        <p className={`text-lg mb-6 ${getStatusColor()}`}>{status.message}</p>

        {status.isError && (
          <div className="space-y-4">
            <div className="text-sm text-gray-600">If this error persists, please try again or contact support.</div>
            <Button onClick={() => navigate('/today')} variant="outline" className="w-full">
              <ArrowLeft className="mr-2 h-4 w-4" />
              Return to Dashboard
            </Button>
          </div>
        )}

        {status.isProcessing && (
          <div className="text-sm text-gray-600">Please wait while we complete the authentication process...</div>
        )}

        {status.isComplete && !status.isError && (
          <div className="text-sm text-gray-600">
            {status.service === 'gmail'
              ? 'You will be redirected to your dashboard shortly...'
              : 'Redirecting to your dashboard...'}
          </div>
        )}
      </Card>
    </div>
  );
};
