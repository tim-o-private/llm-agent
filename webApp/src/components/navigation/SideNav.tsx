import React, { useRef, useState, useEffect, KeyboardEvent } from 'react';
import { NavLink, useLocation } from 'react-router-dom';
import { navItems } from '@/navigation/navConfig';

const SideNav: React.FC = () => {
  const baseStyle = "group flex items-center px-3 py-3 text-sm font-medium rounded-md focus:outline-none focus-visible:ring-2 focus-visible:ring-offset-2 focus-visible:ring-indigo-500 focus-visible:ring-offset-white dark:focus-visible:ring-offset-gray-800";
  const inactiveStyle = "text-gray-700 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-gray-700 hover:text-gray-900 dark:hover:text-white";
  const activeStyle = "bg-gray-200 dark:bg-gray-700 text-gray-900 dark:text-white";

  const navRef = useRef<HTMLElement>(null);
  const location = useLocation();
  const itemRefs = useRef<(HTMLAnchorElement | null)[]>([]);

  useEffect(() => {
    itemRefs.current = itemRefs.current.slice(0, navItems.length);
  }, []);

  const initialFocusedIndex = Math.max(0, navItems.findIndex(item => location.pathname === item.path || (item.path !== '/' && location.pathname.startsWith(item.path))));
  const [focusedIndex, setFocusedIndex] = useState<number>(initialFocusedIndex);

  useEffect(() => {
    const newActiveIndex = navItems.findIndex(item => location.pathname === item.path || (item.path !== '/' && location.pathname.startsWith(item.path)));
    if (newActiveIndex !== -1) {
      setFocusedIndex(newActiveIndex);
    }
  }, [location.pathname]);

  const handleKeyDown = (event: KeyboardEvent<HTMLElement>) => {
    if (event.key === 'ArrowDown' || event.key === 'ArrowUp') {
      event.preventDefault();
      let nextIndex;
      if (event.key === 'ArrowDown') {
        nextIndex = focusedIndex === navItems.length - 1 ? 0 : focusedIndex + 1;
      } else { // ArrowUp
        nextIndex = focusedIndex === 0 ? navItems.length - 1 : focusedIndex - 1;
      }
      setFocusedIndex(nextIndex);
      itemRefs.current[nextIndex]?.focus();
    }
  };

  useEffect(() => {
    itemRefs.current[focusedIndex]?.focus();
  }, [focusedIndex]);

  return (
    <nav 
      ref={navRef} 
      onKeyDown={handleKeyDown} 
      className="flex-1 px-2 space-y-1 overflow-y-auto pt-5"
      aria-label="Main navigation"
      role="navigation"
    >
      {navItems.map((item, index) => (
        <NavLink
          key={item.label}
          to={item.path}
          ref={el => itemRefs.current[index] = el}
          className={({ isActive }) =>
            `${baseStyle} ${isActive ? activeStyle : inactiveStyle}`
          }
          end={item.exact}
          tabIndex={index === focusedIndex ? 0 : -1}
          aria-current={location.pathname === item.path || (item.path !== '/' && location.pathname.startsWith(item.path)) ? "page" : undefined}
        >
          {item.icon && <span className="mr-3 flex-shrink-0 h-6 w-6">{item.icon}</span>}
          {item.label}
        </NavLink>
      ))}
    </nav>
  );
};

export default SideNav; 