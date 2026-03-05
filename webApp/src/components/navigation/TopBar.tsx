import React from 'react';
import { UserMenu } from '@/components/UserMenu';
import ThemeToggle from '@/components/ui/ThemeToggle';
import { useChatStore } from '@/stores/useChatStore';
import { ChatBubbleIcon } from '@radix-ui/react-icons';

const TopBar: React.FC = () => {
  const currentDate = new Date().toLocaleDateString(undefined, {
    weekday: 'long',
    year: 'numeric',
    month: 'long',
    day: 'numeric',
  });

  const toggleChatPanel = useChatStore((state) => state.toggleChatPanel);

  return (
    <div className="flex-1 px-2 sm:px-4 flex justify-between items-center h-full min-w-0">
      {/* Left section - Logo */}
      <div className="flex items-center min-w-0">
        <div className="flex items-center flex-shrink-0 px-2 sm:px-4 h-full">
          <span className="text-xl font-semibold text-text-primary">Clarity</span>
        </div>
        <span className="text-sm text-text-muted hidden md:block ml-4 truncate">{currentDate}</span>
      </div>

      {/* Spacer */}
      <div className="flex-1" />

      {/* Right section */}
      <div className="flex items-center space-x-2 sm:space-x-3 flex-shrink-0">
        {/* Streak - hidden on mobile */}
        <div className="hidden sm:block">
          <span className="text-sm font-medium text-text-secondary whitespace-nowrap">Streak: N/A</span>
        </div>
        <ThemeToggle />
        {/* Mobile chat toggle - visible only on mobile (desktop uses AppShell sidebar button) */}
        <button
          onClick={toggleChatPanel}
          className="md:hidden p-2 rounded-md text-text-muted hover:text-text-primary hover:bg-ui-interactive-bg-hover transition-colors"
          aria-label="Toggle chat"
        >
          <ChatBubbleIcon className="h-5 w-5" />
        </button>
        <UserMenu />
      </div>
    </div>
  );
};

export default TopBar;
