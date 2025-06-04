import React, { useRef, useState, useEffect, KeyboardEvent } from 'react';
import { NavLink, useLocation } from 'react-router-dom';
import { navItems } from '@/navigation/navConfig';
import { clsx } from 'clsx';
import { getFocusClasses } from '@/utils/focusStates';

const baseStyle = clsx(
  "group flex items-center px-3 py-3 text-sm font-medium rounded-md transition-colors",
  getFocusClasses()
);

const SideNav: React.FC = () => {
  const inactiveStyle = "text-text-secondary hover:bg-ui-interactive-bg-hover hover:text-text-primary";
  const activeStyle = "bg-accent-surface text-text-accent border-l-2 border-brand-primary";

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