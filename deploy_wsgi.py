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
from flask import Flask, render_template, request, redirect, url_for
from flask_login import LoginManager
from flask_wtf.csrf import CSRFProtect, CSRFError
from sqlalchemy.exc import SQLAlchemyError
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

# Create Flask app instance
app = Flask(__name__)

# Configure app - essential settings
app.secret_key = os.environ.get("SESSION_SECRET", "dev-secret-key")
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL", "sqlite:///pastebin.db")
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
    
    # Register Blueprints with explicit URL prefixes
    logger.info("Registering blueprints")
    
    # Import blueprints
    from routes.auth import auth_bp
    from routes.user import user_bp
    from routes.search import search_bp
    from routes.comment import comment_bp
    from routes.notification import notification_bp
    from routes.collection import collection_bp
    from routes.admin import admin_bp
    from routes.account import account_bp
    
    # Import paste blueprint separately and fix its routes
    logger.info("Setting up paste routes")
    # Fix paste routes by creating a new blueprint or fixing imports
    import routes.paste
    # Ensure limiter is accessible to the paste module
    routes.paste.limiter = limiter
    # Make db accessible to the paste module
    routes.paste.db = db
    # Get the blueprint
    paste_bp = routes.paste.paste_bp
    
    # Register all blueprints
    logger.info("Registering auth blueprint")
    app.register_blueprint(auth_bp, url_prefix='/auth')
    
    logger.info("Registering paste blueprint")
    app.register_blueprint(paste_bp, url_prefix='')  # Root routes for paste
    
    logger.info("Registering user blueprint")
    app.register_blueprint(user_bp, url_prefix='/user')
    
    logger.info("Registering search blueprint")
    app.register_blueprint(search_bp, url_prefix='/search')
    
    logger.info("Registering comment blueprint")
    app.register_blueprint(comment_bp, url_prefix='/comment')
    
    logger.info("Registering notification blueprint")
    app.register_blueprint(notification_bp, url_prefix='/notifications')
    
    logger.info("Registering collection blueprint")
    app.register_blueprint(collection_bp, url_prefix='/collection')
    
    logger.info("Registering admin blueprint")
    app.register_blueprint(admin_bp, url_prefix='/admin')
    
    logger.info("Registering account blueprint")
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

# Add a root route to ensure basic functionality works
@app.route('/')
def index():
    return redirect(url_for('paste.index'))

# Report successful setup
logger.info("Render deployment WSGI app initialization complete")