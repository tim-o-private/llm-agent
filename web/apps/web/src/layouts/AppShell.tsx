import React from 'react';
import SideNav from '../components/navigation/SideNav';
import TopBar from '../components/navigation/TopBar';

interface AppShellProps {
  children: React.ReactNode;
}

const AppShell: React.FC<AppShellProps> = ({ children }) => {
  // TODO: Implement state for mobile SideNav toggle if needed
  // const [isMobileNavOpen, setIsMobileNavOpen] = React.useState(false);

  return (
    <div className="flex h-screen bg-gray-100 dark:bg-gray-900">
      {/* Side Navigation */}
      {/* Hidden on small screens, visible and fixed width on medium and larger screens */}
      <div className="sm:hidden md:flex md:flex-shrink-0">
        <div className="flex flex-col w-64">
          <SideNav />
        </div>
      </div>

      {/* Mobile SideNav (placeholder for toggle mechanism) */}
      {/* 
      {isMobileNavOpen && (
        <div className="md:hidden fixed inset-0 flex z-40">
          <div className="fixed inset-0 bg-black opacity-50" onClick={() => setIsMobileNavOpen(false)}></div>
          <div className="relative flex-1 flex flex-col max-w-xs w-full bg-white dark:bg-gray-800">
            <SideNav />
          </div>
        </div>
      )}
      */}

      {/* Main content area */}
      <div className="flex flex-col flex-1 w-0 overflow-hidden">
        {/* Top Bar */}
        <div className="relative z-10 flex-shrink-0 flex h-16 bg-white dark:bg-gray-800 shadow">
          {/* Placeholder for mobile nav toggle button if SideNav is outside TopBar for mobile */}
          {/* 
          <button 
            onClick={() => setIsMobileNavOpen(!isMobileNavOpen)} 
            className="md:hidden px-4 border-r border-gray-200 dark:border-gray-700 text-gray-500 dark:text-gray-400 focus:outline-none focus:ring-2 focus:ring-inset focus:ring-indigo-500"
          >
            <span className="sr-only">Open sidebar</span>
            {/* Heroicon name: outline/menu-alt-2 */}
            {/* <svg className="h-6 w-6" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor" aria-hidden="true"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M4 6h16M4 12h16M4 18h7" /></svg> */}
          {/* </button> 
          */}
          <TopBar />
        </div>

        {/* Page Content */}
        <main className="flex-1 relative overflow-y-auto focus:outline-none p-6">
          {children}
        </main>
      </div>
    </div>
  );
};

export default AppShell; 