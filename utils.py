import random
import string
import bleach
import uuid
from datetime import datetime
from flask import request, session, abort, current_app, g
from flask_login import current_user
from functools import wraps
from pygments import highlight
from pygments.lexers import get_lexer_by_name, get_all_lexers, guess_lexer
from pygments.formatters import HtmlFormatter
from pygments.util import ClassNotFound

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
    from models import PasteView
    return PasteView.get_or_create_viewer_id(session, get_client_ip())
    
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
