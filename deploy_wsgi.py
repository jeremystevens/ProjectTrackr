"""
Minimal WSGI entry point for production deployment on Render.

This file is designed to be as simple as possible to avoid SQLAlchemy
mapper conflicts that occur in more complex app structures.
It does not use the application factory pattern or any complex imports.

To use this file:
gunicorn --bind 0.0.0.0:$PORT deploy_wsgi:app
"""
import os
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
logger.info("Starting deployment WSGI app")

# Import Flask and extensions
from flask import Flask, render_template, request
from flask_login import LoginManager
from flask_wtf.csrf import CSRFProtect, CSRFError
from sqlalchemy.exc import SQLAlchemyError
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

# Create Flask app instance
app = Flask(__name__)

# Configure app - essential settings
app.secret_key = os.environ.get("SESSION_SECRET", "dev-secret-key")

# Configure database
# On Render, the database URL is provided as DATABASE_URL
db_url = os.environ.get("DATABASE_URL")
if not db_url:
    # Fall back to development database if no URL provided
    logger.warning("No DATABASE_URL environment variable found, using SQLite for development")
    db_url = "sqlite:///pastebin.db"

# Apply more aggressive patch to fix SQLAlchemy psycopg2 dialect issue
try:
    # First make sure we have psycopg2 installed
    import psycopg2
    import psycopg2.extras
    logger.info("Successfully imported psycopg2 and psycopg2.extras")
except ImportError:
    logger.error("psycopg2 not found, trying to use psycopg2-binary")
    try:
        import sys
        import types
        
        # Create a mock psycopg2 module if it doesn't exist
        if 'psycopg2' not in sys.modules:
            psycopg2 = types.ModuleType('psycopg2')
            sys.modules['psycopg2'] = psycopg2
            logger.info("Created mock psycopg2 module")
        
        # Create a mock psycopg2.extras module with the necessary functions
        mock_extras = types.ModuleType('psycopg2.extras')
        mock_extras.register_uuid = lambda conn: None
        mock_extras.register_default_json = lambda conn: None
        mock_extras.register_default_jsonb = lambda conn: None
        
        # Add HstoreAdapter class
        class HstoreAdapter:
            @staticmethod
            def get_oids(conn):
                # Return dummy OIDs that won't be used but prevent errors
                return (-1, -2)
                
        mock_extras.HstoreAdapter = HstoreAdapter
        sys.modules['psycopg2.extras'] = mock_extras
        logger.info("Created mock psycopg2.extras module")
        
        # Now patch SQLAlchemy's psycopg2 dialect
        try:
            from sqlalchemy.dialects.postgresql import psycopg2 as sa_psycopg2
            
            # Replace the _psycopg2_extras property on the PGDialect_psycopg2 class
            def _patched_extras(self):
                return mock_extras
                
            # Replace the on_connect method to avoid accessing _psycopg2_extras
            def _patched_on_connect(self):
                def connect(conn):
                    conn.set_isolation_level(self.isolation_level)
                    return conn
                return connect
            
            # Create a patched initialize method to bypass hstore checks
            def _patched_initialize(self, connection):
                # Skip the hstore initialization that causes problems
                pass
                
            # Apply the patches
            sa_psycopg2.PGDialect_psycopg2._psycopg2_extras = property(_patched_extras)
            sa_psycopg2.PGDialect_psycopg2.on_connect = _patched_on_connect
            sa_psycopg2.PGDialect_psycopg2.initialize = _patched_initialize
            
            logger.info("Successfully applied aggressive patch to psycopg2 dialect")
        except Exception as e:
            logger.error(f"Failed to patch SQLAlchemy's psycopg2 dialect: {e}")
    except Exception as e:
        logger.error(f"Failed to create mock psycopg2 modules: {e}")

# Ensure we have a database URL
if not db_url:
    logger.error("No DATABASE_URL environment variable found!")
    db_url = "sqlite:///pastebin.db"  # Fallback for development only
    
# Fix URL format for different PostgreSQL URL styles
if db_url and db_url.startswith('postgres://'):
    db_url = db_url.replace('postgres://', 'postgresql://', 1)
    
# Log a sanitized version of the URL (hiding credentials)
if db_url:
    if 'postgresql://' in db_url:
        parts = db_url.split('@')
        if len(parts) > 1:
            sanitized_url = f"postgresql://****:****@{parts[1]}"
            logger.info(f"Using database URL: {sanitized_url}")
        else:
            logger.info("Using PostgreSQL database")
    elif 'mysql' in db_url:
        # We're seeing a MySQL URL, but Render uses PostgreSQL
        logger.warning("MySQL URL detected, but Render uses PostgreSQL. This may cause errors.")
        parts = db_url.split('@')
        if len(parts) > 1:
            sanitized_url = f"mysql://****:****@{parts[1]}"
            logger.info(f"Using database URL: {sanitized_url}")
        else:
            logger.info("Using MySQL database")
    else:
        logger.info(f"Using database URL type: {db_url.split(':')[0]}")

app.config["SQLALCHEMY_DATABASE_URI"] = db_url
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
    "pool_recycle": 300,
    "pool_pre_ping": True,
}

# Initialize SQLAlchemy
from db import db
db.init_app(app)

# Initialize login manager
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'auth.login'
login_manager.login_message_category = 'info'

# Initialize CSRF protection
csrf = CSRFProtect()
csrf.init_app(app)

# Initialize rate limiter
limiter = Limiter(
    get_remote_address,
    app=app,
    default_limits=["200 per day", "50 per hour"],
    storage_uri="memory://",
)

# Initialize the database and load models once
with app.app_context():
    # Import models
    logger.info("Importing models")
    import models
    
    # Create tables if they don't exist
    logger.info("Creating database tables")
    db.create_all()
    
    # Configure user loader
    from models import User
    @login_manager.user_loader
    def load_user(user_id):
        return db.session.get(User, int(user_id))
    
    # Register Blueprints
    logger.info("Registering blueprints")
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
    app.register_blueprint(paste_bp, url_prefix='')  # Note: Ensure root path for paste_bp
    app.register_blueprint(user_bp, url_prefix='/user')
    app.register_blueprint(search_bp, url_prefix='/search')
    app.register_blueprint(comment_bp, url_prefix='/comment')
    app.register_blueprint(notification_bp, url_prefix='/notification')
    app.register_blueprint(collection_bp, url_prefix='/collection')
    app.register_blueprint(admin_bp, url_prefix='/admin')
    app.register_blueprint(account_bp, url_prefix='/account')

# Apply error handlers outside the app context
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

@app.errorhandler(SQLAlchemyError)
def handle_db_error(error):
    app.logger.error(f"Database error: {error}")
    return render_template('errors/500.html', error_id="DB-ERROR"), 500

# Add template filters
from datetime import datetime

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
        # Check for special short_id
        if hasattr(paste, 'short_id') and 'expires_in_10_minutes' in paste.short_id:
            return True
            
        # If that doesn't work, check the time difference
        if hasattr(paste, 'expires_at') and paste.expires_at and hasattr(paste, 'created_at'):
            # Calculate total minutes of expiration
            diff = paste.expires_at - paste.created_at
            total_minutes = diff.total_seconds() / 60
            
            # If it's close to 10 minutes (between 9 and 11)
            if 9 <= total_minutes <= 11:
                return True
                
        return False
    
    return {
        'now': datetime.utcnow(),
        'is_ten_minute_expiration': is_ten_minute_expiration
    }

# Report successful setup
logger.info("Render deployment WSGI app initialization complete")