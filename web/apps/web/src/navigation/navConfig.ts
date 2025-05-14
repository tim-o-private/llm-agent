import React from 'react';
import { NavLink } from 'react-router-dom';

export interface NavItem {
  path: string;
  label: string;
  icon?: React.ReactNode; // Placeholder for actual icon components
  exact?: boolean;
}

export const navItems: NavItem[] = [
  { path: '/today', label: 'Today', icon: '[T]', exact: true }, // Assuming /today is the main view, similar to /
  { path: '/focus', label: 'Focus', icon: '[F]' },
  { path: '/coach', label: 'Coach', icon: '[C]' },
  { path: '/settings', label: 'Settings', icon: '[S]' },
]; 