import { create } from 'zustand';
import { v4 as uuidv4 } from 'uuid'; // For generating session IDs
import { supabase } from '@/lib/supabaseClient'; // For direct DB interaction
import { useAuthStore } from '@/features/auth/useAuthStore'; // To get userId
import { generateNewSessionId, UserAgentActiveSession } from '@/api/hooks/useChatSessionHooks'; // For new session IDs and type

import { useEffect } from 'react';

// Keep existing ChatMessage interface if it matches what the UI uses
export interface ChatMessage {
  id: string;
  text: string;
  sender: 'user' | 'ai' | 'tool'; // Added 'tool' sender type if applicable
  timestamp: Date;
  tool_name?: string; // Optional: for tool messages
  tool_input?: Record<string, any>; // Optional: for tool messages
  // Add any other fields that might come from server responses or UI needs
}

interface ChatStore {
  messages: ChatMessage[];
  isChatPanelOpen: boolean;
  sessionId: string | null;
  currentAgentName: string | null; // Renamed from currentAgentId

  addMessage: (message: Omit<ChatMessage, 'id' | 'timestamp'>, senderType?: 'user' | 'ai' | 'tool') => void;
  toggleChatPanel: () => void;
  setChatPanelOpen: (isOpen: boolean) => void;
  initializeSessionAsync: (agentName: string) => Promise<void>; // Renamed and made async
  clearCurrentSession: () => void;
  setCurrentAgentName: (agentName: string | null) => void; // Renamed

  // Archival related methods and state are removed assuming backend handles all message history
}

