/**
 * SPEC-049 AC-16, AC-17, AC-18, AC-22: Inline "ask about this" chip.
 *
 * Self-contained, reusable. No surface-specific imports. Surfaces pass the
 * appropriate ChatScope when rendering it.
 */

import React from 'react';
import { ChatBubbleIcon } from '@radix-ui/react-icons';
import { useChatStore } from '@/stores/useChatStore';
import type { ChatScope } from '@/api/types/chat';

interface AskChipProps {
  scope: ChatScope;
  label?: string;
  prompt?: string;
}

export const AskChip: React.FC<AskChipProps> = ({
  scope,
  label = 'Ask about this',
  prompt,
}) => {
  const handleClick = () => {
    const store = useChatStore.getState();
    store.setScope(scope);
    store.setChatPanelOpen(true);
    if (prompt) {
      store.setPendingPrompt(prompt);
    }
  };

  return (
    <button
      onClick={handleClick}
      className="inline-flex items-center gap-1 px-2 py-1 text-xs font-medium text-text-muted hover:text-text-primary bg-ui-element-bg hover:bg-ui-interactive-bg-hover border border-ui-border rounded-md transition-colors focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-brand-primary"
      aria-label={label}
    >
      <ChatBubbleIcon className="w-3 h-3" />
      {label}
    </button>
  );
};

export default AskChip;
