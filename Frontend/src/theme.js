function initTheme() {
  // Check for saved theme preference or use system preference
  const savedTheme = localStorage.getItem('theme') || 
    (window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light');
  
  // Apply the theme
  document.documentElement.setAttribute('data-theme', savedTheme);
  
  // Create theme toggle button if it doesn't exist
  if (!document.querySelector('.theme-toggle')) {
    const themeToggle = document.createElement('button');
    themeToggle.className = 'theme-toggle';
    themeToggle.innerHTML = savedTheme === 'dark' ? '☀️' : '🌙';
    themeToggle.setAttribute('aria-label', 'Toggle dark mode');
    
    themeToggle.addEventListener('click', () => {
      // Get current theme and switch to opposite
      const currentTheme = document.documentElement.getAttribute('data-theme');
      const newTheme = currentTheme === 'dark' ? 'light' : 'dark';
      
      // Update theme
      document.documentElement.setAttribute('data-theme', newTheme);
      localStorage.setItem('theme', newTheme);
      
      // Update button icon
      themeToggle.innerHTML = newTheme === 'dark' ? '☀️' : '🌙';
    });
    
    document.body.appendChild(themeToggle);
  }
}

// Initialize theme when DOM is loaded
document.addEventListener('DOMContentLoaded', initTheme);

// Export for use in other components if needed
export { initTheme };