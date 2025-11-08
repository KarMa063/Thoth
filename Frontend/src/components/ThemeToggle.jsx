import React, { useEffect, useState } from "react";
import { initializeTheme, toggleTheme, setupThemeListener } from "../utils/themeManager";

function ThemeToggle() {
  const [darkMode, setDarkMode] = useState(false);

  useEffect(() => {
    // Initialize theme and set state
    const currentTheme = initializeTheme();
    setDarkMode(currentTheme === 'dark');
    
    // Setup listener for system theme changes
    setupThemeListener((newTheme) => {
      setDarkMode(newTheme === 'dark');
    });
  }, []);

  const handleToggle = () => {
    const newTheme = toggleTheme();
    setDarkMode(newTheme === 'dark');
  };

  return (
    <button 
      onClick={handleToggle} 
      className="theme-toggle"
      aria-label="Toggle dark mode"
    >
      {darkMode ? '☀️' : '🌙'}
    </button>
  );
}

export default ThemeToggle;