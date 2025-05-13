import React from 'react';
import { useTheme } from '../../hooks/useTheme';
import { Button } from './Button';

export const ThemeToggle: React.FC = () => {
  const [theme, , toggleTheme] = useTheme();
  return (
    <Button variant="secondary" onClick={toggleTheme} aria-label="Toggle theme">
      {theme === 'light' ? '🌙 Dark' : '☀️ Light'}
    </Button>
  );
}; 