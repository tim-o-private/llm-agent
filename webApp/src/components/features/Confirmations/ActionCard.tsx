/**
 * ActionCard component for displaying a single pending action.
 *
 * Shows the tool name, arguments, and approve/reject buttons.
 */

import React from 'react';
import { Button } from '../../ui/Button';
import { Card } from '../../ui/Card';
import { Badge } from '../../ui/Badge';
import { Check, X, Clock, AlertTriangle } from 'lucide-react';
import type { PendingAction } from '@/api/hooks/useActionsHooks';

interface ActionCardProps {
  action: PendingAction;
  onApprove: (actionId: string) => void;
  onReject: (actionId: string) => void;
  isApproving?: boolean;
  isRejecting?: boolean;
}

function formatToolName(toolName: string): string {
  return toolName
    .split('_')
    .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
    .join(' ');
}

function formatRelativeTime(dateString: string): string {
  const date = new Date(dateString);
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffMins = Math.floor(diffMs / 60000);
  const diffHours = Math.floor(diffMins / 60);

  if (diffMins < 1) return 'just now';
  if (diffMins < 60) return `${diffMins}m ago`;
  if (diffHours < 24) return `${diffHours}h ago`;
  return date.toLocaleDateString();
}

function formatTimeUntilExpiry(expiresAt: string): string {
  const expiry = new Date(expiresAt);
  const now = new Date();
  const diffMs = expiry.getTime() - now.getTime();

  if (diffMs < 0) return 'Expired';

  const diffMins = Math.floor(diffMs / 60000);
  const diffHours = Math.floor(diffMins / 60);

  if (diffMins < 60) return `${diffMins}m left`;
  if (diffHours < 24) return `${diffHours}h left`;
  return `${Math.floor(diffHours / 24)}d left`;
}

function renderToolArgs(args: Record<string, unknown>): React.ReactNode {
  const entries = Object.entries(args);

  if (entries.length === 0) {
    return <span className="text-gray-400 italic">No arguments</span>;
  }

  return (
    <dl className="space-y-1">
      {entries.slice(0, 5).map(([key, value]) => (
        <div key={key} className="flex gap-2">
          <dt className="text-gray-500 font-medium text-xs">{key}:</dt>
          <dd className="text-gray-700 text-xs truncate max-w-[200px]">
            {typeof value === 'string' ? value : JSON.stringify(value)}
          </dd>
        </div>
      ))}
      {entries.length > 5 && (
        <div className="text-gray-400 text-xs italic">
          +{entries.length - 5} more fields
        </div>
      )}
    </dl>
  );
}

export const ActionCard: React.FC<ActionCardProps> = ({
  action,
  onApprove,
  onReject,
  isApproving = false,
  isRejecting = false,
}) => {
  const isExpiringSoon = new Date(action.expires_at).getTime() - Date.now() < 3600000;

  return (
    <Card className="p-4 border-l-4 border-l-amber-400">
      <div className="flex items-start justify-between gap-4">
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-2">
            <AlertTriangle className="h-4 w-4 text-amber-500" />
            <h4 className="font-semibold text-gray-900">
              {formatToolName(action.tool_name)}
            </h4>
            <Badge className="bg-amber-100 text-amber-800 text-xs">
              Pending Approval
            </Badge>
          </div>

          <div className="bg-gray-50 rounded p-2 mb-2">
            {renderToolArgs(action.tool_args)}
          </div>

          <div className="flex items-center gap-4 text-xs text-gray-500">
            <span className="flex items-center gap-1">
              <Clock className="h-3 w-3" />
              {formatRelativeTime(action.created_at)}
            </span>
            <span className={`flex items-center gap-1 ${isExpiringSoon ? 'text-amber-600 font-medium' : ''}`}>
              {isExpiringSoon && <AlertTriangle className="h-3 w-3" />}
              {formatTimeUntilExpiry(action.expires_at)}
            </span>
            {action.context.agent_name && (
              <span>Agent: {action.context.agent_name as string}</span>
            )}
          </div>
        </div>

        <div className="flex flex-col gap-2">
          <Button
            size="1"
            onClick={() => onApprove(action.id)}
            disabled={isApproving || isRejecting}
            className="bg-green-600 hover:bg-green-700 text-white"
          >
            {isApproving ? (
              <span className="animate-pulse">Approving...</span>
            ) : (
              <>
                <Check className="h-4 w-4 mr-1" />
                Approve
              </>
            )}
          </Button>
          <Button
            size="1"
            variant="outline"
            onClick={() => onReject(action.id)}
            disabled={isApproving || isRejecting}
            className="border-red-300 text-red-600 hover:bg-red-50"
          >
            {isRejecting ? (
              <span className="animate-pulse">Rejecting...</span>
            ) : (
              <>
                <X className="h-4 w-4 mr-1" />
                Reject
              </>
            )}
          </Button>
        </div>
      </div>
    </Card>
  );
};
