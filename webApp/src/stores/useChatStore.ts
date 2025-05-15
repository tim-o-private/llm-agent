import { create } from 'zustand';

interface ChatMessage {
  id: string;
  text: string;
  sender: 'user' | 'ai';
  timestamp: Date;
}

interface ChatStore {
  messages: ChatMessage[];
  isChatPanelOpen: boolean;
  addMessage: (message: Omit<ChatMessage, 'id' | 'timestamp'>) => void;
  toggleChatPanel: () => void;
  setChatPanelOpen: (isOpen: boolean) => void;
}

export const useChatStore = create<ChatStore>((set) => ({
  messages: [],
  isChatPanelOpen: false, // Default to closed
  addMessage: (message) =>
    set((state) => ({
      messages: [
        ...state.messages,
        { ...message, id: Date.now().toString(), timestamp: new Date() },
      ],
    })),
  toggleChatPanel: () =>
    set((state) => ({ isChatPanelOpen: !state.isChatPanelOpen })),
  setChatPanelOpen: (isOpen) => set(() => ({ isChatPanelOpen: isOpen })),
})); 