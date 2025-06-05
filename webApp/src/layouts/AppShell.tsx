import React from 'react';
import SideNav from '@/components/navigation/SideNav';
import TopBar from '@/components/navigation/TopBar';
import { ChatPanel } from '@/components/ChatPanel';
import { useChatUIStore } from '@/stores/useChatUIStore';
import { OverlayManager } from '@/components/overlays/OverlayManager';
import { ChatBubbleIcon, DoubleArrowRightIcon } from '@radix-ui/react-icons';

interface AppShellProps {
  children: React.ReactNode;
}

const AppShell: React.FC<AppShellProps> = ({ children }) => {
  const isChatPanelOpen = useChatUIStore((state) => state.isChatPanelOpen);
  const toggleChatPanel = useChatUIStore((state) => state.toggleChatPanel);
  
  console.log('[AppShell] isChatPanelOpen:', isChatPanelOpen);

  return (
    <>
      <div className="flex flex-col h-screen bg-gradient-to-br from-ui-bg via-ui-bg-glow to-ui-bg">
        {/* TopBar goes first for DOM order */}
        <div className="relative z-20 flex-shrink-0 flex h-16 bg-ui-element-bg/80 backdrop-blur-glass shadow-elevated border-b border-ui-border-glow">
          {/* Removed md:hidden from TopBar container, TopBar itself might have responsive logic */}
          <TopBar />
        </div>

        {/* Simple Grid Layout - No Flex Conflicts */}
        <div className="flex-1 grid grid-cols-[256px_1fr] overflow-hidden">
          {/* Sidebar - Fixed Width Column */}
          <div className="hidden md:block bg-ui-element-bg/90 backdrop-blur-glass border-r border-ui-border-glow shadow-glow">
            <SideNav />
          </div>

                     {/* Main Content - Takes Remaining Space */}
           <main 
             className="overflow-y-auto focus:outline-none p-6 relative"
             style={{
               marginRight: isChatPanelOpen ? 'calc(50vw + 4rem)' : '4rem' // Panel width + button width when open
             }}
           >
            {children}
          </main>
        </div>

        {/* Chat Panel - Fixed Positioned Outside Grid */}
        <div 
          className={`fixed top-16 bottom-0 w-1/2 bg-ui-element-bg/95 backdrop-blur-glass border-l border-ui-border-electric shadow-neon transition-transform duration-300 ease-in-out ${
            isChatPanelOpen ? 'translate-x-0' : 'translate-x-full'
          }`}
          style={{ right: '4rem' }}
        >
          <ChatPanel agentId={import.meta.env.VITE_DEFAULT_CHAT_AGENT_ID || "assistant"} />
        </div>

        {/* Chat Button - Fixed Positioned */}
        <button
          onClick={toggleChatPanel}
          className={`fixed top-16 right-0 bottom-0 w-16 flex flex-col items-center justify-center py-4 text-text-muted hover:bg-ui-interactive-bg-glow hover:text-text-electric focus:outline-none bg-ui-element-bg/90 backdrop-blur-glass border-l border-ui-border-glow shadow-glow hover:shadow-electric transition-all duration-300 ease-out ${
            isChatPanelOpen ? 'z-50 bg-ui-interactive-bg-active text-text-accent' : 'z-40'
          }`}
          aria-label={isChatPanelOpen ? "Close chat panel" : "Open chat panel"}
        >
          {isChatPanelOpen ? <DoubleArrowRightIcon className="h-6 w-6" /> : <ChatBubbleIcon className="h-6 w-6" />}
          {!isChatPanelOpen && <span className="text-xs mt-1">Chat</span>}
        </button>
      </div>
      <OverlayManager />
    </>
  );
};

export default AppShell; 