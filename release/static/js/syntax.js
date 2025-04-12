document.addEventListener('DOMContentLoaded', function() {
  // Initialize highlight.js for client-side syntax highlighting
  if (typeof hljs !== 'undefined') {
    hljs.highlightAll();
  }
  
  // Handle syntax selection in the paste form
  const syntaxSelect = document.getElementById('syntax');
  const previewContainer = document.getElementById('syntax-preview');
  const content = document.getElementById('content');
  
  if (syntaxSelect && previewContainer && content) {
    syntaxSelect.addEventListener('change', function() {
      updateSyntaxPreview();
    });
    
    content.addEventListener('input', function() {
      updateSyntaxPreview();
    });
    
    // Initial preview update
    updateSyntaxPreview();
  }
  
  function updateSyntaxPreview() {
    if (!content.value.trim()) {
      previewContainer.innerHTML = '<div class="text-muted">Enter some code to see syntax highlighting preview</div>';
      return;
    }
    
    const syntax = syntaxSelect.value;
    const previewContent = content.value.substring(0, 500); // Preview first 500 chars
    
    // Show loading indicator
    previewContainer.innerHTML = '<div class="text-muted">Loading preview...</div>';
    
    // Use server-side Pygments highlighting via the API
    fetch('/api/highlight', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/x-www-form-urlencoded',
        'X-CSRFToken': getCsrfToken()
      },
      body: new URLSearchParams({
        'content': previewContent,
        'syntax': syntax
      })
    })
    .then(response => response.json())
    .then(data => {
      // Clear previous content
      previewContainer.innerHTML = '';
      
      // Add the highlighted HTML and CSS
      if (data.css) {
        // Add the CSS if not already present
        if (!document.getElementById('pygments-css')) {
          const style = document.createElement('style');
          style.id = 'pygments-css';
          style.textContent = data.css;
          document.head.appendChild(style);
        }
      }
      
      // Add the highlighted HTML
      const preElement = document.createElement('div');
      preElement.className = 'syntax-preview-content';
      preElement.innerHTML = data.highlighted;
      
      if (content.value.length > 500) {
        const ellipsis = document.createElement('div');
        ellipsis.className = 'text-muted';
        ellipsis.textContent = '... (preview truncated)';
        preElement.appendChild(ellipsis);
      }
      
      previewContainer.appendChild(preElement);
    })
    .catch(error => {
      console.error('Error fetching syntax highlight preview:', error);
      previewContainer.innerHTML = '<div class="alert alert-danger">Error loading preview</div>';
    });
  }
  
  // Helper function to get CSRF token
  function getCsrfToken() {
    return document.querySelector('meta[name="csrf-token"]')?.getAttribute('content') || '';
  }
  
  // Line numbers for code blocks
  const codeBlocks = document.querySelectorAll('pre code');
  if (codeBlocks.length > 0) {
    codeBlocks.forEach(block => {
      if (!block.classList.contains('line-numbers-added')) {
        const lines = block.innerHTML.split('\n').length;
        let lineNumbers = '';
        
        for (let i = 1; i < lines; i++) {
          lineNumbers += `<span class="line-number">${i}</span>\n`;
        }
        
        const lineNumbersWrapper = document.createElement('div');
        lineNumbersWrapper.className = 'line-numbers-wrapper';
        lineNumbersWrapper.innerHTML = lineNumbers;
        
        const pre = block.parentNode;
        pre.classList.add('has-line-numbers');
        pre.insertBefore(lineNumbersWrapper, block);
        
        block.classList.add('line-numbers-added');
      }
    });
  }
});
