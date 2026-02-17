import React, { useState, useRef, useEffect } from 'react';
import { useChatStore, useInitializeChatStore } from '@/stores/useChatStore';
import { MessageHeader, MessageInput, MessageBubble } from '@/components/ui';
import { supabase } from '@/lib/supabaseClient';
import { useSendMessageMutation } from '@/api/hooks/useChatApiHooks';

// ADD agentId prop to the component's props interface
interface ChatPanelV1Props {
  agentId?: string; // MADE agentId optional
}

export const ChatPanelV1: React.FC<ChatPanelV1Props> = ({ agentId: agentIdProp }) => {
  const agentId = agentIdProp || import.meta.env.VITE_DEFAULT_CHAT_AGENT_ID || 'assistant';

  const { messages, addMessage, activeChatId, currentSessionInstanceId, sendHeartbeatAsync, clearCurrentSessionAsync } =
    useChatStore();

  useInitializeChatStore(agentId);

  const messagesEndRef = useRef<null | HTMLDivElement>(null);

  const sendMessageMutation = useSendMessageMutation();

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  const [userId, setUserId] = useState<string | null>(null);

  useEffect(() => {
    const fetchUserSessionData = async () => {
      const {
        data: { user },
      } = await supabase.auth.getUser();
      setUserId(user?.id || null);
    };
    fetchUserSessionData();
  }, []);

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  // Periodic Heartbeat
  useEffect(() => {
    if (currentSessionInstanceId) {
      const intervalId = setInterval(() => {
        sendHeartbeatAsync();
      }, 60000);

      return () => {
        clearInterval(intervalId);
      };
    }
  }, [currentSessionInstanceId, sendHeartbeatAsync]);

  // beforeunload listener to deactivate session instance
  useEffect(() => {
    const handleBeforeUnload = () => {
      if (useChatStore.getState().currentSessionInstanceId) {
        clearCurrentSessionAsync();
      }
    };
    window.addEventListener('beforeunload', handleBeforeUnload);
    return () => {
      window.removeEventListener('beforeunload', handleBeforeUnload);
    };
  }, [clearCurrentSessionAsync]);

  const handleSendMessage = async (messageText: string) => {
    if (!messageText || sendMessageMutation.isPending || !userId || !currentSessionInstanceId || !activeChatId) {
      if (!currentSessionInstanceId) console.error('Cannot send message: currentSessionInstanceId is null.');
      if (!activeChatId) console.error('Cannot send message: activeChatId is null.');
      return;
    }

    addMessage({ text: messageText, sender: 'user' });

    try {
      const aiResponseText = await sendMessageMutation.mutateAsync({
        message: messageText,
        userId,
        activeChatId,
      });
      addMessage({ text: aiResponseText, sender: 'ai' });
    } catch (error) {
      const errorMessage =
        error instanceof Error ? error.message : 'An unexpected error occurred while sending the message.';
      addMessage({ text: errorMessage, sender: 'ai' });
      console.error('ChatPanelV1: Error sending message:', error);
    }
  };

  return (
    <div className="flex flex-col h-full bg-ui-element-bg shadow-lg border-l border-ui-border">
      <MessageHeader
        chatTitle="AI Coach"
        status={sendMessageMutation.isPending ? 'Typing...' : 'Online'}
        statusColor={sendMessageMutation.isPending ? 'yellow' : 'green'}
      />
      <div className="flex-grow p-4 overflow-y-auto space-y-1">
        {messages.map((msg) => (
          <MessageBubble key={msg.id} id={msg.id} text={msg.text} sender={msg.sender as 'user' | 'ai' | 'system'} />
        ))}
        <div ref={messagesEndRef} />
      </div>
      <MessageInput
        onSendMessage={handleSendMessage}
        disabled={sendMessageMutation.isPending}
        placeholder="Ask your coach..."
      />
    </div>
  );
};
