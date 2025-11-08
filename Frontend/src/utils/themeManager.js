/**
 * Theme Manager for Thoth Application
 * Handles dark mode toggling and persistence
 */

// Check if user prefers dark mode
const prefersDarkMode = () => {
  return window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches;
};

// Initialize theme based on localStorage or system preference
const initializeTheme = () => {
  // Check for saved theme preference or use system preference
  const savedTheme = localStorage.getItem('theme');
  
  if (savedTheme === 'dark' || (!savedTheme && prefersDarkMode())) {
    document.documentElement.classList.add('dark');
    return 'dark';
  } else {
    document.documentElement.classList.remove('dark');
    return 'light';
  }
};

// Toggle between light and dark mode
const toggleTheme = () => {
  if (document.documentElement.classList.contains('dark')) {
    document.documentElement.classList.remove('dark');
    localStorage.setItem('theme', 'light');
    return 'light';
  } else {
    document.documentElement.classList.add('dark');
    localStorage.setItem('theme', 'dark');
    return 'dark';
  }
};

// Get current theme
const getCurrentTheme = () => {
  return document.documentElement.classList.contains('dark') ? 'dark' : 'light';
};

// Set specific theme
const setTheme = (theme) => {
  if (theme === 'dark') {
    document.documentElement.classList.add('dark');
    localStorage.setItem('theme', 'dark');
  } else {
    document.documentElement.classList.remove('dark');
    localStorage.setItem('theme', 'light');
  }
  return theme;
};

// Listen for system theme changes
const setupThemeListener = (callback) => {
  if (window.matchMedia) {
    const colorSchemeQuery = window.matchMedia('(prefers-color-scheme: dark)');
    
    const handleChange = (e) => {
      const newTheme = e.matches ? 'dark' : 'light';
      // Only change if user hasn't set a preference
      if (!localStorage.getItem('theme')) {
        setTheme(newTheme);
        if (callback) callback(newTheme);
      }
    };
    
    // Modern browsers
    if (colorSchemeQuery.addEventListener) {
      colorSchemeQuery.addEventListener('change', handleChange);
    } 
    // Older browsers
    else if (colorSchemeQuery.addListener) {
      colorSchemeQuery.addListener(handleChange);
    }
  }
};

export {
  initializeTheme,
  toggleTheme,
  getCurrentTheme,
  setTheme,
  setupThemeListener
};