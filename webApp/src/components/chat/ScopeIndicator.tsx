import React from 'react';
import type { ChatScope } from '@/api/types/chat';
import { scopeLabel } from '@/lib/scopeLabel';

export const ScopeIndicator: React.FC<{ scope: ChatScope }> = ({ scope }) => {
  const label = scopeLabel(scope);
  if (!label) return null;

  return (
    <p
      className="text-[10px] text-text-muted font-mono truncate"
      aria-label={`Chat scope: ${label}`}
    >
      {label}
    </p>
  );
};

export default ScopeIndicator;
