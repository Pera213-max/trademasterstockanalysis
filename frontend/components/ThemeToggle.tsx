'use client';

import React from 'react';
import { useTheme } from '@/lib/theme-context';
import { Moon, Sun } from 'lucide-react';

interface ThemeToggleProps {
  className?: string;
}

const ThemeToggle: React.FC<ThemeToggleProps> = ({ className = '' }) => {
  const { theme, toggleTheme } = useTheme();

  return null;
};

export default ThemeToggle;
