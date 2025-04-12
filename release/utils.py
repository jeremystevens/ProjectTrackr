import random
import string
import bleach
import uuid
import os
import base64
import logging
from datetime import datetime
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from flask import request, session, abort, current_app, g
from flask_login import current_user
from functools import wraps
from pygments import highlight
from pygments.lexers import get_lexer_by_name, get_all_lexers, guess_lexer
from pygments.formatters import HtmlFormatter
from pygments.util import ClassNotFound

# Import OpenAI for AI summary generation
import openai

def generate_short_id(length=8):
    """Generate a random alphanumeric ID of specified length"""
    chars = string.ascii_letters + string.digits
    return ''.join(random.choice(chars) for _ in range(length))

def sanitize_html(text):
    """Sanitize HTML to prevent XSS attacks"""
    allowed_tags = ['p', 'br', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 
                    'ul', 'ol', 'li', 'strong', 'em', 'b', 'i', 'pre', 
                    'code', 'blockquote', 'span']
    allowed_attrs = {'*': ['class']}
    return bleach.clean(text, tags=allowed_tags, attributes=allowed_attrs, strip=True)

# This function was duplicated in both utils.py and models.py (as a method)
# It was causing the "Expires: Expires:" issue, so we've removed it from utils.py
# Use paste.get_expiration_text() method from the Paste model instead

def highlight_code(code, syntax='text'):
    """Highlight code using Pygments"""
    try:
        lexer = get_lexer_by_name(syntax, stripall=True)
    except ClassNotFound:
        lexer = get_lexer_by_name('text', stripall=True)
    
    # Use a dark style (like 'monokai' or 'dracula') for better visibility with dark theme
    formatter = HtmlFormatter(linenos=True, cssclass='highlight', style='monokai')
    highlighted = highlight(code, lexer, formatter)
    css = HtmlFormatter(style='monokai').get_style_defs('.highlight')
    
    # Add additional styles for better readability
    css += "\n.highlight { background-color: #272822; border-radius: 4px; padding: 10px; }"
    css += "\n.highlight pre { background-color: #272822; color: #f8f8f2; }"
    css += "\n.highlight .linenos { color: #8f908a; }"
    
    return highlighted, css

def get_available_lexers():
    """Get all available syntax highlighting lexers"""
    return sorted([(lexer[1][0], lexer[0]) for lexer in get_all_lexers()])

def detect_language(code):
    """
    Detect the programming language of code using Pygments lexer guessing
    Returns the alias of the detected lexer (e.g., 'python', 'javascript', etc.)
    Falls back to 'text' if detection fails
    """
    import logging
    from flask import current_app
    
    try:
        # Ensure code is not empty to avoid errors
        if not code or code.strip() == '':
            logging.debug("Empty code, returning 'text'")
            return 'text'
            
        # Add detailed logging
        logging.debug(f"Attempting to detect language for code: {code[:100]}...")
        
        # Attempt to guess the lexer
        lexer = guess_lexer(code)
        
        # Get the aliases (short names) of the detected lexer
        aliases = lexer.aliases
        
        # Log lexer info for debugging
        logging.debug(f"Detected lexer: {lexer.name}")
        logging.debug(f"Lexer aliases: {aliases}")
        
        # Return the first alias, which is typically the most common one
        # (e.g., 'py' or 'python' for Python code)
        if aliases and len(aliases) > 0:
            logging.debug(f"Using alias: {aliases[0]}")
            return aliases[0]
        
        # If no aliases are found, return the lexer name
        logging.debug(f"No aliases found, using lexer name: {lexer.name.lower()}")
        return lexer.name.lower()
    except Exception as e:
        # Log the error and fall back to 'text'
        logging.error(f"Language detection failed: {str(e)}")
        current_app.logger.warning(f"Language detection failed: {str(e)}")
        return 'text'

def format_size(size_bytes):
    """Format bytes to human-readable format"""
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size_bytes < 1024 or unit == 'GB':
            return f"{size_bytes:.2f} {unit}" if unit != 'B' else f"{size_bytes} {unit}"
        size_bytes /= 1024

