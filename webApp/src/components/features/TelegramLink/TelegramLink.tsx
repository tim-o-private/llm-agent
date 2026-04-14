/**
 * Telegram account linking component for Settings/Integrations page.
 *
 * Shows current link status and provides a flow to connect or disconnect
 * the user's Telegram account for receiving notifications.
 */

import React, { useState } from 'react';
import { QRCodeSVG } from 'qrcode.react';
import { Card } from '@/components/ui/Card';
import { useTelegramStatus, useGenerateLinkToken, useUnlinkTelegram } from '@/api/hooks/useTelegramHooks';

export const TelegramLink: React.FC = () => {
  const { data: status, isLoading } = useTelegramStatus();
  const generateToken = useGenerateLinkToken();
  const unlinkMutation = useUnlinkTelegram();
  const [showConfirmUnlink, setShowConfirmUnlink] = useState(false);

  const isLinked = status?.linked ?? false;

  const handleGenerateToken = () => {
    generateToken.mutate();
  };

  const handleUnlink = () => {
    unlinkMutation.mutate(undefined, {
      onSuccess: () => setShowConfirmUnlink(false),
    });
  };

  return (
    <Card className="p-6">
      <div className="flex items-center gap-3 mb-3">
        <div className="w-8 h-8 bg-info-subtle rounded flex items-center justify-center text-sm">TG</div>
        <h3 className="text-lg font-semibold text-text-primary">Telegram</h3>
        {isLinked && <span className="text-sm bg-success-subtle text-success-strong px-2 py-1 rounded">Connected</span>}
      </div>

      <p className="text-text-secondary text-sm mb-4">
        Connect Telegram to receive agent notifications, approve actions, and chat with your agents directly.
      </p>

      {isLoading ? (
        <p className="text-text-muted text-sm">Checking status...</p>
      ) : isLinked ? (
        <LinkedState
          linkedAt={status?.linked_at ?? null}
          showConfirm={showConfirmUnlink}
          onShowConfirm={() => setShowConfirmUnlink(true)}
          onCancel={() => setShowConfirmUnlink(false)}
          onUnlink={handleUnlink}
          isUnlinking={unlinkMutation.isPending}
        />
      ) : (
        <UnlinkedState
          tokenData={generateToken.data ?? null}
          onGenerate={handleGenerateToken}
          isGenerating={generateToken.isPending}
          error={generateToken.error?.message ?? null}
        />
      )}
    </Card>
  );
};

// --- Sub-components ---

interface LinkedStateProps {
  linkedAt: string | null;
  showConfirm: boolean;
  onShowConfirm: () => void;
  onCancel: () => void;
  onUnlink: () => void;
  isUnlinking: boolean;
}

const LinkedState: React.FC<LinkedStateProps> = ({
  linkedAt,
  showConfirm,
  onShowConfirm,
  onCancel,
  onUnlink,
  isUnlinking,
}) => (
  <div className="space-y-3">
    {linkedAt && <p className="text-text-muted text-xs">Connected {new Date(linkedAt).toLocaleDateString()}</p>}

    {showConfirm ? (
      <div className="flex items-center gap-2">
        <span className="text-text-secondary text-sm">Disconnect Telegram?</span>
        <button
          onClick={onUnlink}
          disabled={isUnlinking}
          className="px-3 py-1 text-sm rounded bg-danger-bg text-text-primary hover:opacity-80 disabled:opacity-50"
        >
          {isUnlinking ? 'Disconnecting...' : 'Yes, disconnect'}
        </button>
        <button
          onClick={onCancel}
          className="px-3 py-1 text-sm rounded bg-ui-interactive-bg text-text-secondary hover:bg-ui-interactive-bg-hover"
        >
          Cancel
        </button>
      </div>
    ) : (
      <button
        onClick={onShowConfirm}
        className="px-3 py-1.5 text-sm rounded bg-ui-interactive-bg text-text-secondary hover:bg-ui-interactive-bg-hover"
      >
        Disconnect
      </button>
    )}
  </div>
);

interface UnlinkedStateProps {
  tokenData: { token: string; bot_username: string } | null;
  onGenerate: () => void;
  isGenerating: boolean;
  error: string | null;
}

const UnlinkedState: React.FC<UnlinkedStateProps> = ({ tokenData, onGenerate, isGenerating, error }) => {
  const deepLink = tokenData ? `https://t.me/${tokenData.bot_username}?start=${tokenData.token}` : null;

  return (
    <div className="space-y-3">
      {!tokenData ? (
        <>
          <button
            onClick={onGenerate}
            disabled={isGenerating}
            className="px-4 py-2 text-sm rounded bg-brand-primary text-brand-primary-text hover:bg-brand-primary-hover disabled:opacity-50"
          >
            {isGenerating ? 'Generating...' : 'Connect Telegram'}
          </button>
          {error && <p className="text-destructive text-sm">{error}</p>}
        </>
      ) : (
        <div className="space-y-4 p-4 rounded bg-ui-bg-alt border border-ui-border">
          <p className="text-text-primary text-sm font-medium">Connect your Telegram account:</p>

          <div className="flex flex-col sm:flex-row gap-4">
            {/* QR code for scanning from phone */}
            <div className="flex flex-col items-center gap-2">
              <div className="p-3 bg-white rounded-lg">
                <QRCodeSVG value={deepLink!} size={160} />
              </div>
              <p className="text-text-muted text-xs text-center">Scan with your phone camera</p>
            </div>

            {/* Text instructions */}
            <div className="flex-1 space-y-3">
              <p className="text-text-secondary text-sm">Scan the QR code, or:</p>
              <ol className="text-text-secondary text-sm space-y-2 list-decimal list-inside">
                <li>
                  <a
                    href={deepLink!}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-text-accent underline hover:opacity-80"
                  >
                    Open in Telegram
                  </a>
                </li>
                <li>
                  Or search for <span className="font-mono text-text-accent">@{tokenData.bot_username}</span> and send:
                </li>
              </ol>
              <div className="flex items-center gap-2">
                <code className="flex-1 block p-2 rounded bg-ui-bg text-text-primary text-sm font-mono break-all border border-ui-border">
                  /start {tokenData.token}
                </code>
                <button
                  onClick={() => navigator.clipboard.writeText(`/start ${tokenData.token}`)}
                  className="px-3 py-2 text-sm rounded bg-ui-interactive-bg text-text-secondary hover:bg-ui-interactive-bg-hover shrink-0"
                >
                  Copy
                </button>
              </div>
            </div>
          </div>

          <p className="text-text-muted text-xs">This token expires in 10 minutes.</p>
        </div>
      )}
    </div>
  );
};
