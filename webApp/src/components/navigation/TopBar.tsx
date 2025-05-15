import React from 'react';
import { UserMenu } from '@/components/UserMenu';
import { ThemeToggle, Button } from '@/components/ui';
import { MessageSquare } from 'lucide-react';
import { useChatStore } from '@/stores/useChatStore';

const TopBar: React.FC = () => {
  const currentDate = new Date().toLocaleDateString(undefined, {
    weekday: 'long',
    year: 'numeric',
    month: 'long',
    day: 'numeric'
  });
  const { toggleChatPanel, isChatPanelOpen } = useChatStore();

  return (
    <div className="flex-1 px-4 flex justify-between items-center h-full">
      {/* Left section - Logo and optionally Mobile Nav Toggle or context actions */}
      <div className="flex items-center">
        {/* Logo or App Name Placeholder - MOVED HERE */}
        <div className="flex items-center flex-shrink-0 px-4 h-full">
           {/* The h-16 on AppShell for TopBar and border-b from SideNav logo div are now implicitly handled by TopBar's fixed height if needed */}
           {/* For alignment, ensure TopBar container (in AppShell) has items-center if logo isn't full height */}
          <span className="text-xl font-semibold text-gray-800 dark:text-white">Clarity</span>
        </div>
        {/* <button className="md:hidden ..."> Mobile Nav Toggle </button> */}
        {/* Date can be here or moved further right if logo takes precedence */}
        <span className="text-sm text-gray-600 dark:text-gray-400 hidden sm:block ml-4">
          {currentDate}
        </span>
      </div>

      {/* Center section - e.g., breadcrumbs or page title - can be empty */}
      <div className="flex-1 flex justify-center px-4 lg:ml-6 lg:justify-end">
        {/* Search bar placeholder - if needed in future */}
        {/* <div className="max-w-lg w-full lg:max-w-xs">
          <label htmlFor="search" className="sr-only">Search</label>
          <div className="relative">
            <input id="search" name="search" className="block w-full ..." placeholder="Search" type="search" />
          </div>
        </div> */}
      </div>

      {/* Right section - Streak, ThemeToggle, ChatPanel Toggle, UserMenu */}
      <div className="ml-4 flex items-center md:ml-6 space-x-3"> {/* Added space-x-3 for item spacing */}
        {/* Streak Progress Placeholder */}
        <div className="mr-3"> {/* This mr-3 might be redundant due to space-x-3 on parent */}
          <span className="text-sm font-medium text-gray-700 dark:text-gray-300">Streak:  N/A</span>
          {/* TODO: Add streak icon/progress bar */}
        </div>
        
        <ThemeToggle /> {/* Added ThemeToggle */}

        <Button 
          variant="secondary" // Consistent with AppLayout's button style for this
          onClick={toggleChatPanel} 
          aria-label={isChatPanelOpen ? 'Close chat panel' : 'Open chat panel'}
          className="p-2" // Consistent with AppLayout's button style
        >
          <MessageSquare size={20} />
        </Button>

        {/* User Menu Integration */}
        <UserMenu />
      </div>
    </div>
  );
};

export default TopBar; 