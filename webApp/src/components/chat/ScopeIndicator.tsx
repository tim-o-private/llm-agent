/**
 * SPEC-049 AC-05: Displays the current chat scope as a label.
 *
 * Renders nothing for global scope. For all other scopes, shows the scope type
 * and the last path segment as the display name.
 */

import React from 'react';
import type { ChatScope, ChatScopeType } from '@/api/types/chat';

const SCOPE_LABELS: Record<ChatScopeType, (scope: ChatScope) => string | null> = {
  global: () => null,
  today: () => 'Today',
  folder: (s) =>
    `Folder: ${(s as { type: 'folder'; path: string }).path.replace(/\/$/, '').split('/').pop()}`,
  file: (s) =>
    `File: ${(s as { type: 'file'; path: string }).path.split('/').pop()}`,
  workflow: (s) =>
    `Workflow: ${(s as { type: 'workflow'; path: string }).path.split('/').pop()?.replace('.flow.md', '')}`,
};

export const ScopeIndicator: React.FC<{ scope: ChatScope }> = ({ scope }) => {
  const label = SCOPE_LABELS[scope.type](scope);
  if (!label) return null;

  return (
    <p
      className="text-xs text-text-muted font-mono truncate"
      aria-label={`Chat scope: ${label}`}
    >
      {label}
    </p>
  );
};

export default ScopeIndicator;
