/**
 * Password strength meter
 * Used for registration and password reset forms
 */

document.addEventListener('DOMContentLoaded', function() {
    // Get password inputs and strength meter elements
    const passwordField = document.getElementById('password');
    const strengthMeter = document.getElementById('password-strength-meter');
    const strengthText = document.getElementById('password-strength-text');
    
    // If we're on a page with these elements
    if (passwordField && strengthMeter && strengthText) {
        // Listen for input changes
        passwordField.addEventListener('input', updateStrength);
        
        // Initial update
        updateStrength();
    }
    
    function updateStrength() {
        const password = passwordField.value;
        let strength = 0;
        let feedback = '';
        
        if (password.length === 0) {
            // Empty password
            strengthMeter.value = 0;
            strengthMeter.classList.remove('bg-danger', 'bg-warning', 'bg-info', 'bg-success');
            strengthText.textContent = '';
            return;
        }
        
        // Length check
        if (password.length >= 8) {
            strength += 1;
        } else {
            feedback = 'Password must be at least 8 characters';
        }
        
        // Contains number
        if (/\d/.test(password)) {
            strength += 1;
        } else {
            feedback = feedback || 'Add numbers';
        }
        
        // Contains uppercase
        if (/[A-Z]/.test(password)) {
            strength += 1;
        } else {
            feedback = feedback || 'Add uppercase letters';
        }
        
        // Contains special character
        if (/[!@#$%^&*(),.?":{}|<>]/.test(password)) {
            strength += 1;
        } else {
            feedback = feedback || 'Add special characters';
        }
        
        // Update meter and text
        strengthMeter.value = strength;
        
        // Remove all classes first
        strengthMeter.classList.remove('bg-danger', 'bg-warning', 'bg-info', 'bg-success');
        
        // Add class based on strength
        if (strength === 0) {
            strengthMeter.classList.add('bg-danger');
            strengthText.textContent = 'Very Weak: ' + feedback;
        } else if (strength === 1) {
            strengthMeter.classList.add('bg-danger');
            strengthText.textContent = 'Weak: ' + feedback;
        } else if (strength === 2) {
            strengthMeter.classList.add('bg-warning');
            strengthText.textContent = 'Fair: ' + feedback;
        } else if (strength === 3) {
            strengthMeter.classList.add('bg-info');
            strengthText.textContent = 'Good: ' + feedback;
        } else {
            strengthMeter.classList.add('bg-success');
            strengthText.textContent = 'Strong';
        }
    }
});
