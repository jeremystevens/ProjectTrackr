#!/usr/bin/env python3
import re

# Path to the paste.py file
file_path = 'routes/paste.py'

# Read the file content
with open(file_path, 'r') as f:
    content = f.read()

# Define the pattern for the embed route's encryption handling
pattern = r'(\s+# Handle encrypted content\n\s+content = paste\.content\n\s+if paste\.is_encrypted:.*?\n\s+# If password protected.*?\n\s+if paste\.password_protected.*?\n\s+.*?\n\s+return redirect.*?\n\s+\n\s+# If we\'ve already decrypted.*?\n\s+decrypted_content = paste\.get_content\(\)\n\s+if decrypted_content:\n\s+content = decrypted_content)'

# Define the replacement for the embed route
replacement = """    # Handle encrypted content
    content = paste.content
    
    # Add debug logging
    import logging
    logging.debug(f"EMBED: Handling encrypted paste: {paste.short_id}, Encrypted: {paste.is_encrypted}, Method: {paste.encryption_method}")
    
    if paste.is_encrypted:
        # If password protected and not already decrypted in this session, redirect to the standard view
        if paste.password_protected and not session.get('decrypted_pastes', {}).get(paste.short_id):
            flash('This paste is password protected. Please enter the password to view.', 'warning')
            return redirect(url_for('paste.view', short_id=paste.short_id))
        
        # For random key encryption, check if we need to get the key from URL
        if paste.encryption_method == 'fernet-random' and not session.get('decrypted_pastes', {}).get(paste.short_id):
            # Get key from URL for random key encryption
            key = request.args.get('key')
            logging.debug(f"EMBED: Random key from URL: {key}")
            
            if not key:
                # No key provided, redirect to the standard view which will handle the error
                flash('This paste requires an encryption key that was not provided in the URL.', 'danger')
                return redirect(url_for('paste.view', short_id=paste.short_id))
            
            # Use the key from the URL
            paste.encryption_salt = key
            logging.debug(f"EMBED: Using key from URL for paste {short_id}")
        
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
            logging.error(f"EMBED: Failed to decrypt paste {short_id}")
            flash('Failed to decrypt paste. The encryption key may be invalid.', 'danger')
            return redirect(url_for('paste.view', short_id=paste.short_id))"""

# Find all matches of the pattern in the content - there should be multiple spots for encryption handling
matches = list(re.finditer(pattern, content, re.DOTALL))

# If we found at least one match
if matches:
    print(f"Found {len(matches)} matches")
    
    # We want to replace the third occurrence (embed route)
    if len(matches) >= 3:
        match = matches[2]
        # Replace the matched content with our new content
        content = content[:match.start()] + replacement + content[match.end():]
        
        # Write the updated content back to the file
        with open(file_path, 'w') as f:
            f.write(content)
        
        print("Successfully updated embed route")
    else:
        print("Not enough matches found")
else:
    print("No matches found")