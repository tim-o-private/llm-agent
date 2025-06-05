import { create } from 'zustand';

interface ChatUIStore {
  isChatPanelOpen: boolean;
  toggleChatPanel: () => void;
  setChatPanelOpen: (isOpen: boolean) => void;
}

/**
 * Store for managing chat UI state (separate from data management)
 * This handles panel visibility, focus states, etc.
 */
export const useChatUIStore = create<ChatUIStore>((set) => {
  console.log('[useChatUIStore] Store initialized with isChatPanelOpen: false');
  return {
    isChatPanelOpen: false,
    
    toggleChatPanel: () => {
      console.log('[useChatUIStore] toggleChatPanel called');
      set((state) => {
        console.log('[useChatUIStore] toggling from', state.isChatPanelOpen, 'to', !state.isChatPanelOpen);
        return { isChatPanelOpen: !state.isChatPanelOpen };
      });
    },
      
    setChatPanelOpen: (isOpen) => {
      console.log('[useChatUIStore] setChatPanelOpen called with:', isOpen);
      set({ isChatPanelOpen: isOpen });
    },
  };
}); 