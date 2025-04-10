/**
 * Theme Switcher for FlaskBin
 * Manages dark/light theme preferences and toggle functionality
 */
document.addEventListener('DOMContentLoaded', function() {
  console.log("Theme switcher loading...");
  
  // Theme toggle button
  const themeToggleBtn = document.getElementById('theme-toggle');
  const themeIcon = document.getElementById('theme-icon');
  
  if (!themeToggleBtn || !themeIcon) {
    console.error("Theme toggle elements not found in the DOM");
    return;
  }
  
  console.log("Theme toggle elements found in the DOM");
  
  // Apply the given theme
  function applyTheme(theme) {
    console.log(`Applying theme: ${theme}`);
    
    // Set the data attribute on the html element
    document.documentElement.setAttribute('data-bs-theme', theme);
    
    // Update the icon
    if (themeIcon) {
      themeIcon.className = theme === 'dark' ? 'fas fa-sun' : 'fas fa-moon';
    }
    
    // Store the preference
    localStorage.setItem('flaskbin-theme', theme);
    
    console.log(`Theme applied: ${theme}`);
    
    // Force redraw of the page (helps with some browsers)
    document.body.style.display = 'none';
    setTimeout(() => {
      document.body.style.display = '';
    }, 5);
  }
  
  // Toggle the current theme
  function toggleTheme() {
    console.log("Toggle theme function called");
    const currentTheme = document.documentElement.getAttribute('data-bs-theme') || 'dark';
    const newTheme = currentTheme === 'dark' ? 'light' : 'dark';
    console.log(`Toggling from ${currentTheme} to ${newTheme}`);
    applyTheme(newTheme);
  }
  
  // Set up the click handler
  themeToggleBtn.addEventListener('click', function(e) {
    console.log("Theme toggle button clicked");
    e.preventDefault();
    toggleTheme();
  });
  
  // Initialize theme from local storage or default to dark
  const storedTheme = localStorage.getItem('flaskbin-theme');
  console.log(`Retrieved stored theme: ${storedTheme}`);
  
  if (storedTheme) {
    applyTheme(storedTheme);
  } else {
    // Default to dark theme if no preference is stored
    applyTheme('dark');
  }
  
  console.log("Theme switcher initialization complete");
});
