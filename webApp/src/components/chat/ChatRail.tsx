/**
 * SPEC-049 AC-04, AC-21: Thin wrapper around ChatPanel for the right pane.
 *
 * - Derives scope from the current route via useChatScope
 * - Syncs scope to the Zustand store so ChatPanel's send handler can read it
 * - Provides the <aside role="complementary"> landmark
 */

import React, { useEffect } from 'react';
import { useChatScope } from '@/hooks/useChatScope';
import { useChatStore } from '@/stores/useChatStore';
import { ChatPanel } from '@/components/ChatPanel';

export const ChatRail: React.FC = () => {
  const scope = useChatScope();
  const setScope = useChatStore((s) => s.setScope);

  useEffect(() => {
    setScope(scope);
  }, [scope, setScope]);

  return (
    <aside role="complementary" aria-label="Chat" className="h-full flex flex-col">
      <ChatPanel
        scope={scope}
        agentId={import.meta.env.VITE_DEFAULT_CHAT_AGENT_ID || 'assistant'}
      />
    </aside>
  );
};

export default ChatRail;