def get_client_ip():
    """Get the client's IP address from the request"""
    if request.environ.get('HTTP_X_FORWARDED_FOR'):
        # For requests going through a proxy
        ip = request.environ['HTTP_X_FORWARDED_FOR'].split(',')[0].strip()
    else:
        # Direct connection
        ip = request.remote_addr or '127.0.0.1'
    return ip

def get_viewer_id():
    """Get a unique identifier for the current viewer"""
    # Import PasteView inside the function to avoid circular imports
    from models import PasteView
    return PasteView.get_or_create_viewer_id(session, get_client_ip())
    
def encrypt_content(content, password=None):
    """
    Encrypt content using Fernet symmetric encryption
    
    Args:
        content (str): The content to encrypt
        password (str, optional): If provided, derives a key from the password
                                  If not, generates a random key
                                  
    Returns:
        tuple: (encrypted_content, salt, method)
               - encrypted_content: Base64 encoded encrypted bytes
               - salt: Base64 encoded salt (if password was used) or None
               - method: Either 'fernet-random' or 'fernet-password'
    """
    try:
        # Convert content to bytes if it's a string
        if isinstance(content, str):
            content_bytes = content.encode('utf-8')
        else:
            content_bytes = content
            
        if password:
            # Password-based encryption
            # Generate a random salt
            salt = os.urandom(16)
            
            # Derive a key from the password and salt
            kdf = PBKDF2HMAC(
                algorithm=hashes.SHA256(),
                length=32,
                salt=salt,
                iterations=100000,
            )
            key = base64.urlsafe_b64encode(kdf.derive(password.encode('utf-8')))
            
            # Create a Fernet cipher with the derived key
            cipher = Fernet(key)
            
            # Encrypt the content
            encrypted_content = cipher.encrypt(content_bytes)
            
            return (
                base64.urlsafe_b64encode(encrypted_content).decode('utf-8'),
                base64.urlsafe_b64encode(salt).decode('utf-8'),
                'fernet-password'
            )
        else:
            # Random key-based encryption
            # Generate a random key
            key = Fernet.generate_key()
            
            # Create a Fernet cipher with the random key
            cipher = Fernet(key)
            
            # Encrypt the content
            encrypted_content = cipher.encrypt(content_bytes)
            
            # Combine the key and encrypted content
            # This is necessary because we need the key to decrypt later
            combined = key + b"." + encrypted_content
            
            return (
                base64.urlsafe_b64encode(combined).decode('utf-8'),
                None,
                'fernet-random'
            )
    except Exception as e:
        current_app.logger.error(f"Encryption error: {str(e)}")
        return None, None, None
        
def decrypt_content(encrypted_content, salt=None, method='fernet-random', password=None):
    """
    Decrypt content that was encrypted using encrypt_content
    
    Args:
        encrypted_content (str): Base64 encoded encrypted content
        salt (str, optional): Base64 encoded salt (for password-based encryption)
        method (str): Either 'fernet-random' or 'fernet-password'
        password (str, optional): The password to use for decryption (for password-based)
        
    Returns:
        str: The decrypted content or None if decryption fails
    """
    try:
        # Decode the base64 encoded encrypted content
        encrypted_bytes = base64.urlsafe_b64decode(encrypted_content.encode('utf-8'))
        
        if method == 'fernet-password':
            if not password or not salt:
                current_app.logger.error("Password and salt required for password-based decryption")
                return None
                
            # Decode the salt
            salt_bytes = base64.urlsafe_b64decode(salt.encode('utf-8'))
            
            # Derive the key from the password and salt
            kdf = PBKDF2HMAC(
                algorithm=hashes.SHA256(),
                length=32,
                salt=salt_bytes,
                iterations=100000,
            )
            key = base64.urlsafe_b64encode(kdf.derive(password.encode('utf-8')))
            
            # Create a Fernet cipher with the derived key
            cipher = Fernet(key)
            
            # Decrypt the content
            decrypted_bytes = cipher.decrypt(encrypted_bytes)
            
        elif method == 'fernet-random':
            # Split the combined key and encrypted content
            parts = encrypted_bytes.split(b".", 1)
            if len(parts) != 2:
                current_app.logger.error("Invalid format for random key encryption")
                return None
                
            key, actual_encrypted = parts
            
            # Create a Fernet cipher with the extracted key
            cipher = Fernet(key)
            
            # Decrypt the content
            decrypted_bytes = cipher.decrypt(actual_encrypted)
            
        else:
            current_app.logger.error(f"Unsupported encryption method: {method}")
            return None
            
        # Convert bytes back to string
        return decrypted_bytes.decode('utf-8')
        
    except Exception as e:
        current_app.logger.error(f"Decryption error: {str(e)}")
        return None

