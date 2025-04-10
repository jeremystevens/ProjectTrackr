/**
 * Theme Switcher for FlaskBin
 * Manages dark/light theme preferences and toggle functionality
 */
document.addEventListener('DOMContentLoaded', function() {
  console.log("Theme switcher initialized");
  
  // Get DOM elements
  const themeToggleBtn = document.getElementById('theme-toggle');
  const themeIcon = document.getElementById('theme-icon');
  
  if (!themeToggleBtn || !themeIcon) {
    console.error("Theme toggle elements not found");
    return;
  }
  
  console.log("Theme toggle elements found");
  
  // Function to set theme
  function setTheme(isDark) {
    // Update HTML element
    document.documentElement.setAttribute('data-bs-theme', isDark ? 'dark' : 'light');
    
    // Update icon
    themeIcon.className = isDark ? 'fas fa-sun' : 'fas fa-moon';
    
    // Update highlight.js theme
    const highlightTheme = isDark ? 'atom-one-dark' : 'atom-one-light';
    const stylesheets = document.querySelectorAll('link');
    for (let i = 0; i < stylesheets.length; i++) {
      const href = stylesheets[i].getAttribute('href');
      if (href && href.includes('highlight.js')) {
        const newHref = href.replace(/\/styles\/.*\.min\.css/, `/styles/${highlightTheme}.min.css`);
        stylesheets[i].setAttribute('href', newHref);
        console.log(`Updated syntax theme to ${highlightTheme}`);
        break;
      }
    }
    
    // Save preference
    localStorage.setItem('theme', isDark ? 'dark' : 'light');
    console.log(`Theme set to ${isDark ? 'dark' : 'light'}`);
  }
  
  // Set up click handler
  themeToggleBtn.addEventListener('click', function() {
    console.log("Theme toggle button clicked");
    const currentTheme = document.documentElement.getAttribute('data-bs-theme');
    setTheme(currentTheme !== 'dark'); // Toggle
  });
  
  // Initialize theme from localStorage or default to dark
  const savedTheme = localStorage.getItem('theme');
  if (savedTheme) {
    setTheme(savedTheme === 'dark');
  } else {
    // Default to system preference, fallback to dark
    const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
    setTheme(prefersDark);
  }
});
