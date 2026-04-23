/**
 * SPEC-048 AC-04/AC-05/AC-06/AC-07: Workflow list panel (left sub-pane).
 *
 * Lists all .flow.md files from useWorkflowList. Each entry shows:
 * name, description (truncated 80 chars), trigger summary + next run.
 * Click navigates via react-router. "+ New workflow" button at bottom.
 */

import React, { useState, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { PlusIcon } from '@radix-ui/react-icons';
import { useWorkflowList, useCreateWorkflow } from '@/api/hooks/useWorkflowEditorHooks';
import { Spinner } from '@/components/ui/Spinner';

interface WorkflowListPanelProps {
  currentPath: string;
}

function truncate(text: string, max: number): string {
  if (text.length <= max) return text;
  return text.slice(0, max - 1) + '…';
}

function formatRelativeTime(isoString: string | null): string | null {
  if (!isoString) return null;
  const date = new Date(isoString);
  const now = new Date();
  const diffMs = date.getTime() - now.getTime();
  const diffMin = Math.round(diffMs / 60_000);

  if (diffMin <= 0) return 'now';
  if (diffMin < 60) return `in ${diffMin}m`;
  const diffHrs = Math.round(diffMin / 60);
  if (diffHrs < 24) return `in ${diffHrs}h`;
  const diffDays = Math.round(diffHrs / 24);
  return `in ${diffDays}d`;
}

export const WorkflowListPanel: React.FC<WorkflowListPanelProps> = ({
  currentPath,
}) => {
  const navigate = useNavigate();
  const { data: workflows, isLoading, error } = useWorkflowList();
  const createMutation = useCreateWorkflow();
  const [newName, setNewName] = useState('');
  const [showNameInput, setShowNameInput] = useState(false);

  const handleCreateWorkflow = useCallback(() => {
    if (!newName.trim()) return;
    const sanitized = newName
      .trim()
      .toLowerCase()
      .replace(/[^a-z0-9-]/g, '-')
      .replace(/-+/g, '-')
      .replace(/^-|-$/g, '')
      .slice(0, 60);

    if (!sanitized) return;

    createMutation.mutate(
      { name: sanitized },
      {
        onSuccess: (data) => {
          setShowNameInput(false);
          setNewName('');
          navigate(`/vault/${data.path}`);
        },
      },
    );
  }, [newName, createMutation, navigate]);

  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent) => {
      if (e.key === 'Enter') {
        handleCreateWorkflow();
      } else if (e.key === 'Escape') {
        setShowNameInput(false);
        setNewName('');
      }
    },
    [handleCreateWorkflow],
  );

  if (isLoading) {
    return (
      <nav aria-label="Workflow list" className="h-full flex items-center justify-center">
        <Spinner size={16} />
      </nav>
    );
  }

  if (error) {
    return (
      <nav aria-label="Workflow list" className="h-full p-3">
        <p className="text-xs text-red-500">Failed to load workflows</p>
      </nav>
    );
  }

  const items = workflows ?? [];

  return (
    <nav aria-label="Workflow list" className="h-full flex flex-col">
      {/* Header */}
      <div className="px-3 py-2 border-b border-ui-border flex-shrink-0">
        <h2 className="text-xs font-semibold text-text-muted uppercase tracking-wider">
          Workflows
        </h2>
      </div>

      {/* List */}
      <div className="flex-1 overflow-y-auto">
        {items.length === 0 ? (
          <div className="px-3 py-8 text-center">
            <p className="text-xs text-text-muted">
              No workflows — create your first.
            </p>
          </div>
        ) : (
          <ul role="list" className="py-1">
            {items.map((wf) => {
              const wfPath = `_workflows/${wf.filename}`;
              const isActive = currentPath === wfPath;
              const nextRun = formatRelativeTime(wf.next_run_at);

              return (
                <li key={wf.filename}>
                  <button
                    onClick={() => navigate(`/vault/${wfPath}`)}
                    className={`w-full text-left px-3 py-2 transition-colors focus-visible:outline-2 focus-visible:outline-offset-[-2px] focus-visible:outline-brand-primary ${
                      isActive
                        ? 'bg-brand-primary/10 border-l-2 border-brand-primary'
                        : 'hover:bg-ui-interactive-bg-hover border-l-2 border-transparent'
                    }`}
                    aria-current={isActive ? 'page' : undefined}
                  >
                    <div className="text-sm font-medium text-text-primary truncate">
                      {wf.name}
                    </div>
                    {wf.description && (
                      <div className="text-xs text-text-muted mt-0.5 truncate">
                        {truncate(wf.description, 80)}
                      </div>
                    )}
                    <div className="flex items-center gap-2 mt-1">
                      <span className="text-xs font-mono text-text-muted">
                        {wf.trigger_summary}
                      </span>
                      {nextRun && (
                        <>
                          <span className="text-text-muted">&middot;</span>
                          <span className="text-xs font-mono text-text-muted">
                            {nextRun}
                          </span>
                        </>
                      )}
                    </div>
                  </button>
                </li>
              );
            })}
          </ul>
        )}
      </div>

      {/* Create new workflow */}
      <div className="flex-shrink-0 border-t border-ui-border p-2">
        {showNameInput ? (
          <div className="flex gap-1">
            <input
              autoFocus
              value={newName}
              onChange={(e) => setNewName(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="workflow-name"
              className="flex-1 min-w-0 px-2 py-1 text-xs rounded-md border border-ui-border bg-ui-element-bg text-text-primary placeholder:text-text-muted focus:outline-2 focus:outline-brand-primary"
            />
            <button
              onClick={handleCreateWorkflow}
              disabled={createMutation.isPending || !newName.trim()}
              className="px-2 py-1 text-xs font-medium rounded-md bg-brand-primary text-white hover:bg-brand-primary/90 disabled:opacity-50 transition-colors"
            >
              {createMutation.isPending ? '...' : 'Create'}
            </button>
          </div>
        ) : (
          <button
            data-testid="new-workflow-btn"
            onClick={() => setShowNameInput(true)}
            className="w-full inline-flex items-center justify-center gap-1 px-2 py-1.5 text-xs font-medium text-text-muted hover:text-text-primary bg-ui-element-bg hover:bg-ui-interactive-bg-hover border border-ui-border rounded-md transition-colors focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-brand-primary"
          >
            <PlusIcon className="h-3.5 w-3.5" />
            New workflow
          </button>
        )}
      </div>
    </nav>
  );
};
