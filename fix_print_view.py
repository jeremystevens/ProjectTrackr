#!/usr/bin/env python3
import re

# Path to the paste.py file
file_path = 'routes/paste.py'

# Read the file content
with open(file_path, 'r') as f:
    content = f.read()

# Define the pattern to find the print_view function's encryption handling
print_view_pattern = r"""    # Handle encrypted content
    content = paste.content
    if paste.is_encrypted:
        # If password protected and not already decrypted in this session, redirect to the standard view
        if paste.password_protected and not session.get\('decrypted_pastes', {}\).get\(paste.short_id\):
            flash\('This paste is password protected. Please enter the password to view.', 'warning'\)
            return redirect\(url_for\('paste.view', short_id=paste.short_id\)\)
            
        # If we've already decrypted this paste or it's not password protected
        decrypted_content = paste.get_content\(\)
        if decrypted_content:
            content = decrypted_content"""

# Define the replacement for the print_view function
print_view_replacement = """    # Handle encrypted content
    content = paste.content
    
    # Add debug logging
    import logging
    logging.debug(f"PRINT: Handling encrypted paste: {paste.short_id}, Encrypted: {paste.is_encrypted}, Method: {paste.encryption_method}")
    
    if paste.is_encrypted:
        # If password protected and not already decrypted in this session, redirect to the standard view
        if paste.password_protected and not session.get('decrypted_pastes', {}).get(paste.short_id):
            flash('This paste is password protected. Please enter the password to view.', 'warning')
            return redirect(url_for('paste.view', short_id=paste.short_id))
        
        # For random key encryption, check if we need to get the key from URL
        if paste.encryption_method == 'fernet-random' and not session.get('decrypted_pastes', {}).get(paste.short_id):
            # Get key from URL for random key encryption
            key = request.args.get('key')
            logging.debug(f"PRINT: Random key from URL: {key}")
            
            if not key:
                # No key provided, redirect to the standard view which will handle the error
                flash('This paste requires an encryption key that was not provided in the URL.', 'danger')
                return redirect(url_for('paste.view', short_id=paste.short_id))
            
            # Use the key from the URL
            paste.encryption_salt = key
            logging.debug(f"PRINT: Using key from URL for paste {short_id}")
        
        # Try to decrypt with the key or from session
        decrypted_content = paste.get_content()
        if decrypted_content:
            content = decrypted_content
            # Store in session for future reference if not already stored
            if not session.get('decrypted_pastes', {}).get(paste.short_id):
                session_decrypted = session.get('decrypted_pastes', {})
                session_decrypted[paste.short_id] = True
                session['decrypted_pastes'] = session_decrypted
        else:
            logging.error(f"PRINT: Failed to decrypt paste {short_id}")
            flash('Failed to decrypt paste. The encryption key may be invalid.', 'danger')
            return redirect(url_for('paste.view', short_id=paste.short_id))"""

# Use regex to search for the print_view function's encryption handling 
match = re.search(print_view_pattern, content, re.DOTALL)

if match:
    print("Found print_view encryption handling")
    # Replace the old code with the new one
    new_content = content.replace(match.group(0), print_view_replacement)
    
    # Write the updated content back to the file
    with open(file_path, 'w') as f:
        f.write(new_content)
    
    print("Successfully updated print_view function")
else:
    print("Could not find print_view encryption handling")