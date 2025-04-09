document.addEventListener('DOMContentLoaded', function() {
  // Initialize tooltips
  const tooltips = document.querySelectorAll('[data-bs-toggle="tooltip"]');
  if (tooltips.length > 0) {
    tooltips.forEach(tooltip => {
      new bootstrap.Tooltip(tooltip);
    });
  }

  // Auto-resize textarea
  const pasteTextarea = document.getElementById('content');
  if (pasteTextarea) {
    pasteTextarea.addEventListener('input', function() {
      this.style.height = 'auto';
      this.style.height = (this.scrollHeight) + 'px';
    });
    
    // Initial resize
    pasteTextarea.style.height = 'auto';
    pasteTextarea.style.height = (pasteTextarea.scrollHeight) + 'px';
  }

  // Copy to clipboard functionality
  const copyButtons = document.querySelectorAll('.btn-copy');
  if (copyButtons.length > 0) {
    copyButtons.forEach(button => {
      button.addEventListener('click', function() {
        const targetId = this.getAttribute('data-clipboard-target');
        const targetElement = document.querySelector(targetId);
        
        if (targetElement) {
          // Create a temporary textarea to copy from
          const textarea = document.createElement('textarea');
          textarea.value = targetElement.textContent;
          textarea.setAttribute('readonly', '');
          textarea.style.position = 'absolute';
          textarea.style.left = '-9999px';
          document.body.appendChild(textarea);
          
          // Select and copy
          textarea.select();
          document.execCommand('copy');
          
          // Clean up
          document.body.removeChild(textarea);
          
          // Update button text temporarily
          const originalText = this.textContent;
          this.textContent = 'Copied!';
          
          setTimeout(() => {
            this.textContent = originalText;
          }, 2000);
        }
      });
    });
  }

  // Confirmation dialogs
  const confirmButtons = document.querySelectorAll('[data-confirm]');
  if (confirmButtons.length > 0) {
    confirmButtons.forEach(button => {
      button.addEventListener('click', function(e) {
        const message = this.getAttribute('data-confirm');
        if (!confirm(message)) {
          e.preventDefault();
        }
      });
    });
  }

  // Paste expiration countdown
  const expirationElements = document.querySelectorAll('.expiration-countdown');
  if (expirationElements.length > 0) {
    expirationElements.forEach(element => {
      const expiresAt = new Date(element.getAttribute('data-expires-at')).getTime();
      
      if (expiresAt) {
        const updateCountdown = () => {
          const now = new Date().getTime();
          const distance = expiresAt - now;
          
          if (distance < 0) {
            element.textContent = 'Expired';
            return;
          }
          
          // Calculate days, hours, minutes, and seconds
          const days = Math.floor(distance / (1000 * 60 * 60 * 24));
          const hours = Math.floor((distance % (1000 * 60 * 60 * 24)) / (1000 * 60 * 60));
          const minutes = Math.floor((distance % (1000 * 60 * 60)) / (1000 * 60));
          const seconds = Math.floor((distance % (1000 * 60)) / 1000);
          
          // Format the countdown as "in Xd Yh Zm Ws" or appropriate variations
          let countdownText = 'in ';
          
          if (days > 0) {
            countdownText += `${days}d `;
          }
          
          if (hours > 0 || days > 0) {
            countdownText += `${hours}h `;
          }
          
          if (minutes > 0 || hours > 0 || days > 0) {
            countdownText += `${minutes}m `;
          }
          
          countdownText += `${seconds}s`;
          
          element.textContent = countdownText;
        };
        
        // Update immediately and then every second
        updateCountdown();
        setInterval(updateCountdown, 1000);
      }
    });
  }

  // Form validation
  const forms = document.querySelectorAll('.needs-validation');
  if (forms.length > 0) {
    forms.forEach(form => {
      form.addEventListener('submit', function(event) {
        if (!form.checkValidity()) {
          event.preventDefault();
          event.stopPropagation();
        }
        
        form.classList.add('was-validated');
      });
    });
  }
});
