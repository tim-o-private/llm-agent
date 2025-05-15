import React from 'react';
import SideNav from '../components/navigation/SideNav';
import TopBar from '../components/navigation/TopBar';
import { ChatPanel } from '../components/ChatPanel';
import { useChatStore } from '../stores/useChatStore';
import { OverlayManager } from '../components/overlays/OverlayManager';

interface AppShellProps {
  children: React.ReactNode;
}

const AppShell: React.FC<AppShellProps> = ({ children }) => {
  const { isChatPanelOpen } = useChatStore();

  return (
    <>
      <div className="flex h-screen bg-gray-100 dark:bg-gray-900">
        {/* Side Navigation */}
        {/* Hidden on small screens, visible and fixed width on medium and larger screens */}
        <div className="sm:hidden md:flex md:flex-shrink-0">
          <div className="flex flex-col w-64">
            <SideNav />
          </div>
        </div>

        {/* Main content area & TopBar */}
        <div className="flex flex-col flex-1 w-0 overflow-hidden">
          <div className="relative z-10 flex-shrink-0 flex h-16 bg-white dark:bg-gray-800 shadow">
            <TopBar />
          </div>

          {/* Page Content & ChatPanel container */}
          <div className="flex flex-1 relative overflow-hidden">
            <main className="flex-1 relative overflow-y-auto focus:outline-none p-6">
              {children}
            </main>
            {/* Chat Panel - slides in from the right or is overlaid */}
            {isChatPanelOpen && (
              <aside className="w-full md:w-96 bg-white dark:bg-gray-800 border-l border-gray-200 dark:border-gray-700 shadow-lg overflow-y-auto transition-all duration-300 ease-in-out">
                {/* Consider absolute positioning for overlay on smaller screens if needed */}
                {/* For now, it will take space in the flex container */}
                <ChatPanel />
              </aside>
            )}
          </div>
        </div>
      </div>
      {/* OverlayManager to handle all modal/tray type overlays */}
      <OverlayManager />
    </>
  );
};

export default AppShell; 