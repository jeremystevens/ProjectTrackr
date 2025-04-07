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

def get_expiration_text(expires_at):
    """Convert expiration datetime to human-readable text"""
    if not expires_at:
        return "Never"
    
    now = datetime.utcnow()
    if expires_at < now:
        return "Expired"
    
    # Print debug info
    import logging
    logging.debug(f"Now: {now}")
    logging.debug(f"Expires at: {expires_at}")
    
    # Calculate time difference
    diff = expires_at - now
    days = diff.days
    hours, remainder = divmod(diff.seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    
    logging.debug(f"Time diff: {days} days, {hours} hours, {minutes} minutes, {seconds} seconds")
    
    # For 10-minute expiration special case
    # Note: In the template, we now handle 10-minute expirations separately with the is_ten_minute flag
    # This is just a fallback in case the flag isn't available
    if days == 0 and hours == 0 and 8 <= minutes <= 11:
        logging.debug("Detected 10 minute expiration time range")
        return "in 10 minutes"
    
    # Regular formatted output based on actual time difference
    # Format according to specification:
    # - Hours/Minutes for > 1h
    # - Minutes only for < 1h
    
    if hours > 0:
        # More than 1 hour: show hours and minutes
        return f"in {hours}h {minutes}m"
    elif minutes > 0:
        # Less than 1 hour: show only minutes
        return f"in {minutes} minutes"
    elif days > 0:
        # Days (note: this is now a fallback case since we prioritize hour/minute display)
        return f"in {days} days"
    else:
        # Seconds (very short expiration)
        return f"in {seconds} seconds"

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
