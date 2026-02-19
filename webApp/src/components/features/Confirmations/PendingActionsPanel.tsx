/**
 * PendingActionsPanel component for displaying and managing pending actions.
 */

import React, { useState, useRef, useEffect } from 'react';
import { Card } from '../../ui/Card';
import { Badge } from '../../ui/Badge';
import { AlertTriangle, CheckCircle, History, RefreshCw, Loader2 } from 'lucide-react';
import { Button } from '../../ui/Button';
import { ActionCard } from './ActionCard';
import { usePendingActions, usePendingCount, useApproveAction, useRejectAction } from '@/api/hooks/useActionsHooks';

interface PendingActionsPanelProps {
  className?: string;
  compact?: boolean;
}

export const PendingActionsPanel: React.FC<PendingActionsPanelProps> = ({ className = '', compact = false }) => {
  const [approvingId, setApprovingId] = useState<string | null>(null);
  const [rejectingId, setRejectingId] = useState<string | null>(null);

  const { data: actions, isLoading, error, refetch } = usePendingActions();

  const { data: countData } = usePendingCount();

  const approveAction = useApproveAction();
  const rejectAction = useRejectAction();

  const handleApprove = async (actionId: string) => {
    setApprovingId(actionId);
    try {
      await approveAction.mutateAsync(actionId);
    } finally {
      setApprovingId(null);
    }
  };

  const handleReject = async (actionId: string) => {
    setRejectingId(actionId);
    try {
      await rejectAction.mutateAsync({ actionId });
    } finally {
      setRejectingId(null);
    }
  };

  const pendingCount = countData?.count || 0;
  const pendingActions = actions || [];

  if (compact) {
    if (pendingCount === 0) return null;

    return (
      <Badge className="flex items-center gap-1 bg-warning-subtle text-warning-strong cursor-pointer hover:bg-warning-subtle/80">
        <AlertTriangle className="h-3 w-3" />
        {pendingCount} pending
      </Badge>
    );
  }

  return (
    <Card className={`p-4 ${className}`}>
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <AlertTriangle className="h-5 w-5 text-amber-500" />
          <h3 className="text-lg font-semibold">Pending Actions</h3>
          {pendingCount > 0 && <Badge className="bg-warning-subtle text-warning-strong">{pendingCount}</Badge>}
        </div>
        <Button size="1" variant="ghost" onClick={() => refetch()} disabled={isLoading}>
          {isLoading ? <Loader2 className="h-4 w-4 animate-spin" /> : <RefreshCw className="h-4 w-4" />}
        </Button>
      </div>

      {isLoading && pendingActions.length === 0 ? (
        <div className="flex items-center justify-center py-8 text-text-muted">
          <Loader2 className="h-6 w-6 animate-spin mr-2" />
          Loading actions...
        </div>
      ) : error ? (
        <div className="text-destructive py-4 text-center">Failed to load pending actions: {error.message}</div>
      ) : pendingActions.length === 0 ? (
        <div className="flex flex-col items-center justify-center py-8 text-text-muted">
          <CheckCircle className="h-12 w-12 text-success-strong mb-2" />
          <p className="font-medium">No pending actions</p>
          <p className="text-sm">All actions have been reviewed</p>
        </div>
      ) : (
        <div className="space-y-3">
          {pendingActions.map((action) => (
            <ActionCard
              key={action.id}
              action={action}
              onApprove={handleApprove}
              onReject={handleReject}
              isApproving={approvingId === action.id}
              isRejecting={rejectingId === action.id}
            />
          ))}
        </div>
      )}

      {pendingActions.length > 0 && (
        <div className="mt-4 pt-4 border-t border-ui-border">
          <Button size="1" variant="ghost" className="w-full text-text-muted hover:text-text-secondary">
            <History className="h-4 w-4 mr-2" />
            View Action History
          </Button>
        </div>
      )}
    </Card>
  );
};

export const PendingActionsBadge: React.FC = () => {
  const [isOpen, setIsOpen] = useState(false);
  const dropdownRef = useRef<HTMLDivElement>(null);
  const { data: countData, isLoading } = usePendingCount();
  const count = countData?.count || 0;

  // Close dropdown on outside click
  useEffect(() => {
    if (!isOpen) return;
    const handleClickOutside = (event: Event) => {
      const target = event.target as HTMLElement;
      if (dropdownRef.current && !dropdownRef.current.contains(target)) {
        setIsOpen(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, [isOpen]);

  if (isLoading || count === 0) return null;

  return (
    <div className="relative" ref={dropdownRef}>
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="relative inline-flex items-center px-2 py-1 rounded-full bg-warning-subtle text-warning-strong text-xs font-medium hover:bg-warning-subtle/80 transition-colors"
      >
        <AlertTriangle className="h-3 w-3 mr-1" />
        {count} pending
      </button>

      {isOpen && (
        <div className="absolute right-0 top-full mt-2 w-96 max-h-[80vh] overflow-y-auto rounded-lg border border-ui-border bg-ui-element-bg shadow-lg z-50">
          <PendingActionsPanel />
        </div>
      )}
    </div>
  );
};
