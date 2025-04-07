import random
import string
import bleach
from datetime import datetime
from pygments import highlight
from pygments.lexers import get_lexer_by_name, get_all_lexers
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

def format_size(size_bytes):
    """Format bytes to human-readable format"""
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size_bytes < 1024 or unit == 'GB':
            return f"{size_bytes:.2f} {unit}" if unit != 'B' else f"{size_bytes} {unit}"
        size_bytes /= 1024
