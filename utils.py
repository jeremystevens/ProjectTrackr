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
    
    diff = expires_at - now
    days = diff.days
    hours, remainder = divmod(diff.seconds, 3600)
    minutes, _ = divmod(remainder, 60)
    
    if days > 30:
        months = days // 30
        return f"Expires in {months} month{'s' if months > 1 else ''}"
    elif days > 0:
        return f"Expires in {days} day{'s' if days > 1 else ''}"
    elif hours > 0:
        return f"Expires in {hours} hour{'s' if hours > 1 else ''}"
    else:
        return f"Expires in {minutes} minute{'s' if minutes > 1 else ''}"

def highlight_code(code, syntax='text'):
    """Highlight code using Pygments"""
    try:
        lexer = get_lexer_by_name(syntax, stripall=True)
    except ClassNotFound:
        lexer = get_lexer_by_name('text', stripall=True)
    
    formatter = HtmlFormatter(linenos=True, cssclass='highlight')
    highlighted = highlight(code, lexer, formatter)
    css = HtmlFormatter().get_style_defs('.highlight')
    
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
