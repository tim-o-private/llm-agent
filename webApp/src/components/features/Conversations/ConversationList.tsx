import React, { useState, useMemo, useCallback } from 'react';
import { useChatSessions, type ChatSession } from '@/api/hooks/useChatHistoryHooks';
import { useChatStore } from '@/stores/useChatStore';

interface ConversationGroup {
  chatId: string;
  agentName: string;
  channel: string;
  latestTimestamp: string;
  isActive: boolean;
}

interface ConversationListProps {
  agentName: string;
}

export const ConversationList: React.FC<ConversationListProps> = ({ agentName }) => {
  const [isExpanded, setIsExpanded] = useState(false);
  const { data: sessions, isLoading, error } = useChatSessions(undefined, 100);
  const { activeChatId, startNewConversationAsync, switchToConversationAsync } = useChatStore();

  // Group sessions by unique chat_id, keeping the most recent session per chat_id
  const conversationGroups = useMemo((): ConversationGroup[] => {
    if (!sessions || sessions.length === 0) return [];

    const groupMap = new Map<string, ChatSession>();
    for (const session of sessions) {
      if (!session.chat_id) continue;
      const existing = groupMap.get(session.chat_id);
      if (!existing || new Date(session.updated_at) > new Date(existing.updated_at)) {
        groupMap.set(session.chat_id, session);
      }
    }

    return Array.from(groupMap.values())
      .map((session) => ({
        chatId: session.chat_id!,
        agentName: session.agent_name,
        channel: session.channel || 'web',
        latestTimestamp: session.updated_at,
        isActive: session.is_active,
      }))
      .sort((a, b) => new Date(b.latestTimestamp).getTime() - new Date(a.latestTimestamp).getTime());
  }, [sessions]);

  const handleNewConversation = useCallback(async () => {
    await startNewConversationAsync(agentName);
  }, [agentName, startNewConversationAsync]);

  const handleSwitchConversation = useCallback(
    async (chatId: string) => {
      if (chatId === activeChatId) return;
      await switchToConversationAsync(chatId);
    },
    [activeChatId, switchToConversationAsync],
  );

  const formatTimestamp = useCallback((timestamp: string): string => {
    const date = new Date(timestamp);
    const now = new Date();
    const diffMs = now.getTime() - date.getTime();
    const diffMins = Math.floor(diffMs / 60000);
    const diffHours = Math.floor(diffMs / 3600000);
    const diffDays = Math.floor(diffMs / 86400000);

    if (diffMins < 1) return 'Just now';
    if (diffMins < 60) return `${diffMins}m ago`;
    if (diffHours < 24) return `${diffHours}h ago`;
    if (diffDays < 7) return `${diffDays}d ago`;
    return date.toLocaleDateString();
  }, []);

  const channelBadgeClass = useCallback((channel: string): string => {
    switch (channel) {
      case 'telegram':
        return 'bg-ui-interactive-bg text-text-secondary';
      case 'scheduled':
        return 'bg-ui-element-bg text-text-muted';
      default:
        return 'bg-brand-primary/10 text-brand-primary';
    }
  }, []);

  return (
    <div className="border-b border-ui-border">
      {/* Toggle header */}
      <button
        onClick={() => setIsExpanded((prev) => !prev)}
        className="w-full flex items-center justify-between px-4 py-2 text-sm font-medium text-text-secondary hover:bg-ui-element-bg transition-colors"
        aria-expanded={isExpanded}
        aria-controls="conversation-list-panel"
      >
        <span className="flex items-center gap-1.5">
          <svg
            className={`w-3.5 h-3.5 transition-transform ${isExpanded ? 'rotate-90' : ''}`}
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
            strokeWidth={2}
          >
            <path strokeLinecap="round" strokeLinejoin="round" d="M9 5l7 7-7 7" />
          </svg>
          Conversations
          {conversationGroups.length > 0 && (
            <span className="text-xs text-text-muted">({conversationGroups.length})</span>
          )}
        </span>
      </button>

      {/* Expandable panel */}
      {isExpanded && (
        <div id="conversation-list-panel" className="px-2 pb-2">
          {/* New Conversation button */}
          <button
            onClick={handleNewConversation}
            className="w-full flex items-center gap-2 px-3 py-2 mb-1 text-sm font-medium text-brand-primary hover:bg-brand-primary/10 rounded-md transition-colors"
          >
            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M12 4v16m8-8H4" />
            </svg>
            New Conversation
          </button>

          {/* Loading state */}
          {isLoading && (
            <div className="px-3 py-4 text-center text-xs text-text-muted">Loading conversations...</div>
          )}

          {/* Error state */}
          {error && (
            <div className="px-3 py-2 text-center text-xs text-text-muted">
              Failed to load conversations.
            </div>
          )}

          {/* Conversation items */}
          {!isLoading && !error && conversationGroups.length === 0 && (
            <div className="px-3 py-4 text-center text-xs text-text-muted">No conversations yet.</div>
          )}

          <div className="max-h-48 overflow-y-auto space-y-0.5">
            {conversationGroups.map((group) => {
              const isSelected = group.chatId === activeChatId;
              return (
                <button
                  key={group.chatId}
                  onClick={() => handleSwitchConversation(group.chatId)}
                  className={`w-full flex items-center justify-between px-3 py-2 rounded-md text-left text-sm transition-colors ${
                    isSelected
                      ? 'bg-brand-primary/10 text-text-primary'
                      : 'text-text-secondary hover:bg-ui-element-bg'
                  }`}
                  title={`Chat ID: ${group.chatId}`}
                >
                  <div className="flex flex-col min-w-0 flex-1">
                    <span className="truncate font-medium text-xs">
                      {group.agentName}
                    </span>
                    <span className="text-xs text-text-muted truncate">
                      {formatTimestamp(group.latestTimestamp)}
                    </span>
                  </div>
                  <div className="flex items-center gap-1.5 ml-2 flex-shrink-0">
                    <span
                      className={`text-[10px] px-1.5 py-0.5 rounded-full ${channelBadgeClass(group.channel)}`}
                    >
                      {group.channel}
                    </span>
                    {group.isActive && (
                      <span className="w-1.5 h-1.5 rounded-full bg-success-indicator flex-shrink-0" />
                    )}
                  </div>
                </button>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
};
