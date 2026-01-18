'use client';

import React from 'react';
import { useTheme } from '@/lib/theme-context';
import { Moon, Sun } from 'lucide-react';

interface ThemeToggleProps {
  className?: string;
}

const ThemeToggle: React.FC<ThemeToggleProps> = ({ className = '' }) => {
  const { theme, toggleTheme } = useTheme();

  return (
    <button
      onClick={toggleTheme}
      className={`relative inline-flex items-center justify-center p-2 rounded-lg
        bg-gray-800 dark:bg-gray-800 hover:bg-gray-700 dark:hover:bg-gray-700
        border border-gray-700 dark:border-gray-700 transition-all duration-200
        group ${className}`}
      aria-label="Toggle theme"
    >
      {/* Sun Icon (Light Mode) */}
      <Sun
        className={`absolute w-5 h-5 text-yellow-400 transition-all duration-300 ${
          theme === 'light'
            ? 'opacity-100 rotate-0 scale-100'
            : 'opacity-0 rotate-90 scale-0'
        }`}
      />

      {/* Moon Icon (Dark Mode) */}
      <Moon
        className={`absolute w-5 h-5 text-blue-400 transition-all duration-300 ${
          theme === 'dark'
            ? 'opacity-100 rotate-0 scale-100'
            : 'opacity-0 -rotate-90 scale-0'
        }`}
      />

      {/* Placeholder for sizing */}
      <div className="w-5 h-5 opacity-0">
        <Sun className="w-5 h-5" />
      </div>
    </button>
  );
};

export default ThemeToggle;
