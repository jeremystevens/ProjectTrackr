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
    const preElement = document.createElement('pre');
    const codeElement = document.createElement('code');
    
    if (syntax !== 'text') {
      codeElement.className = `language-${syntax}`;
    }
    
    // Escape HTML in content
    codeElement.textContent = content.value.substring(0, 200); // Preview first 200 chars
    
    if (content.value.length > 200) {
      codeElement.textContent += '...';
    }
    
    preElement.appendChild(codeElement);
    
    // Clear previous content and add new preview
    previewContainer.innerHTML = '';
    previewContainer.appendChild(preElement);
    
    // Apply highlighting
    if (typeof hljs !== 'undefined') {
      hljs.highlightElement(codeElement);
    }
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
