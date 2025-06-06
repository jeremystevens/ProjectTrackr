"""
WSGI entry point for production deployment on Render.

This is a minimal WSGI entry point that avoids circular imports and
SQLAlchemy mapper conflicts.

To use this file with Gunicorn:
gunicorn --bind 0.0.0.0:$PORT wsgi:app
"""

import os
import logging
from datetime import datetime
import flask
from flask import Flask, render_template
from flask_login import LoginManager
from flask_wtf.csrf import CSRFProtect, CSRFError

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
logger.info("Starting WSGI app")

# Create Flask app
app = Flask(__name__)

# Configure app settings
app.secret_key = os.environ.get("SESSION_SECRET", "dev-secret-key")

# Set up Sentry for error tracking if configured
sentry_dsn = os.environ.get("SENTRY_DSN")
if sentry_dsn:
    try:
        import sentry_sdk
        from sentry_sdk.integrations.flask import FlaskIntegration
        
        sentry_sdk.init(
            dsn=sentry_dsn,
            integrations=[FlaskIntegration()],
            traces_sample_rate=0.1,
            send_default_pii=False,
            environment=os.environ.get("FLASK_ENV", "production")
        )
        logger.info("Sentry integration enabled")
    except ImportError:
        logger.warning("Sentry SDK not installed, error tracking disabled")

# Configure database - PostgreSQL only
db_url = os.environ.get("DATABASE_URL")
# Fix Heroku/Render style postgres:// URLs to postgresql://
if db_url and db_url.startswith('postgres://'):
    db_url = db_url.replace('postgres://', 'postgresql://', 1)
    logger.info("Fixed PostgreSQL URL format")

# Configure SQLAlchemy with PostgreSQL
app.config["SQLALCHEMY_DATABASE_URI"] = db_url
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
    "pool_recycle": 300,
    "pool_pre_ping": True,
}

# Initialize SQLAlchemy
from flask_sqlalchemy import SQLAlchemy
db = SQLAlchemy(app)

# Import models once
import models

# Set up login manager
login_manager = LoginManager(app)
login_manager.login_view = 'auth.login'
login_manager.login_message_category = 'info'

@login_manager.user_loader
def load_user(user_id):
    return db.session.get(models.User, int(user_id))

# Set up CSRF protection
csrf = CSRFProtect(app)

# Set up rate limiting
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
limiter = Limiter(
    get_remote_address,
    app=app,
    default_limits=["200 per day", "50 per hour"],
    storage_uri="memory://",
)

# Import and register blueprints
from routes.auth import auth_bp
from routes.paste import paste_bp
from routes.user import user_bp
from routes.search import search_bp
from routes.comment import comment_bp
from routes.notification import notification_bp
from routes.collection import collection_bp
from routes.admin import admin_bp
from routes.account import account_bp

app.register_blueprint(auth_bp, url_prefix='/auth')
app.register_blueprint(paste_bp)  # Root blueprint for pastes
app.register_blueprint(user_bp, url_prefix='/user')
app.register_blueprint(search_bp, url_prefix='/search')
app.register_blueprint(comment_bp, url_prefix='/comment')
app.register_blueprint(notification_bp, url_prefix='/notification')
app.register_blueprint(collection_bp, url_prefix='/collection')
app.register_blueprint(admin_bp, url_prefix='/admin')
app.register_blueprint(account_bp, url_prefix='/account')

# Error handlers
@app.errorhandler(404)
def not_found_error(error):
    return render_template('errors/404.html'), 404

@app.errorhandler(500)
def internal_server_error(error):
    error_id = f"ERR-{os.urandom(3).hex()}"
    return render_template('errors/500.html', error_id=error_id), 500

@app.errorhandler(CSRFError)
def handle_csrf_error(e):
    return render_template('errors/csrf_error.html'), 400

# Template helpers
@app.template_filter('timesince')
def timesince_filter(dt):
    """Format the datetime as a pretty relative time."""
    now = datetime.utcnow()
    diff = now - dt
    
    seconds = diff.total_seconds()
    if seconds < 60:
        return f"{int(seconds)} seconds ago"
    minutes = seconds // 60
    if minutes < 60:
        return f"{int(minutes)} minutes ago"
    hours = minutes // 60
    if hours < 24:
        return f"{int(hours)} hours ago"
    days = hours // 24
    if days < 30:
        return f"{int(days)} days ago"
    months = days // 30
    if months < 12:
        return f"{int(months)} months ago"
    years = months // 12
    return f"{int(years)} years ago"

@app.context_processor
def utility_processor():
    def is_ten_minute_expiration(paste):
        """Check if a paste has 10-minute expiration"""
        if hasattr(paste, 'short_id') and 'expires_in_10_minutes' in paste.short_id:
            return True
            
        if hasattr(paste, 'expires_at') and paste.expires_at and hasattr(paste, 'created_at'):
            diff = paste.expires_at - paste.created_at
            total_minutes = diff.total_seconds() / 60
            if 9 <= total_minutes <= 11:
                return True
                
        return False
    
    return {
        'now': datetime.utcnow(),
        'is_ten_minute_expiration': is_ten_minute_expiration
    }

logger.info("WSGI app initialization complete")