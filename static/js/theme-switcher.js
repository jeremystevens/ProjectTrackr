document.addEventListener('DOMContentLoaded', function() {
  console.log("Theme switcher initialized");
  
  const themeToggle = document.getElementById('theme-toggle');
  const themeIcon = document.getElementById('theme-icon');
  
  if (!themeToggle || !themeIcon) {
    console.error("Theme toggle elements not found");
    return;
  }
  
  console.log("Theme toggle elements found");
  
  // Function to switch between dark and light themes
  function toggleTheme() {
    console.log("Toggle theme called");
    
    // Get current theme
    const currentTheme = document.documentElement.getAttribute('data-bs-theme');
    const newTheme = currentTheme === 'dark' ? 'light' : 'dark';
    
    console.log(`Switching from ${currentTheme} to ${newTheme}`);
    
    // Update the theme
    document.documentElement.setAttribute('data-bs-theme', newTheme);
    
    // Update icon
    themeIcon.className = newTheme === 'dark' ? 'fas fa-sun' : 'fas fa-moon';
    
    // Store preference in localStorage
    localStorage.setItem('flaskbin-theme', newTheme);
    
    // Update syntax highlighting theme if on a page with code
    const syntaxStyle = document.querySelector('link[href*="highlight.js"]');
    if (syntaxStyle) {
      const theme = newTheme === 'dark' ? 'atom-one-dark' : 'atom-one-light';
      syntaxStyle.href = `https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.7.0/styles/${theme}.min.css`;
      console.log(`Updated syntax theme to ${theme}`);
    }
  }
  
  // Add click event listener
  themeToggle.addEventListener('click', function(e) {
    console.log("Theme toggle clicked");
    e.preventDefault();
    toggleTheme();
  });
  
  // Initialize theme based on localStorage or default to dark
  const savedTheme = localStorage.getItem('flaskbin-theme');
  console.log(`Saved theme: ${savedTheme}`);
  
  if (savedTheme) {
    // Use saved preference
    document.documentElement.setAttribute('data-bs-theme', savedTheme);
    themeIcon.className = savedTheme === 'dark' ? 'fas fa-sun' : 'fas fa-moon';
    console.log(`Applied saved theme: ${savedTheme}`);
  }
});
