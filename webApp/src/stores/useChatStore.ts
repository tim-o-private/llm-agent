import { create } from 'zustand';
import { supabase } from '@/lib/supabaseClient';
import { useAuthStore } from '@/features/auth/useAuthStore';
import { generateNewChatId } from '@/api/hooks/useChatSessionHooks';
import { useEffect } from 'react';
import { toast } from '@/components/ui/toast';
import { v4 as uuidv4 } from 'uuid'; // For client-side message IDs

// Keep existing ChatMessage interface if it matches what the UI uses
export interface ChatMessage {
  id: string;
  text: string;
  sender: 'user' | 'ai' | 'tool'; // Added 'tool' sender type if applicable
  timestamp: Date;
  tool_name?: string; // Optional: for tool messages
  tool_input?: Record<string, unknown>; // Optional: for tool messages
  // Add any other fields that might come from server responses or UI needs
}

interface ChatStore {
  messages: ChatMessage[];
  isChatPanelOpen: boolean;
  activeChatId: string | null;
  currentSessionInstanceId: string | null;
  currentAgentName: string | null; // Renamed from currentAgentId
  isInitializingSession: boolean; // ADDED: Flag to prevent multiple initializations
  sendHeartbeatAsync: () => Promise<void>;

  addMessage: (message: Omit<ChatMessage, 'id' | 'timestamp'>, senderType?: 'user' | 'ai' | 'tool') => Promise<void>;
  toggleChatPanel: () => void;
  setChatPanelOpen: (isOpen: boolean) => void;
  initializeSessionAsync: (agentName: string) => Promise<void>; // Renamed and made async
  clearCurrentSessionAsync: () => Promise<void>;
  setCurrentAgentName: (agentName: string | null) => void; // Renamed
  startNewConversationAsync: (agentName: string) => Promise<void>;
  switchToConversationAsync: (chatId: string) => Promise<void>;

  // Archival related methods and state are removed assuming backend handles all message history
}

const CHAT_ID_LOCAL_STORAGE_PREFIX = 'chatUI_activeChatId';

