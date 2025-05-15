import React from 'react';
import { NavLink } from 'react-router-dom';
import { navItems } from '../../navigation/navConfig'; // Adjusted path

const SideNav: React.FC = () => {
  const baseStyle = "group flex items-center px-3 py-3 text-sm font-medium rounded-md";
  const inactiveStyle = "text-gray-700 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-gray-700 hover:text-gray-900 dark:hover:text-white";
  const activeStyle = "bg-gray-200 dark:bg-gray-700 text-gray-900 dark:text-white";

  return (
    <div className="flex flex-col h-full bg-white dark:bg-gray-800 border-r border-gray-200 dark:border-gray-700">
      <div className="flex items-center flex-shrink-0 px-4 h-16 border-b border-gray-200 dark:border-gray-700">
        {/* Logo or App Name Placeholder */}
        <span className="text-xl font-semibold text-gray-800 dark:text-white">Clarity</span>
      </div>
      <nav className="flex-1 mt-5 px-2 space-y-1 overflow-y-auto">
        {navItems.map((item) => (
          <NavLink
            key={item.label}
            to={item.path}
            className={({ isActive }) => 
              `${baseStyle} ${isActive ? activeStyle : inactiveStyle}`
            }
            end={item.exact}
          >
            {item.icon && <span className="mr-3 flex-shrink-0 h-6 w-6">{item.icon}</span>}
            {item.label}
          </NavLink>
        ))}
      </nav>
      {/* Optional: Footer or additional links in SideNav */}
      {/* <div className="mt-auto p-2 border-t border-gray-200 dark:border-gray-700">
        <p className="text-xs text-gray-500 dark:text-gray-400 text-center">User Profile / Logout</p>
      </div> */}
    </div>
  );
};

export default SideNav; 