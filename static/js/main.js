// FlaskBin main JavaScript

document.addEventListener('DOMContentLoaded', function() {
    // Initialize syntax highlighting if Highlight.js is loaded
    if (typeof hljs !== 'undefined') {
        document.querySelectorAll('pre code').forEach((block) => {
            hljs.highlightElement(block);
        });
    }
    
    // Initialize copy to clipboard buttons
    const copyButtons = document.querySelectorAll('.btn-copy');
    if (copyButtons.length > 0) {
        copyButtons.forEach(button => {
            button.addEventListener('click', function() {
                const codeBlock = this.closest('.pre-container').querySelector('code');
                
                // Create a temporary textarea element to copy from
                const textarea = document.createElement('textarea');
                textarea.value = codeBlock.textContent;
                textarea.style.position = 'fixed';  // Avoid scrolling to bottom
                document.body.appendChild(textarea);
                textarea.select();
                
                try {
                    // Execute copy command
                    document.execCommand('copy');
                    
                    // Provide visual feedback
                    const originalText = this.innerHTML;
                    this.innerHTML = '<i class="fas fa-check"></i> Copied!';
                    this.classList.add('text-success');
                    
                    // Reset after a short delay
                    setTimeout(() => {
                        this.innerHTML = originalText;
                        this.classList.remove('text-success');
                    }, 2000);
                } catch (err) {
                    console.error('Failed to copy text: ', err);
                }
                
                document.body.removeChild(textarea);
            });
        });
    }
    
    // Initialize paste expiration countdown
    const expirationElement = document.getElementById('expiration-countdown');
    if (expirationElement && expirationElement.dataset.expires) {
        updateExpirationCountdown();
        setInterval(updateExpirationCountdown, 1000);
    }
    
    // Form validation
    const newPasteForm = document.getElementById('new-paste-form');
    if (newPasteForm) {
        newPasteForm.addEventListener('submit', function(event) {
            const contentField = document.getElementById('content');
            if (!contentField.value.trim()) {
                event.preventDefault();
                alert('Please enter paste content');
                contentField.focus();
            }
        });
    }
});

// Helper function to update expiration countdown
function updateExpirationCountdown() {
    const expirationElement = document.getElementById('expiration-countdown');
    if (!expirationElement || !expirationElement.dataset.expires) return;
    
    const expiresAt = new Date(expirationElement.dataset.expires).getTime();
    const now = new Date().getTime();
    const distance = expiresAt - now;
    
    if (distance <= 0) {
        expirationElement.innerHTML = '<span class="text-danger">Expired</span>';
        return;
    }
    
    // Calculate time components
    const days = Math.floor(distance / (1000 * 60 * 60 * 24));
    const hours = Math.floor((distance % (1000 * 60 * 60 * 24)) / (1000 * 60 * 60));
    const minutes = Math.floor((distance % (1000 * 60 * 60)) / (1000 * 60));
    const seconds = Math.floor((distance % (1000 * 60)) / 1000);
    
    let countdown = '';
    if (days > 0) countdown += `${days}d `;
    if (hours > 0 || days > 0) countdown += `${hours}h `;
    if (minutes > 0 || hours > 0 || days > 0) countdown += `${minutes}m `;
    countdown += `${seconds}s`;
    
    expirationElement.textContent = countdown;
}

// Function to handle dark mode toggle
function toggleDarkMode() {
    document.body.classList.toggle('dark-mode');
    const isDarkMode = document.body.classList.contains('dark-mode');
    
    // Save preference to localStorage
    localStorage.setItem('darkMode', isDarkMode);
    
    // Update toggle button icon
    const toggleIcon = document.querySelector('.dark-mode-toggle i');
    if (toggleIcon) {
        toggleIcon.className = isDarkMode ? 'fas fa-sun' : 'fas fa-moon';
    }
}

// Check for saved dark mode preference
if (localStorage.getItem('darkMode') === 'true') {
    document.body.classList.add('dark-mode');
    const toggleIcon = document.querySelector('.dark-mode-toggle i');
    if (toggleIcon) {
        toggleIcon.className = 'fas fa-sun';
    }
}
