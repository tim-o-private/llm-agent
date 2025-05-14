import React from 'react';
import { UserMenu } from '../UserMenu'; // Uncommented and ensured named import

const TopBar: React.FC = () => {
  const currentDate = new Date().toLocaleDateString(undefined, {
    weekday: 'long',
    year: 'numeric',
    month: 'long',
    day: 'numeric'
  });

  return (
    <div className="flex-1 px-4 flex justify-between items-center">
      {/* Left section - e.g., Mobile Nav Toggle or context actions - can be empty for now */}
      <div className="flex items-center">
        {/* <button className="md:hidden ..."> Mobile Nav Toggle </button> */}
        <span className="text-sm text-gray-600 dark:text-gray-400 hidden sm:block">
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

      {/* Right section - Streak, UserMenu */}
      <div className="ml-4 flex items-center md:ml-6">
        {/* Streak Progress Placeholder */}
        <div className="mr-3">
          <span className="text-sm font-medium text-gray-700 dark:text-gray-300">Streak:  N/A</span>
          {/* TODO: Add streak icon/progress bar */}
        </div>
        
        {/* User Menu Integration */}
        <UserMenu />
      </div>
    </div>
  );
};

export default TopBar; 