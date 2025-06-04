import { create } from 'zustand';
import { devtools } from 'zustand/middleware';
import { immer } from 'zustand/middleware/immer';
import { useAuthStore } from '@/features/auth/useAuthStore';
import { apiClient } from '@/lib/apiClient';
import { chatAPI } from '@/lib/chatAPI';
import { pollingManager } from '@/lib/pollingManager';
import { toast } from '@/components/ui/toast';
import { ChatRequest, ChatResponse, ChatSession, ChatMessage, AgentAction } from '@/types/chat';
import { CacheEntry, StorePollingConfig } from '@/types/polling';

export interface ChatStore {
  // Data (compatible with ChatState)
  sessions: ChatSession[];
  currentSession: ChatSession | null;
  messages: ChatMessage[];
  isLoading: boolean;
  error: string | null;
  
  // Additional state for router-proxied implementation
  sessionsMap: Record<string, ChatSession>;
  messagesMap: Record<string, ChatMessage[]>; // Keyed by session_id
  currentSessionId: string | null;
  
  // Caching and polling
  cache: {
    sessions: CacheEntry<ChatSession[]> | null;
    messages: Record<string, CacheEntry<ChatMessage[]>>; // Keyed by session_id
  };
  pollingConfig: StorePollingConfig;
  
  // Actions (compatible with ChatState)
  createSession: (title?: string) => Promise<ChatSession>;
  loadSession: (sessionId: string) => Promise<void>;
  sendMessage: (message: string, agentName?: string) => Promise<ChatResponse>;
  clearError: () => void;
  refreshSessions: () => Promise<void>;
  
  // Additional actions
  loadSessions: () => Promise<void>;
  loadMessages: (sessionId: string) => Promise<void>;
  deleteSession: (sessionId: string) => Promise<void>;
  setCurrentSession: (sessionId: string | null) => void;
  
  // Cache and polling management
  clearCache: () => void;
  isSessionsStale: () => boolean;
  isMessagesStale: (sessionId: string) => boolean;
  refreshMessages: (sessionId: string) => Promise<void>;
  startPolling: () => void;
  stopPolling: () => void;
  updatePollingConfig: (config: Partial<StorePollingConfig>) => void;
  
  // Selectors
  getCurrentMessages: () => ChatMessage[];
  getSessionById: (id: string) => ChatSession | undefined;
  getMessagesBySessionId: (sessionId: string) => ChatMessage[];
}

/**
 * Store for managing chat sessions and AI interactions via router
 */