export const useChatStore = create<ChatStore>((set, get) => ({
  messages: [], // Messages will be primarily managed by backend history; client might only hold current view if needed.
                // For now, we keep it, but it might not be populated from DB on init if backend handles full history.
  isChatPanelOpen: false,
  sessionId: null,
  currentAgentName: null,

  addMessage: (message, senderTypeFromParam) => {
    const senderType = senderTypeFromParam || (message.sender || 'ai');
    set((state) => ({
      messages: [
        ...state.messages,
        { 
          id: uuidv4(), 
          ...message, 
          sender: senderType as 'user' | 'ai' | 'tool',
          timestamp: new Date() 
        },
      ],
    }));
  },

  toggleChatPanel: () =>
    set((state) => ({ isChatPanelOpen: !state.isChatPanelOpen })),
  setChatPanelOpen: (isOpen) => set({ isChatPanelOpen: isOpen }),
  setCurrentAgentName: (agentName) => set({ currentAgentName: agentName }),

  initializeSessionAsync: async (agentName: string) => {
    const user = useAuthStore.getState().user;
    if (!user) {
      console.warn("User not authenticated, cannot initialize session.");
      set({ sessionId: null, currentAgentName: null, messages: [] });
      return;
    }

    console.log(`Initializing chat session for agent: ${agentName}, user: ${user.id}`);
    let finalSessionId: string | null = null;

    const localStorageKey = `chatSession_${user.id}_${agentName}`;

    // 1. Try localStorage
    const persistedSessionId = localStorage.getItem(localStorageKey);
    if (persistedSessionId) {
      console.log(`Found persisted session ID in localStorage: ${persistedSessionId}`);
      // Optional: Validate persistedSessionId against DB to ensure it's still the most recent / valid.
      // For simplicity now, we trust it if found, but DB check is more robust.
      // Let's add a simple check to see if it exists in user_agent_active_sessions.
      const { data: dbSessionValidation, error: dbValidationError } = await supabase
        .from('user_agent_active_sessions')
        .select('active_session_id')
        .eq('user_id', user.id)
        .eq('agent_name', agentName)
        .eq('active_session_id', persistedSessionId)
        .maybeSingle();

      if (dbValidationError && dbValidationError.code !== 'PGRST116') {
        console.error("Error validating persisted session ID against DB:", dbValidationError);
        // Proceed to fetch latest from DB or create new
      } else if (dbSessionValidation) {
        finalSessionId = persistedSessionId;
        console.log("Validated persisted session ID with DB.");
      } else {
        console.log("Persisted session ID from localStorage not found or invalid in DB. Will fetch/create new.");
        localStorage.removeItem(localStorageKey); // Clear invalid/stale ID
      }
    }

    // 2. If not found/validated in localStorage, try fetching the latest from DB
    if (!finalSessionId) {
      console.log("Attempting to fetch latest active session from DB...");
      const { data: latestDbSession, error: fetchError } = await supabase
        .from('user_agent_active_sessions')
        .select('*') 
        .eq('user_id', user.id)
        .eq('agent_name', agentName)
        .order('last_active_at', { ascending: false })
        .limit(1)
        .maybeSingle<UserAgentActiveSession>();

      if (fetchError) {
        console.error("Error fetching latest active session from DB:", fetchError);
      } else if (latestDbSession && latestDbSession.active_session_id) { 
        const dbSessionId = latestDbSession.active_session_id; // dbSessionId is definitely a string here
        finalSessionId = dbSessionId; // Assign to finalSessionId (which is string | null)
        console.log(`Fetched latest active session ID from DB: ${dbSessionId}`);
        localStorage.setItem(localStorageKey, dbSessionId); // Use the definitely-string dbSessionId for setItem
      } else {
        console.log("No active session found in DB or active_session_id was null.");
      }
    }

    // 3. If still no session ID, generate a new one and save it
    if (!finalSessionId) {
      finalSessionId = generateNewSessionId();
      console.log(`Generated new session ID: ${finalSessionId}`);
      localStorage.setItem(localStorageKey, finalSessionId);
      
      const { error: upsertError } = await supabase
        .from('user_agent_active_sessions')
        .upsert({
          user_id: user.id,
          agent_name: agentName,
          active_session_id: finalSessionId,
          last_active_at: new Date().toISOString(),
        }, { onConflict: 'user_id, agent_name' })
        .select()
        .single();

      if (upsertError) {
        console.error("Error upserting new active session to DB:", upsertError);
        // If DB upsert fails, we still use the generated ID locally for this client session
        // but it won't persist across devices/browsers until DB is reachable.
      } else {
        console.log("Successfully upserted new active session to DB.");
      }
    }
    
    set({
      sessionId: finalSessionId,
      currentAgentName: agentName,
      messages: [], // Messages will be loaded from PostgresChatMessageHistory by the backend
    });
    console.log(`Chat session initialized. Agent: ${agentName}, Session ID: ${finalSessionId}`);
    // Old archival listeners and timers are removed
  },

  clearCurrentSession: () => {
    // No client-side archival to trigger here anymore.
    // Simply clear local state.
    const state = get();
    const currentUser = useAuthStore.getState().user;

    if (currentUser && typeof state.currentAgentName === 'string') {
        const agentNameForLocalStorage: string = state.currentAgentName; // Explicitly typed new variable
        const localStorageKey = `chatSession_${currentUser.id}_${agentNameForLocalStorage}`;
        localStorage.removeItem(localStorageKey);
        console.log(`Cleared localStorage key for ${agentNameForLocalStorage}: ${localStorageKey}`);
    }

    set({
      messages: [],
      sessionId: null,
      currentAgentName: null,
    });
    console.log("Chat session cleared locally.");
  },
}));

// Hook to initialize and clean up the store's session management
export const useInitializeChatStore = (agentName: string | null | undefined) => {
  const user = useAuthStore((state) => state.user);

  useEffect(() => {
    if (agentName && user?.id) {
      console.log(`useInitializeChatStore effect triggered for agent: ${agentName}`);
      useChatStore.getState().initializeSessionAsync(agentName);
    } else {
      // If no agentName or user, ensure session is cleared or not initialized
      // This might happen if agent is deselected or user logs out
      console.log("useInitializeChatStore: No agentName or user, potentially clearing session or ensuring it's null.");
      const currentSessionId = useChatStore.getState().sessionId;
      if (currentSessionId !== null || useChatStore.getState().currentAgentName !== null) {
          // If there was an active session, clear it. 
          // Avoids clearing if it's already null to prevent loops if not careful with deps.
          useChatStore.getState().clearCurrentSession();
      }
    }

    // No specific cleanup needed here anymore as listeners are removed.
    // If initializeSessionAsync were to set up anything that needs teardown per agent/user,
    // it would go here.
    return () => {
        // Consider if any cleanup is needed when agentName/user changes *before* re-init.
        // For now, clearCurrentSession handles removing localStorage for the *previous* agent
        // if called directly.
        // If an agent is simply switched, the new initializeSessionAsync will handle the new agent's localStorage.
    };
  }, [agentName, user?.id]); // Re-run if agentName or user.id changes
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