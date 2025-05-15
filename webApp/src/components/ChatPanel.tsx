import React, { useState, useRef, useEffect } from 'react';
import { useChatStore } from '../stores/useChatStore';
import { MessageHeader, MessageInput, MessageBubble } from '@/components/ui';
import { supabase } from '@/lib/supabaseClient';



// Actual function to fetch AI response from the backend
async function fetchAiResponse(message: string): Promise<string> {
  console.log('Sending message to backend API:', message);
  try {
    const apiUrl = `${import.meta.env.VITE_API_BASE_URL || ''}/api/chat`;
    const { data: { session } } = await supabase.auth.getSession();
    const accessToken = session?.access_token;
    console.log('Access token:', accessToken);
    const response = await fetch(apiUrl, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${accessToken}`,
      },
      body: JSON.stringify({
        agent_id: 'assistant',
        message: message,
        // user_id: userId, // (optional, can be omitted)
      }),
    });

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({ detail: 'Unknown error from API' }));
      throw new Error(`API Error: ${response.status} ${response.statusText} - ${errorData.detail}`);
    }

    const data = await response.json();
    return data.reply;
  } catch (error) {
    console.error('Failed to fetch AI response from backend:', error);
    // Return a user-friendly error message to be displayed in the chat
    if (error instanceof Error && error.message.startsWith('API Error:')) {
        return `Sorry, I couldn\'t connect to the AI: ${error.message.replace('API Error: ', '')}`;
    }
    return 'Sorry, I had trouble connecting to the AI. Please check the server and try again.';
  }
}

export const ChatPanel: React.FC = () => {
  const {
    messages,
    addMessage,
    isChatPanelOpen // This might be re-evaluated if ChatPanel is always visible on CoachPage
  } = useChatStore();
  // inputValue is now managed by MessageInput component
  // const [inputValue, setInputValue] = useState(''); 
  const [isLoading, setIsLoading] = useState(false);
  const messagesEndRef = useRef<null | HTMLDivElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  const [userId, setUserId] = useState<string | null>(null);
  
  useEffect(() => {
    const fetchUserId = async () => {
      const { data: { user } } = await supabase.auth.getUser();
      setUserId(user?.id || null);
    };
    fetchUserId();
  }, []);

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  // handleSendMessage is now passed to MessageInput
  const handleSendMessage = async (messageText: string) => {
    if (!messageText || isLoading || !userId) return; 


    addMessage({ text: messageText, sender: 'user' });
    // setInputValue(''); // MessageInput handles its own state clearing
    setIsLoading(true);

    try {
      const aiResponse = await fetchAiResponse(messageText);
      addMessage({ text: aiResponse, sender: 'ai' });
    } catch (error) {
      addMessage({ text: error instanceof Error ? error.message : 'An unexpected error occurred.', sender: 'ai'});
    } finally {
      setIsLoading(false);
    }
  };

  // If ChatPanel is part of CoachPage, it might not need its own `isChatPanelOpen` check anymore,
  // as its visibility would be controlled by navigating to/from CoachPage.
  // For now, let's assume `CoachPage` renders it conditionally if this logic is still desired from the store.
  // Or, if always visible on CoachPage, this check can be removed.
  // Keeping for now to minimize breaking changes to store logic immediately.
  if (!isChatPanelOpen && window.location.pathname !== '/coach') { // Adjusted condition slightly
    return null;
  }

  return (
    // Changed from fixed sidebar to a flexible container for CoachPage
    <div className="flex flex-col h-full bg-white dark:bg-gray-800 shadow-lg border-l border-gray-200 dark:border-gray-700">
      <MessageHeader 
        chatTitle="AI Coach" 
        status={isLoading ? "Typing..." : "Online"} 
        statusColor={isLoading ? 'yellow' : 'green'}
      />
      <div className="flex-grow p-4 overflow-y-auto space-y-1">
        {/* Replaced old message rendering with MessageBubble */}
        {messages.map((msg) => (
          <MessageBubble
            key={msg.id} // Ensure your message object in the store has an `id`
            id={msg.id} // Pass id to MessageBubbleProps
            text={msg.text}
            sender={msg.sender as 'user' | 'ai' | 'system'} // Cast sender to the expected type
            // timestamp={msg.timestamp} // Add if your message object has a timestamp
            // avatarUrl={msg.sender === 'user' ? 'user_avatar_url' : 'ai_avatar_url'} // Example avatar logic
            // senderName={msg.sender === 'ai' ? 'AI Coach' : undefined} // Example sender name logic
          />
        ))}
        <div ref={messagesEndRef} />
      </div>
      {/* Replaced old input with MessageInput component */}
      <MessageInput onSendMessage={handleSendMessage} disabled={isLoading} placeholder="Ask your coach..." />
    </div>
  );
}; 