import React from 'react';
import { NavLink } from 'react-router-dom';
import { Button } from '@clarity/ui';

const navLinks = [
  { to: '/dashboard', label: 'Dashboard' },
  { to: '/', label: 'Home' },
];

export const SidebarNav: React.FC = () => (
  <nav className="flex flex-col gap-2">
    {navLinks.map((link) => (
      <Button
        asChild
        key={link.to}
        variant="secondary"
        className={({ isActive }: any) =>
          isActive ? 'btn-primary' : ''
        }
      >
        <NavLink to={link.to} end>{link.label}</NavLink>
      </Button>
    ))}
  </nav>
); 