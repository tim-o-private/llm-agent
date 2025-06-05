import React from 'react';
import { UserMenu } from '@/components/UserMenu';
import ThemeToggle from '@/components/ui/ThemeToggle';
import { Button } from '@/components/ui/Button';
import { useChatUIStore } from '@/stores/useChatUIStore';

const TopBar: React.FC = () => {
  const currentDate = new Date().toLocaleDateString(undefined, {
    weekday: 'long',
    year: 'numeric',
    month: 'long',
    day: 'numeric'
  });

  const { toggleChatPanel } = useChatUIStore();

  return (
    <div className="flex-1 px-4 flex justify-between items-center h-full">
      {/* Left section - Logo and optionally Mobile Nav Toggle or context actions */}
      <div className="flex items-center">
        {/* Logo or App Name Placeholder - MOVED HERE */}
        <div className="flex items-center flex-shrink-0 px-4 h-full">
           {/* The h-16 on AppShell for TopBar and border-b from SideNav logo div are now implicitly handled by TopBar's fixed height if needed */}
           {/* For alignment, ensure TopBar container (in AppShell) has items-center if logo isn't full height */}
          <span className="text-xl font-semibold text-text-primary">Clarity</span>
        </div>
        {/* <button className="md:hidden ..."> Mobile Nav Toggle </button> */}
        {/* Date can be here or moved further right if logo takes precedence */}
        <span className="text-sm text-text-muted hidden sm:block ml-4">
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

      {/* Right section - Streak, ThemeToggle, UserMenu */}
      <div className="ml-4 flex items-center md:ml-6 space-x-3"> {/* Added space-x-3 for item spacing */}
        {/* Streak Progress Placeholder */}
        <div className="mr-3"> {/* This mr-3 might be redundant due to space-x-3 on parent */}
          <span className="text-sm font-medium text-text-secondary">Streak:  N/A</span>
          {/* TODO: Add streak icon/progress bar */}
        </div>
        
        <ThemeToggle /> {/* Added ThemeToggle */}

        {/* REMOVING CHAT TOGGLE BUTTON FROM TOPBAR - Now handled in TodayView */}
        <Button 
          variant="soft" 
          onClick={toggleChatPanel}
          className="lg:hidden"
        >
          ��
        </Button>

        {/* User Menu Integration */}
        <UserMenu />
      </div>
    </div>
  );
};

export default TopBar; 