import React from 'react';
import SideNav from '@/components/navigation/SideNav';
import TopBar from '@/components/navigation/TopBar';
import { ChatPanel } from '@/components/ChatPanel';
import { useChatStore } from '@/stores/useChatStore';
import { OverlayManager } from '@/components/overlays/OverlayManager';

interface AppShellProps {
  children: React.ReactNode;
}

const AppShell: React.FC<AppShellProps> = ({ children }) => {
  const { isChatPanelOpen } = useChatStore();

  return (
    <>
      <div className="flex flex-col h-screen bg-gray-100 dark:bg-gray-900">
        {/* TopBar goes first for DOM order */}
        <div className="relative z-20 flex-shrink-0 flex h-16 bg-white dark:bg-gray-800 shadow">
          {/* Removed md:hidden from TopBar container, TopBar itself might have responsive logic */}
          <TopBar />
        </div>

        {/* Container for SideNav and Main Content + ChatPanel */}
        <div className="flex flex-1 overflow-hidden">
          {/* Side Navigation */}
          {/* Hidden on small screens (sm:hidden), visible and fixed width on medium and larger screens (md:flex) */}
          {/* SideNav container needs to be a direct child of the flex container if it's to be a flex item alongside main content area */}
          <div className="hidden md:flex md:flex-shrink-0" tabIndex={-1}>
            <div className="flex flex-col w-64">
              <SideNav />
            </div>
          </div>

          {/* Main content area & ChatPanel container */}
          {/* This div now siblings SideNav's container within the inner flex div */}
          <div className="flex flex-col flex-1 w-0 overflow-hidden">
            {/* Page Content & ChatPanel container */}
            <div className="flex flex-1 relative overflow-hidden">
              {/* Ensure main content area is focusable for scroll, or skip-to-content target */}
              <main className="flex-1 relative overflow-y-auto focus:outline-none p-6" tabIndex={-1}>
                {children}
              </main>
              {/* Chat Panel */}
              {isChatPanelOpen && (
                // Ensure aside is focusable if it contains interactive elements and needs to be part of sequence
                <aside className="w-full md:w-96 bg-white dark:bg-gray-800 border-l border-gray-200 dark:border-gray-700 shadow-lg overflow-y-auto transition-all duration-300 ease-in-out" tabIndex={-1}>
                  <ChatPanel />
                </aside>
              )}
            </div>
          </div>
        </div>
      </div>
      <OverlayManager />
    </>
  );
};

export default AppShell; 