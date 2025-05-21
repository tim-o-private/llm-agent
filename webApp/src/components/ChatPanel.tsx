import React, { useState, useRef, useEffect } from 'react';
import { useChatStore, useInitializeChatStore } from '@/stores/useChatStore';
import { MessageHeader, MessageInput, MessageBubble } from '@/components/ui';
import { supabase } from '@/lib/supabaseClient';



// Actual function to fetch AI response from the backend
async function fetchAiResponse(message: string, userId: string | null, sessionId: string | null): Promise<string> { 
  console.log('Sending message to backend API (/api/chat):', message, 'UserId:', userId, 'SessionId:', sessionId);
  try {
    const apiUrl = `${import.meta.env.VITE_API_BASE_URL || ''}/api/chat`;
    const { data: { session } } = await supabase.auth.getSession();
    const accessToken = session?.access_token;

    const agentIdToUse = import.meta.env.VITE_DEFAULT_CHAT_AGENT_ID || "assistant";

    if (!sessionId) {
      // This should ideally not happen if the store initialization logic is correct
      // and ChatPanel only allows sending messages when a session is active.
      throw new Error("Session ID is missing. Cannot send message.");
    }

    const requestBody = {
      agent_id: agentIdToUse, 
      message: message,       
      session_id: sessionId // ADDED: Pass the session_id from the store
    };

    const response = await fetch(apiUrl, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${accessToken}`,
      },
      body: JSON.stringify(requestBody),
    });

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({ detail: 'Unknown error from API' }));
      // The /api/chat endpoint returns { "detail": "message" } for HTTPExceptions
      // and { "reply": "message" } for ChatResponse.
      // Let's try to get a consistent error message.
      const detail = errorData.detail || errorData.reply || 'No detail';
      throw new Error(`API Error: ${response.status} ${response.statusText} - ${detail}`);
    }

    const data = await response.json();
    // /api/chat returns { "reply": "agent_response_text" }  <-- This comment is now incorrect
    // Backend actually sends { "response": "agent_response_text" }
    return data.response; // CHANGED from data.reply
  } catch (error) {
    console.error('Failed to fetch AI response from backend (/api/chat):', error);
    if (error instanceof Error && error.message.startsWith('API Error:')) {
        return `Sorry, I couldn\'t connect to the AI: ${error.message.replace('API Error: ', '')}`;
    }
    return 'Sorry, I had trouble connecting to the AI. Please check the server and try again.';
  }
}

// ADD agentId prop to the component's props interface
interface ChatPanelProps {
  agentId?: string; // MADE agentId optional
}

export const ChatPanel: React.FC<ChatPanelProps> = ({ agentId: agentIdProp }) => { // RENAMED prop to avoid conflict
  // Use provided agentId or default to environment variable
  const agentId = agentIdProp || import.meta.env.VITE_DEFAULT_CHAT_AGENT_ID || "assistant";

  const { messages, addMessage, sessionId } = useChatStore(); // Get sessionId from store
  // const { isChatPanelOpen } = useChatStore(); // isChatPanelOpen is no longer used here
  
  // Initialize the chat store with the provided agentId.
  // The hook will handle session and message state internally based on this agentId.
  useInitializeChatStore(agentId);

  const [isLoading, setIsLoading] = useState(false);
  const messagesEndRef = useRef<null | HTMLDivElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  const [userId, setUserId] = useState<string | null>(null);
  
  useEffect(() => {
    const fetchUserSessionData = async () => {
      const { data: { user } } = await supabase.auth.getUser();
      setUserId(user?.id || null);
    };
    fetchUserSessionData();
  }, []);

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const handleSendMessage = async (messageText: string) => {
    if (!messageText || isLoading || !userId || !sessionId) { // Ensure sessionId is present
        if(!sessionId) console.error("Cannot send message: Session ID is null.");
        return;
    } 

    addMessage({ text: messageText, sender: 'user' });
    setIsLoading(true);

    try {
      // Pass userId for logging/context if needed by fetchAiResponse, but not for the request body to /api/chat
      // sessionId is now passed to fetchAiResponse
      const aiResponseText = await fetchAiResponse(messageText, userId, sessionId); 
      addMessage({ text: aiResponseText, sender: 'ai' });
    } catch (error) {
      addMessage({ text: error instanceof Error ? error.message : 'An unexpected error occurred.', sender: 'ai'});
    } finally {
      setIsLoading(false);
    }
  };

  // This visibility check is now handled by the parent component (TodayView)
  /*
  if (!isChatPanelOpen && window.location.pathname !== '/coach') { 
    return null;
  }
  */

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