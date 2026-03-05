import React from 'react';
import SideNav from '@/components/navigation/SideNav';
import TopBar from '@/components/navigation/TopBar';
import { ChatPanel } from '@/components/ChatPanel';
import { useChatStore } from '@/stores/useChatStore';
import { OverlayManager } from '@/components/overlays/OverlayManager';
import { ChatBubbleIcon, DoubleArrowRightIcon } from '@radix-ui/react-icons';

interface AppShellProps {
  children: React.ReactNode;
}

const AppShell: React.FC<AppShellProps> = ({ children }) => {
  const isChatPanelOpen = useChatStore((state) => state.isChatPanelOpen);
  const toggleChatPanel = useChatStore((state) => state.toggleChatPanel);

  return (
    <>
      <div className="flex flex-col h-screen bg-gradient-to-br from-ui-bg via-ui-bg-glow to-ui-bg">
        {/* TopBar goes first for DOM order */}
        <div className="relative z-20 flex-shrink-0 flex h-16 bg-ui-element-bg/80 backdrop-blur-glass shadow-elevated border-b border-ui-border-glow">
          {/* Removed md:hidden from TopBar container, TopBar itself might have responsive logic */}
          <TopBar />
        </div>

        {/* Container for SideNav and Main Content + ChatPanel */}
        <div className="flex flex-1 overflow-hidden">
          {/* Side Navigation */}
          {/* Hidden on small screens (sm:hidden), visible and fixed width on medium and larger screens (md:flex) */}
          {/* SideNav container needs to be a direct child of the flex container if it's to be a flex item alongside main content area */}
          <div className="hidden md:flex md:flex-shrink-0" tabIndex={-1}>
            <div className="flex flex-col w-64 bg-ui-element-bg/90 backdrop-blur-glass border-r border-ui-border-glow shadow-glow">
              <SideNav />
            </div>
          </div>

          {/* Main content area & ChatPanel container */}
          <div className="flex flex-col flex-1 w-0 overflow-hidden">
            {/* Page Content & ChatPanel container */}
            <div className="flex flex-1 relative overflow-hidden">
              {/* Main Content Area - shrinks when chat opens */}
              <main
                className={`relative overflow-y-auto focus:outline-none p-4 md:p-6 transition-all duration-700 ease-in-out flex-1 main-content-area ${
                  isChatPanelOpen ? 'hidden md:block chat-open' : ''
                }`}
                tabIndex={-1}
              >
                {children}
              </main>

              {/* Chat Panel - full-width overlay on mobile, side panel on desktop */}
              <div
                className={`absolute top-0 right-0 md:right-16 bottom-0 bg-ui-element-bg/95 backdrop-blur-glass border-l border-ui-border-electric shadow-neon transition-all duration-700 ease-in-out ${
                  isChatPanelOpen
                    ? 'w-full md:w-1/2 translate-x-0 opacity-100'
                    : 'w-full md:w-1/2 translate-x-full opacity-0 pointer-events-none'
                }`}
              >
                {/* Mobile close button */}
                <button
                  onClick={toggleChatPanel}
                  className="md:hidden absolute top-3 right-3 z-10 p-2 rounded-md text-text-muted hover:text-text-primary hover:bg-ui-interactive-bg-hover transition-colors"
                  aria-label="Close chat panel"
                >
                  <DoubleArrowRightIcon className="h-5 w-5" />
                </button>
                <aside className="h-full relative overflow-y-auto" tabIndex={-1}>
                  <ChatPanel agentId={import.meta.env.VITE_DEFAULT_CHAT_AGENT_ID || 'assistant'} />
                </aside>
              </div>

              {/* Chat Toggle Button - hidden on mobile, visible on desktop */}
              <div className="hidden md:flex absolute top-0 right-0 bottom-0 w-16">
                <button
                  onClick={toggleChatPanel}
                  className={`w-16 h-full flex flex-col items-center justify-center py-4 text-text-muted hover:bg-ui-interactive-bg-glow hover:text-text-electric focus:outline-none bg-ui-element-bg/90 backdrop-blur-glass border-l border-ui-border-glow shadow-glow hover:shadow-electric transition-all duration-300 ease-out hover:scale-105 ${
                    isChatPanelOpen ? 'z-50 bg-ui-interactive-bg-active text-text-accent' : 'z-40'
                  }`}
                  aria-label={isChatPanelOpen ? 'Close chat panel' : 'Open chat panel'}
                >
                  {isChatPanelOpen ? (
                    <DoubleArrowRightIcon className="h-6 w-6" />
                  ) : (
                    <ChatBubbleIcon className="h-6 w-6" />
                  )}
                  {!isChatPanelOpen && <span className="text-xs mt-1">Chat</span>}
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>
      <OverlayManager />
    </>
  );
};

export default AppShell;
