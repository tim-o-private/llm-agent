import React from 'react';
import { useTheme } from '../../hooks/useTheme';
import { Button } from './Button';

const ThemeToggle: React.FC = () => {
  const [theme, , toggleTheme] = useTheme();

  return (
    <Button variant="soft" onClick={toggleTheme} aria-label="Toggle theme">
      {theme === 'light' ? '🌙' : '☀️'}
    </Button>
  );
};

export default ThemeToggle; 