/** Shared helper: fetch historical messages for a chat_id from the backend API. */
async function loadHistoricalMessages(chatId: string): Promise<ChatMessage[]> {
  try {
    const {
      data: { session: authSession },
    } = await supabase.auth.getSession();
    const accessToken = authSession?.access_token;
    if (!accessToken) return [];

    const apiBaseUrl = import.meta.env.VITE_API_BASE_URL || '';
    const response = await fetch(
      `${apiBaseUrl}/api/chat/sessions/${encodeURIComponent(chatId)}/messages?limit=50`,
      {
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${accessToken}`,
        },
      },
    );
    if (!response.ok) return [];

    const serverMessages = await response.json();
    const messages: ChatMessage[] = serverMessages
      .reverse()
      .map(
        (msg: { id: number; session_id: string; message: Record<string, unknown>; created_at: string }) => {
          const msgData = msg.message as Record<string, unknown>;
          const dataField = msgData?.data as Record<string, unknown> | undefined;
          const rawContent = dataField?.content ?? msgData?.content ?? '';

          // Handle content block arrays from newer langchain-anthropic
          // e.g. [{"type": "text", "text": "..."}]
          let textContent: string;
          if (Array.isArray(rawContent)) {
            textContent = rawContent
              .filter((block: unknown) => typeof block === 'object' && block !== null && (block as Record<string, unknown>).type === 'text')
              .map((block: unknown) => (block as Record<string, string>).text || '')
              .join('');
          } else {
            textContent = String(rawContent);
          }

          return {
            id: String(msg.id),
            text: textContent,
            sender: msgData?.type === 'human' ? ('user' as const) : ('ai' as const),
            timestamp: new Date(msg.created_at),
          };
        },
      )
      .filter((msg: ChatMessage) => msg.text.length > 0);
    console.log(`Loaded ${messages.length} historical messages for chat ${chatId}`);
    return messages;
  } catch (historyError) {
    console.warn('Failed to load historical messages (non-fatal):', historyError);
    return [];
  }
}

/** Shared helper: create a new session instance row in DB and return its id. */
async function createSessionInstanceInDb(
  userId: string,
  agentName: string,
  chatId: string,
): Promise<string> {
  const payload = {
    user_id: userId,
    agent_name: agentName,
    chat_id: chatId,
    is_active: true,
    updated_at: new Date().toISOString(),
  };
  const { data: newInstance, error: instanceError } = await supabase
    .from('chat_sessions')
    .insert(payload)
    .select('id')
    .single();

  if (instanceError) throw instanceError;
  if (!newInstance || !newInstance.id) throw new Error('Failed to create session instance or get its ID.');
  return newInstance.id;
}

/** Shared helper: deactivate the current session instance in DB. */
async function deactivateSessionInstance(sessionInstanceId: string, userId: string): Promise<void> {
  try {
    console.log(`Deactivating session instance: ${sessionInstanceId}`);
    await supabase
      .from('chat_sessions')
      .update({ is_active: false, updated_at: new Date().toISOString() })
      .eq('id', sessionInstanceId)
      .eq('user_id', userId);
  } catch (error) {
    console.error('Error deactivating session instance in DB:', error);
  }
}

export const useChatStore = create<ChatStore>((set, get) => ({
  messages: [], // Messages will be primarily managed by backend history; client might only hold current view if needed.
  // For now, we keep it, but it might not be populated from DB on init if backend handles full history.
  isChatPanelOpen: false,
  activeChatId: null,
  currentSessionInstanceId: null,
  currentAgentName: null,
  isInitializingSession: false, // ADDED: Initial state for the flag

  addMessage: async (message, senderTypeFromParam) => {
    const senderType = senderTypeFromParam || message.sender || 'ai';
    set((state) => ({
      messages: [
        ...state.messages,
        {
          id: uuidv4(),
          ...message,
          sender: senderType as 'user' | 'ai' | 'tool',
          timestamp: new Date(),
        },
      ],
    }));

    // Heartbeat: Update the current session instance
    const { currentSessionInstanceId } = get();
    const user = useAuthStore.getState().user;
    if (currentSessionInstanceId && user) {
      try {
        await supabase
          .from('chat_sessions')
          .update({ updated_at: new Date().toISOString(), is_active: true })
          .eq('id', currentSessionInstanceId)
          .eq('user_id', user.id); // Ensure user owns it
        // console.log('Heartbeat: Session instance updated', currentSessionInstanceId);
      } catch (error) {
        console.error('Error sending heartbeat update:', error);
        // Non-critical, chat continues locally
      }
    }
  },

  toggleChatPanel: () => set((state) => ({ isChatPanelOpen: !state.isChatPanelOpen })),
  setChatPanelOpen: (isOpen) => set({ isChatPanelOpen: isOpen }),
  setCurrentAgentName: (agentName) => set({ currentAgentName: agentName }),

  initializeSessionAsync: async (agentName: string) => {
    if (get().isInitializingSession) {
      console.log('Session initialization already in progress. Skipping.');
      return;
    }
    set({ isInitializingSession: true });

    const user = useAuthStore.getState().user;
    if (!user) {
      console.warn('User not authenticated, cannot initialize session.');
      set({ activeChatId: null, currentSessionInstanceId: null, currentAgentName: null, messages: [] });
      return;
    }

    console.log(`Initializing chat session for agent: ${agentName}, user: ${user.id}`);
    let chatIdToUse: string | null = null;
    let newSessionInstanceId: string | null = null;

    const localStorageKey = `${CHAT_ID_LOCAL_STORAGE_PREFIX}_${user.id}_${agentName}`;

    // 1. Try localStorage for an existing CHAT_ID
    const persistedChatId = localStorage.getItem(localStorageKey);
    if (persistedChatId) {
      console.log(`Found persisted Chat ID in localStorage: ${persistedChatId}`);
      chatIdToUse = persistedChatId;
      // Later, we could re-validate this chat_id against DB if needed, but for now, trust and proceed.
    }

    // 2. If not in localStorage, try fetching the latest CHAT_ID from DB ( mimicking useFetchLatestChatId logic)
    if (!chatIdToUse) {
      console.log('Attempting to fetch latest Chat ID from DB...');
      // Try active sessions first
      const { data: activeSessions, error: activeError } = await supabase
        .from('chat_sessions')
        .select('chat_id')
        .eq('user_id', user.id)
        .eq('agent_name', agentName)
        .eq('is_active', true)
        .order('updated_at', { ascending: false })
        .limit(1);

      if (activeError) console.error('Error fetching active chat_id for init:', activeError);

      if (activeSessions && activeSessions.length > 0 && activeSessions[0].chat_id) {
        chatIdToUse = activeSessions[0].chat_id;
      } else {
        // If no active, try most recent inactive
        const { data: inactiveSessions, error: inactiveError } = await supabase
          .from('chat_sessions')
          .select('chat_id')
          .eq('user_id', user.id)
          .eq('agent_name', agentName)
          .order('updated_at', { ascending: false })
          .limit(1);
        if (inactiveError) console.error('Error fetching inactive chat_id for init:', inactiveError);
        if (inactiveSessions && inactiveSessions.length > 0 && inactiveSessions[0].chat_id) {
          chatIdToUse = inactiveSessions[0].chat_id;
        }
      }
      if (chatIdToUse) {
        console.log(`Fetched existing Chat ID from DB: ${chatIdToUse}`);
        localStorage.setItem(localStorageKey, chatIdToUse);
      }
    }

    // 3. If still no Chat ID, generate a new one
    if (!chatIdToUse) {
      chatIdToUse = generateNewChatId();
      console.log(`Generated new Chat ID: ${chatIdToUse}`);
      localStorage.setItem(localStorageKey, chatIdToUse);
    }

    // 4. Now, create a NEW SESSION INSTANCE in chat_sessions table for this client engagement
    try {
      newSessionInstanceId = await createSessionInstanceInDb(user.id, agentName, chatIdToUse);
      console.log(
        `Successfully created new session instance in DB. ID: ${newSessionInstanceId}, Chat ID: ${chatIdToUse}`,
      );

      // 5. Load historical messages from server
      const historicalMessages = chatIdToUse ? await loadHistoricalMessages(chatIdToUse) : [];

      set({
        activeChatId: chatIdToUse,
        currentSessionInstanceId: newSessionInstanceId,
        currentAgentName: agentName,
        messages: historicalMessages,
      });
      console.log(
        `Chat store initialized. Agent: ${agentName}, Active Chat ID: ${chatIdToUse}, Session Instance ID: ${newSessionInstanceId}, Historical messages: ${historicalMessages.length}`,
      );
    } catch (error) {
      console.error('Error creating new session instance in DB:', error);
      toast.error('Failed to initialize chat session. Please try again.');
      // Fallback: local session without DB instance, or clear out?
      // For now, if DB interaction fails, we won't have a currentSessionInstanceId.
      set({
        activeChatId: chatIdToUse, // Keep chat_id for message history if possible
        currentSessionInstanceId: null,
        currentAgentName: agentName,
        messages: [],
      });
    } finally {
      set({ isInitializingSession: false }); // ADDED: Reset the flag in finally block
    }
  },

  clearCurrentSessionAsync: async () => {
    const { currentSessionInstanceId, currentAgentName } = get();
    const user = useAuthStore.getState().user;

    if (currentSessionInstanceId && user) {
      await deactivateSessionInstance(currentSessionInstanceId, user.id);
    }

    if (user && typeof currentAgentName === 'string') {
      console.log(
        `Chat session instance ${currentSessionInstanceId} marked inactive (if applicable). Local store state clearing.`,
      );
    }

    set({
      messages: [],
      currentSessionInstanceId: null,
    });
    console.log(
      'Current session instance ID cleared. Active chat ID and agent name retained for potential resumption.',
    );
  },

  startNewConversationAsync: async (agentName: string) => {
    const user = useAuthStore.getState().user;
    if (!user) {
      console.warn('User not authenticated, cannot start new conversation.');
      return;
    }

    // 1. Deactivate current session instance
    const { currentSessionInstanceId } = get();
    if (currentSessionInstanceId) {
      await deactivateSessionInstance(currentSessionInstanceId, user.id);
    }

    // 2. Generate new chatId
    const newChatId = generateNewChatId();
    console.log(`Starting new conversation with Chat ID: ${newChatId}`);

    // 3. Create new session instance in DB
    try {
      const newSessionInstanceId = await createSessionInstanceInDb(user.id, agentName, newChatId);

      // 4. Update localStorage
      const localStorageKey = `${CHAT_ID_LOCAL_STORAGE_PREFIX}_${user.id}_${agentName}`;
      localStorage.setItem(localStorageKey, newChatId);

      // 5. Clear messages, update activeChatId
      set({
        messages: [],
        activeChatId: newChatId,
        currentSessionInstanceId: newSessionInstanceId,
        currentAgentName: agentName,
      });
      console.log(`New conversation started. Chat ID: ${newChatId}, Session Instance: ${newSessionInstanceId}`);
    } catch (error) {
      console.error('Error starting new conversation:', error);
      toast.error('Failed to start new conversation. Please try again.');
    }
  },

  switchToConversationAsync: async (chatId: string) => {
    const user = useAuthStore.getState().user;
    const { currentSessionInstanceId, currentAgentName } = get();
    if (!user) {
      console.warn('User not authenticated, cannot switch conversation.');
      return;
    }
    if (!currentAgentName) {
      console.warn('No current agent name set, cannot switch conversation.');
      return;
    }

    // 1. Deactivate current session instance
    if (currentSessionInstanceId) {
      await deactivateSessionInstance(currentSessionInstanceId, user.id);
    }

    // 2. Set activeChatId
    console.log(`Switching to conversation: ${chatId}`);

    try {
      // 3. Load historical messages
      const historicalMessages = await loadHistoricalMessages(chatId);

      // 4. Create new session instance in DB
      const newSessionInstanceId = await createSessionInstanceInDb(user.id, currentAgentName, chatId);

      // 5. Update localStorage
      const localStorageKey = `${CHAT_ID_LOCAL_STORAGE_PREFIX}_${user.id}_${currentAgentName}`;
      localStorage.setItem(localStorageKey, chatId);

      // 6. Update store state
      set({
        activeChatId: chatId,
        currentSessionInstanceId: newSessionInstanceId,
        messages: historicalMessages,
      });
      console.log(
        `Switched to conversation ${chatId}. Session Instance: ${newSessionInstanceId}, Messages: ${historicalMessages.length}`,
      );
    } catch (error) {
      console.error('Error switching conversation:', error);
      toast.error('Failed to switch conversation. Please try again.');
    }
  },

  sendHeartbeatAsync: async () => {
    const { currentSessionInstanceId } = get();
    const user = useAuthStore.getState().user;
    if (currentSessionInstanceId && user) {
      try {
        // console.log('Sending explicit heartbeat for session instance:', currentSessionInstanceId);
        await supabase
          .from('chat_sessions')
          .update({ updated_at: new Date().toISOString(), is_active: true })
          .eq('id', currentSessionInstanceId)
          .eq('user_id', user.id);
      } catch (error) {
        console.error('Error sending explicit heartbeat:', error);
      }
    } else {
      // console.warn('Cannot send heartbeat: no currentSessionInstanceId or user.');
    }
  },
}));

// Hook to initialize and clean up the store's session management
export const useInitializeChatStore = (agentName: string | null | undefined) => {
  const user = useAuthStore.getState().user;
  const initializeSessionAsync = useChatStore.getState().initializeSessionAsync;
  const clearCurrentSessionAsync = useChatStore.getState().clearCurrentSessionAsync;
  const currentStoreAgentName = useChatStore.getState().currentAgentName;
  const currentStoreSessionInstanceId = useChatStore.getState().currentSessionInstanceId;

  useEffect(() => {
    if (agentName && user?.id) {
      if (agentName !== currentStoreAgentName || !currentStoreSessionInstanceId) {
        console.log(`useInitializeChatStore effect: Initializing for agent: ${agentName}`);
        // If there was a different agent active, clear its session instance first.
        // This check is important to avoid deactivating a session for an agent that's still open in another tab/component if we extend to that.
        // For now, assuming one ChatPanel, if agentName changes, previous session instance should be cleared.
        if (currentStoreSessionInstanceId && currentStoreAgentName && currentStoreAgentName !== agentName) {
          console.log(
            `useInitializeChatStore: Agent changed from ${currentStoreAgentName} to ${agentName}. Clearing previous session instance.`,
          );
          clearCurrentSessionAsync(); // Deactivate previous session instance
        }
        initializeSessionAsync(agentName);
      }
    } else {
      console.log('useInitializeChatStore: No agentName or user. Clearing current session instance.');
      if (currentStoreSessionInstanceId) {
        // Only clear if there was an active instance
        clearCurrentSessionAsync();
      }
    }

    // Cleanup on unmount or when agentName/user.id changes before re-init for a *new* agent.
    // The logic inside the main effect body already handles clearing the *previous* if agentName changes.
    // This specific return function is more for when the component using this hook unmounts entirely.
    return () => {
      // This cleanup will run if the component that uses useInitializeChatStore unmounts.
      // For example, if ChatPanel is conditionally rendered and then removed from UI.
      // We should mark its session as inactive.
      const stillSameAgentAndUser =
        useChatStore.getState().currentAgentName === agentName && useAuthStore.getState().user?.id === user?.id;
      const activeInstanceId = useChatStore.getState().currentSessionInstanceId;

      if (activeInstanceId && stillSameAgentAndUser) {
        // Only clear if this instance was the one this effect was responsible for.
        console.log(`useInitializeChatStore cleanup: Deactivating session instance for agent ${agentName}`);
        clearCurrentSessionAsync();
      }
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [agentName, user?.id, initializeSessionAsync, clearCurrentSessionAsync]); // currentStoreAgentName and currentStoreSessionInstanceId are NOT dependencies here to avoid loops
};

// Example of how a component would use the store and the RQ mutation hook:
// import { useEffect } from 'react';
// import { useChatStore } from './path-to-your-store/useChatStore';
// import { useArchiveChatMutation } from '../api/hooks/useChatApiHooks'; // Adjust path

// const ChatManager = () => {
//   const {
//     sessionId, currentAgentId, messages,
//     lastArchivedMessageCount, isArchiving: storeIsArchivingMarker,
//     initializeSession, archiveChatSession: triggerStoreArchiveLogic, clearChatSession
//   } = useChatStore();

//   const archiveMutation = useArchiveChatMutation();

//   // Effect for periodic and visibility-triggered archival
//   useEffect(() => {
//     const attemptArchive = (isUnloading = false) => {
//       const state = useChatStore.getState(); // Get fresh state
//       if (state.sessionId && state.currentAgentId && (state.messages.length > state.lastArchivedMessageCount || isUnloading)) {
//         const messagesToArchive = state.messages.slice(state.lastArchivedMessageCount);
//         const finalMessages = messagesToArchive.length > 0 ? messagesToArchive : (isUnloading && state.messages.length > 0 ? state.messages : []);

//         if (finalMessages.length > 0 && !archiveMutation.isLoading) {
//           console.log(`ChatManager: Calling archive mutation. Unloading: ${isUnloading}`);
//           archiveMutation.mutate({
//             sessionId: state.sessionId,
//             agentId: state.currentAgentId,
//             messages: finalMessages.map(m => ({...m, timestamp: new Date(m.timestamp)})),
//             isUnloading,
//           }, {
//             onSuccess: (data) => {
//               if (data.success) {
//                 useChatStore.setState({ lastArchivedMessageCount: state.messages.length, isArchiving: false });
//               } else {
//                 useChatStore.setState({ isArchiving: false }); // Reset on API failure too
//               }
//             },
//             onError: () => {
//               useChatStore.setState({ isArchiving: false });
//             }
//           });
//         }
//       }
//     };

//     // Handle store's signal for archival (e.g. from periodic timer)
//     if (storeIsArchivingMarker && !archiveMutation.isLoading) {
//        console.log("ChatManager: Store signaled archive, attempting mutation.");
//        attemptArchive(false); // Call with isUnloading false
//        useChatStore.setState({ isArchiving: false }); // Reset store marker
//     }

//     const handleBeforeUnload = () => attemptArchive(true);
//     const handleVisibilityChange = () => {
//       if (document.visibilityState === 'hidden') attemptArchive(false);
//     };

//     window.addEventListener('beforeunload', handleBeforeUnload);
//     document.addEventListener('visibilitychange', handleVisibilityChange);

//     return () => {
//       window.removeEventListener('beforeunload', handleBeforeUnload);
//       document.removeEventListener('visibilitychange', handleVisibilityChange);
//       attemptArchive(false); // Final attempt on unmount
//     };
//   }, [storeIsArchivingMarker, archiveMutation]); // archiveMutation itself is stable

//   // Initialize session on mount (example)
//   useEffect(() => {
//     initializeSession('test-agent-001');
//     return () => {
//       clearChatSession(); // Also clears periodic timer in store
//     };
//   }, [initializeSession, clearChatSession]);

//   return null; // Manager component
// };

// export default ChatManager;
