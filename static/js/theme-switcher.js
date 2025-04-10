/**
 * Theme Switcher for FlaskBin
 * Manages dark/light theme preferences and toggle functionality
 */
document.addEventListener('DOMContentLoaded', function() {
  const themeToggleBtn = document.getElementById('theme-toggle');
  const themeIcon = document.getElementById('theme-icon');
  const htmlElement = document.documentElement;
  
  // Function to update theme icons
  function updateThemeIcon(isDarkTheme) {
    // Show sun icon if dark theme, moon icon if light theme
    themeIcon.className = isDarkTheme ? 'fas fa-sun' : 'fas fa-moon';
  }
  
  // Function to set theme
  function setTheme(theme) {
    const isDarkTheme = theme === 'dark';
    
    // Set data-bs-theme attribute on html element
    htmlElement.setAttribute('data-bs-theme', theme);
    
    // Update theme icons
    updateThemeIcon(isDarkTheme);
    
    // Set syntax highlighting theme - light or dark version
    const syntaxTheme = isDarkTheme ? 'atom-one-dark' : 'atom-one-light';
    
    // Store the theme preference in localStorage
    localStorage.setItem('flaskbin-theme', theme);
    
    // Find and change the syntax highlighting stylesheet
    const syntaxStylesheet = document.querySelector('link[href*="highlight.js"]');
    if (syntaxStylesheet) {
      syntaxStylesheet.href = `https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.7.0/styles/${syntaxTheme}.min.css`;
    }
    
    // If we have any code blocks with highlight.js, re-highlight them
    if (window.hljs) {
      document.querySelectorAll('pre code').forEach((block) => {
        hljs.highlightElement(block);
      });
    }
  }
  
  // Function to toggle theme
  function toggleTheme() {
    const currentTheme = htmlElement.getAttribute('data-bs-theme');
    const newTheme = currentTheme === 'dark' ? 'light' : 'dark';
    setTheme(newTheme);
  }
  
  // Initialize theme based on localStorage or system preference
  function initTheme() {
    // Check if user has previously selected a theme
    const savedTheme = localStorage.getItem('flaskbin-theme');
    
    if (savedTheme) {
      // Use saved theme preference
      setTheme(savedTheme);
    } else {
      // Check system preference for dark mode
      const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
      setTheme(prefersDark ? 'dark' : 'light');
    }
  }
  
  // Set up event listener for theme toggle button
  if (themeToggleBtn) {
    themeToggleBtn.addEventListener('click', toggleTheme);
  }
  
  // Initialize theme on page load
  initTheme();
  
  // Listen for system theme changes
  window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', e => {
    // Only update if user hasn't manually set a preference
    if (!localStorage.getItem('flaskbin-theme')) {
      setTheme(e.matches ? 'dark' : 'light');
    }
  });
});
