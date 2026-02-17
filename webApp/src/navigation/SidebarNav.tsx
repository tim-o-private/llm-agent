import React from 'react';
import { NavLink } from 'react-router-dom';
import { Button } from '@/components/ui';

const navLinks = [
  { to: '/dashboard', label: 'Dashboard' },
  { to: '/', label: 'Home' },
];

export const SidebarNav: React.FC = () => (
  <nav className="flex flex-col gap-2">
    {navLinks.map((link) => (
      <Button asChild key={link.to} variant="soft">
        <NavLink to={link.to} end className={({ isActive }) => (isActive ? 'btn btn-primary' : 'btn btn-secondary')}>
          {link.label}
        </NavLink>
      </Button>
    ))}
  </nav>
);