def generate_ai_summary(code, language=None, max_tokens=150):
    """
    Generate an AI summary of code using OpenAI's GPT models
    
    Args:
        code (str): The source code to summarize
        language (str, optional): The programming language of the code
        max_tokens (int): Maximum tokens for the response
        
    Returns:
        str or None: AI-generated summary or None if generation fails
    """
    try:
        # Set up OpenAI API key from environment
        api_key = os.environ.get('OPENAI_API_KEY')
        if not api_key:
            current_app.logger.error("Missing OpenAI API key in environment")
            return None
            
        openai.api_key = api_key
        
        # Truncate code if it's too long to avoid excessive token usage
        max_code_chars = 8000  # Approximate limit to avoid hitting token limits
        truncated = False
        
        if len(code) > max_code_chars:
            code = code[:max_code_chars] + "...[truncated]"
            truncated = True
        
        # Language-specific prompt template
        language_text = f"in {language}" if language else ""
        prompt_addition = " The code has been truncated." if truncated else ""
        
        messages = [
            {"role": "system", "content": "You are an expert programmer who provides concise, accurate summaries of code."},
            {"role": "user", "content": f"Please analyze this code {language_text} and provide a brief, clear summary explaining what it does. Focus on the main functionality, key components, and overall purpose. Be objective and technical but easy to understand.{prompt_addition}\n\nCode:\n```\n{code}\n```"}
        ]
        
        # Start timing for performance monitoring
        start_time = datetime.now()
        
        # Make the API call to OpenAI
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",  # Use appropriate model based on your needs
            messages=messages,
            max_tokens=max_tokens,
            temperature=0.5,  # Lower temperature for more focused responses
            n=1,
            stop=None
        )
        
        # End timing
        duration = (datetime.now() - start_time).total_seconds()
        
        # Extract the summary from the response
        summary = response.choices[0].message.content.strip()
        
        # Log metrics for monitoring
        current_app.logger.info(f"AI summary generated in {duration:.2f}s, input: {len(code)} chars, output: {len(summary)} chars")
        
        return summary
    
    except Exception as e:
        current_app.logger.error(f"Error generating AI summary: {str(e)}")
        return None


def check_shadowban(func):
    """
    Decorator to check if the current user is shadowbanned.
    If they are, their actions will only be visible to themselves and admins.
    This decorator sets a flag in flask.g that can be checked in templates and views.
    
    Usage:
        @check_shadowban
        @route_bp.route('/some-route', methods=['POST'])
        def some_function():
            # g.is_shadowbanned will be True if the user is shadowbanned
            # Can use g.is_shadowbanned in templates and views to conditionally show content
            pass
    """
    @wraps(func)
    def decorated_function(*args, **kwargs):
        # Set default value
        g.is_shadowbanned = False
        
        # Check if user is logged in and shadowbanned
        if current_user.is_authenticated and hasattr(current_user, 'is_shadowbanned'):
            if current_user.is_shadowbanned:
                g.is_shadowbanned = True
                current_app.logger.info(f"Shadowbanned user {current_user.id} accessed {request.path}")
        
        # Always proceed, since shadowbanned users can still use the site
        return func(*args, **kwargs)
    
    return decorated_function
