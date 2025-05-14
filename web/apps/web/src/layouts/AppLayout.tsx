import React from 'react';
import { ThemeToggle, Button } from '@/components/ui';
import { UserMenu } from '../components/UserMenu';
import { SidebarNav } from '../navigation/SidebarNav';
import { ChatPanel } from '../components/ChatPanel';
import { useChatStore } from '../stores/useChatStore';
import { MessageSquare } from 'lucide-react';

export const AppLayout: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const { toggleChatPanel, isChatPanelOpen } = useChatStore();

  return (
    <div className="min-h-screen flex flex-col bg-[var(--color-bg)] text-[var(--color-fg)]">
      <header className="flex items-center justify-between px-6 py-4 bg-white dark:bg-gray-900 shadow">
        <div className="flex items-center gap-4">
          <span className="text-xl font-bold text-blue-700">Clarity</span>
          <ThemeToggle />
        </div>
        <div className="flex items-center gap-4">
          <Button 
            variant="secondary" 
            onClick={toggleChatPanel} 
            aria-label={isChatPanelOpen ? 'Close chat panel' : 'Open chat panel'}
            className="p-2"
          >
            <MessageSquare size={20} />
          </Button>
          <UserMenu />
        </div>
      </header>
      <div className="flex flex-1 relative">
        <aside className="hidden md:flex flex-col w-64 bg-gray-50 dark:bg-gray-800 border-r border-gray-200 dark:border-gray-700 p-4">
          <SidebarNav />
        </aside>
        <main className="flex-1 p-4 md:p-8">{children}</main>
        <ChatPanel />
      </div>
    </div>
  );
};