export const useChatStore = create<ChatStore>()(
  devtools(
    immer((set, get) => {
      const SESSIONS_POLLING_KEY = 'chat-sessions';
      const MESSAGES_POLLING_KEY = 'chat-messages';
      
      const defaultPollingConfig: StorePollingConfig = {
        enabled: true,
        interval: 15000,        // 15 seconds for chat (more frequent)
        staleThreshold: 120000, // 2 minutes
        queryLimit: 50,
      };

      return {
        // Initial state (compatible with ChatState)
        sessions: [],
        currentSession: null,
        messages: [],
        isLoading: false,
        error: null,
        
        // Additional state
        sessionsMap: {},
        messagesMap: {},
        currentSessionId: null,
        
        // Caching and polling
        cache: {
          sessions: null,
          messages: {},
        },
        pollingConfig: defaultPollingConfig,
        
        /**
         * Create a new chat session (compatible with ChatState)
         */
        createSession: async (title = 'New Chat') => {
          const userId = useAuthStore.getState().user?.id;
          if (!userId) {
            throw new Error('User not authenticated');
          }
          
          set({ isLoading: true, error: null });
          
          try {
            const sessionData = {
              user_id: userId,
              title,
            };
            
            // Router-proxied PostgREST call
            const newSession = await apiClient.insert<any>('chat_sessions', sessionData);
            
            // Convert to ChatSession format
            const chatSession: ChatSession = {
              id: newSession.id,
              title: newSession.title,
              created_at: newSession.created_at,
              updated_at: newSession.updated_at,
              message_count: 0,
            };
            
            set(state => {
              // Add to sessions array and map
              state.sessions.push(chatSession);
              state.sessionsMap[chatSession.id] = chatSession;
              
              // Initialize empty messages array
              state.messagesMap[chatSession.id] = [];
              
              // Update sessions cache
              if (state.cache.sessions) {
                state.cache.sessions.data.push(chatSession);
                state.cache.sessions.timestamp = new Date();
              }
              
              // Set as current session
              state.currentSession = chatSession;
              state.currentSessionId = chatSession.id;
              state.messages = [];
              state.isLoading = false;
            });
            
            toast.success('New chat session created');
            return chatSession;
          } catch (error) {
            const errorMessage = error instanceof Error ? error.message : 'Failed to create session';
            set({ error: errorMessage, isLoading: false });
            toast.error(errorMessage);
            throw error;
          }
        },
        
        /**
         * Load a specific session (compatible with ChatState)
         */
        loadSession: async (sessionId: string) => {
          await get().loadMessages(sessionId);
          get().setCurrentSession(sessionId);
        },
        
        /**
         * Send a message and get AI response (compatible with ChatState)
         */
        sendMessage: async (message: string, agentName = 'assistant') => {
          const userId = useAuthStore.getState().user?.id;
          if (!userId) {
            throw new Error('User not authenticated');
          }
          
          // Use current session or create new one
          let targetSessionId = get().currentSessionId;
          if (!targetSessionId) {
            const newSession = await get().createSession();
            targetSessionId = newSession.id;
          }
          
          set({ isLoading: true, error: null });
          
          try {
            // Add user message to local state immediately
            const userMessage: ChatMessage = {
              id: `temp_${Date.now()}`,
              session_id: targetSessionId,
              role: 'user',
              content: message,
              timestamp: new Date().toISOString(),
            };
            
            set(state => {
              // Add to current messages
              state.messages.push(userMessage);
              
              // Add to messages map
              if (!state.messagesMap[targetSessionId]) {
                state.messagesMap[targetSessionId] = [];
              }
              state.messagesMap[targetSessionId].push(userMessage);
            });
            
            // Prepare chat request
            const chatRequest: ChatRequest = {
              message,
              session_id: targetSessionId,
              agent_name: agentName,
              context: {
                previousMessages: get().messagesMap[targetSessionId]?.slice(-10) || [], // Last 10 messages for context
              },
            };
            
            // Send to chat gateway via router
            const response: ChatResponse = await chatAPI.sendMessage(chatRequest);
            
            // Add assistant response to local state
            const assistantMessage: ChatMessage = {
              id: `temp_${Date.now() + 1}`,
              session_id: targetSessionId,
              role: 'assistant',
              content: response.message,
              actions: response.actions,
              timestamp: response.timestamp,
            };
            
            set(state => {
              // Add to current messages
              state.messages.push(assistantMessage);
              
              // Add to messages map
              state.messagesMap[targetSessionId].push(assistantMessage);
              
              // Update messages cache
              if (state.cache.messages[targetSessionId]) {
                state.cache.messages[targetSessionId].data.push(userMessage, assistantMessage);
                state.cache.messages[targetSessionId].timestamp = new Date();
              }
              
              state.isLoading = false;
            });
            
            // Persist messages to database via router (async)
            setTimeout(async () => {
              try {
                await apiClient.insert('chat_message_history', {
                  session_id: targetSessionId,
                  role: 'user',
                  content: message,
                });
                
                await apiClient.insert('chat_message_history', {
                  session_id: targetSessionId,
                  role: 'assistant',
                  content: response.message,
                  metadata: response.metadata,
                });
              } catch (error) {
                console.error('Failed to persist messages:', error);
              }
            }, 100);
            
            return response;
          } catch (error) {
            const errorMessage = error instanceof Error ? error.message : 'Failed to send message';
            set({ error: errorMessage, isLoading: false });
            toast.error(errorMessage);
            throw error;
          }
        },
        
        /**
         * Clear error state (compatible with ChatState)
         */
        clearError: () => {
          set({ error: null });
        },
        
        /**
         * Refresh sessions (compatible with ChatState)
         */
        refreshSessions: async () => {
          await get().loadSessions();
        },
        
        /**
         * Load chat sessions from server via router
         */
        loadSessions: async () => {
          const userId = useAuthStore.getState().user?.id;
          if (!userId) {
            set({ error: 'User not authenticated' });
            return;
          }
          
          // Check cache first
          const { cache, isSessionsStale, pollingConfig } = get();
          if (cache.sessions && !isSessionsStale()) {
            console.log('[useChatStore_v2] Using cached sessions');
            const sessions = cache.sessions.data;
            const sessionsMap: Record<string, ChatSession> = {};
            sessions.forEach((session: ChatSession) => {
              sessionsMap[session.id] = session;
            });
            set({ sessions, sessionsMap });
            return;
          }
          
          set({ isLoading: true, error: null });
          
          try {
            // Router-proxied PostgREST call
            const query = `user_id=eq.${userId}&order=updated_at.desc&limit=${pollingConfig.queryLimit}`;
            const data = await apiClient.select<any>('chat_sessions', query);
            
            // Convert to ChatSession format
            const sessions: ChatSession[] = (data || []).map((session: any) => ({
              id: session.id,
              title: session.title,
              created_at: session.created_at,
              updated_at: session.updated_at,
              message_count: 0, // TODO: Calculate from messages
            }));
            
            // Create cache entry
            const newCache: CacheEntry<ChatSession[]> = {
              data: sessions,
              timestamp: new Date(),
              lastFetch: new Date(),
              isStale: false,
              retryCount: 0,
            };
            
            // Create sessions map
            const sessionsMap: Record<string, ChatSession> = {};
            sessions.forEach((session: ChatSession) => {
              sessionsMap[session.id] = session;
            });
            
            set(state => {
              state.sessions = sessions;
              state.sessionsMap = sessionsMap;
              state.cache.sessions = newCache;
              state.isLoading = false;
            });
          } catch (error) {
            const errorMessage = error instanceof Error ? error.message : 'Failed to load sessions';
            set({ error: errorMessage, isLoading: false });
            toast.error(errorMessage);
          }
        },
        
        /**
         * Load messages for a specific session
         */
        loadMessages: async (sessionId: string) => {
          // Check cache first
          const { cache, isMessagesStale, pollingConfig } = get();
          if (cache.messages[sessionId] && !isMessagesStale(sessionId)) {
            console.log(`[useChatStore_v2] Using cached messages for session ${sessionId}`);
            const messages = cache.messages[sessionId].data;
            set(state => {
              state.messagesMap[sessionId] = messages;
              if (state.currentSessionId === sessionId) {
                state.messages = messages;
              }
            });
            return;
          }
          
          set({ isLoading: true, error: null });
          
          try {
            // Router-proxied PostgREST call
            const query = `session_id=eq.${sessionId}&order=created_at.asc&limit=${pollingConfig.queryLimit}`;
            const data = await apiClient.select<any>('chat_message_history', query);
            
            // Convert to ChatMessage format
            const messages: ChatMessage[] = (data || []).map((msg: any) => ({
              id: msg.id,
              session_id: msg.session_id,
              role: msg.role,
              content: msg.content,
              actions: msg.metadata?.actions,
              timestamp: msg.created_at,
            }));
            
            // Create cache entry
            const newCache: CacheEntry<ChatMessage[]> = {
              data: messages,
              timestamp: new Date(),
              lastFetch: new Date(),
              isStale: false,
              retryCount: 0,
            };
            
            set(state => {
              state.messagesMap[sessionId] = messages;
              state.cache.messages[sessionId] = newCache;
              
              // Update current messages if this is the current session
              if (state.currentSessionId === sessionId) {
                state.messages = messages;
              }
              
              state.isLoading = false;
            });
          } catch (error) {
            const errorMessage = error instanceof Error ? error.message : 'Failed to load messages';
            set({ error: errorMessage, isLoading: false });
            toast.error(errorMessage);
          }
        },
        
        /**
         * Delete a chat session
         */
        deleteSession: async (sessionId: string) => {
          set({ isLoading: true, error: null });
          
          try {
            // Router-proxied PostgREST call (soft delete)
            await apiClient.delete('chat_sessions', sessionId);
            
            set(state => {
              // Remove from sessions array and map
              state.sessions = state.sessions.filter(s => s.id !== sessionId);
              delete state.sessionsMap[sessionId];
              delete state.messagesMap[sessionId];
              
              // Update cache
              if (state.cache.sessions) {
                state.cache.sessions.data = state.cache.sessions.data.filter(s => s.id !== sessionId);
                state.cache.sessions.timestamp = new Date();
              }
              delete state.cache.messages[sessionId];
              
              // Clear current session if it was deleted
              if (state.currentSessionId === sessionId) {
                state.currentSession = null;
                state.currentSessionId = null;
                state.messages = [];
              }
              
              state.isLoading = false;
            });
            
            toast.success('Chat session deleted');
          } catch (error) {
            const errorMessage = error instanceof Error ? error.message : 'Failed to delete session';
            set({ error: errorMessage, isLoading: false });
            toast.error(errorMessage);
          }
        },
        
        /**
         * Set the current active session
         */
        setCurrentSession: (sessionId: string | null) => {
          set(state => {
            state.currentSessionId = sessionId;
            state.currentSession = sessionId ? state.sessionsMap[sessionId] || null : null;
            state.messages = sessionId ? state.messagesMap[sessionId] || [] : [];
          });
          
          // Load messages for the session if not already loaded
          if (sessionId && !get().messagesMap[sessionId]) {
            get().loadMessages(sessionId);
          }
        },
        
        // Cache management
        clearCache: () => set(state => {
          state.cache.sessions = null;
          state.cache.messages = {};
          state.sessions = [];
          state.sessionsMap = {};
          state.messagesMap = {};
          state.messages = [];
        }),
        
        isSessionsStale: () => {
          const { cache, pollingConfig } = get();
          if (!cache.sessions) return true;
          
          const now = Date.now();
          const cacheAge = now - cache.sessions.timestamp.getTime();
          return cacheAge > pollingConfig.staleThreshold;
        },
        
        isMessagesStale: (sessionId: string) => {
          const { cache, pollingConfig } = get();
          const messageCache = cache.messages[sessionId];
          if (!messageCache) return true;
          
          const now = Date.now();
          const cacheAge = now - messageCache.timestamp.getTime();
          return cacheAge > pollingConfig.staleThreshold;
        },
        
        refreshMessages: async (sessionId: string) => {
          await get().loadMessages(sessionId);
        },
        
        // Polling management
        startPolling: () => {
          const { pollingConfig, loadSessions, currentSessionId, loadMessages } = get();
          
          if (!pollingConfig.enabled) return;
          
          // Poll sessions
          pollingManager.startPolling(
            SESSIONS_POLLING_KEY,
            () => loadSessions(),
            {
              interval: pollingConfig.interval,
              maxRetries: 3,
              backoffMultiplier: 1.5,
              staleThreshold: pollingConfig.staleThreshold,
            }
          );
          
          // Poll current session messages
          if (currentSessionId) {
            pollingManager.startPolling(
              `${MESSAGES_POLLING_KEY}-${currentSessionId}`,
              () => loadMessages(currentSessionId),
              {
                interval: pollingConfig.interval,
                maxRetries: 3,
                backoffMultiplier: 1.5,
                staleThreshold: pollingConfig.staleThreshold,
              }
            );
          }
        },
        
        stopPolling: () => {
          pollingManager.stopPolling(SESSIONS_POLLING_KEY);
          
          // Stop all message polling
          const { currentSessionId } = get();
          if (currentSessionId) {
            pollingManager.stopPolling(`${MESSAGES_POLLING_KEY}-${currentSessionId}`);
          }
        },
        
        updatePollingConfig: (newConfig: Partial<StorePollingConfig>) => {
          set(state => {
            state.pollingConfig = { ...state.pollingConfig, ...newConfig };
          });
          
          // Restart polling with new config if currently active
          if (pollingManager.isPollingActive(SESSIONS_POLLING_KEY)) {
            get().stopPolling();
            get().startPolling();
          }
        },
        
        // Selectors
        getCurrentMessages: () => {
          return get().messages;
        },
        
        getSessionById: (id: string) => {
          return get().sessionsMap[id];
        },
        
        getMessagesBySessionId: (sessionId: string) => {
          return get().messagesMap[sessionId] || [];
        },
      };
    }),
    {
      name: 'chat-store-v2',
    }
  )
); 