"""
Application configuration module for Flask application.

This module defines helper functions, error handlers, and template filters
used by the application.
"""

import os
from datetime import datetime
import logging

# Flask imports
from flask import Flask, render_template, g, jsonify
from werkzeug.middleware.proxy_fix import ProxyFix
from flask_login import LoginManager
from flask_wtf.csrf import CSRFProtect, CSRFError
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
import sentry_sdk
from sentry_sdk.integrations.flask import FlaskIntegration

# Import database configuration
from new_db import db, init_db

# Set up Sentry error tracking if configured
SENTRY_DSN = os.environ.get("SENTRY_DSN")
if SENTRY_DSN:
    sentry_sdk.init(
        dsn=SENTRY_DSN,
        integrations=[FlaskIntegration()],
        traces_sample_rate=0.1,
        send_default_pii=False
    )

# Set up extensions
login_manager = LoginManager()
csrf = CSRFProtect()
limiter = Limiter(
    key_func=get_remote_address,
    default_limits=["200 per day", "50 per hour"],
    storage_uri="memory://",
    strategy="fixed-window"
)

def create_app():
    """
    Application factory function that creates and configures the Flask app
    This pattern helps prevent circular imports and duplicate model registration
    """
    # Create the application
    app = Flask(__name__)
    app.secret_key = os.environ.get("SESSION_SECRET", "dev-secret-key")
    app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)  # Needed for url_for to generate with https

    # Configure custom error pages
    app.config['TRAP_HTTP_EXCEPTIONS'] = True
    app.config['ERROR_INCLUDE_MESSAGE'] = True

    # Initialize database with the app
    init_db(app)
    
    # Initialize the app with extensions
    login_manager.init_app(app)
    csrf.init_app(app)
    limiter.init_app(app)
    login_manager.login_view = 'auth.login'
    login_manager.login_message_category = 'info'

    @app.before_request
    def before_request():
        g.current_time = datetime.utcnow()

    with app.app_context():
        # Import models - use the new safer approach
        from model_package.import_models import import_all_models
        import_all_models()
        
        # Import user model for login manager
        from new_models import User
        
        # Set up login manager loader
        @login_manager.user_loader
        def load_user(user_id):
            return db.session.get(User, int(user_id))

        # Import blueprints inside the app context to avoid circular imports
        from routes.auth import auth_bp
        from routes.paste import paste_bp
        from routes.user import user_bp
        from routes.search import search_bp
        from routes.comment import comment_bp
        from routes.notification import notification_bp
        from routes.collection import collection_bp
        from routes.admin import admin_bp
        from routes.account import account_bp

        # Register blueprints
        app.register_blueprint(auth_bp)
        app.register_blueprint(paste_bp)
        app.register_blueprint(user_bp)
        app.register_blueprint(search_bp)
        app.register_blueprint(comment_bp)
        app.register_blueprint(notification_bp)
        app.register_blueprint(collection_bp)
        app.register_blueprint(admin_bp)
        app.register_blueprint(account_bp)
        
        # Create database tables
        db.create_all()
        
    return app
    
# Create the application instance
app = create_app()

# Add template filters
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

# Error handlers
@app.errorhandler(400)
def bad_request_error(error):
    """Handle 400 Bad Request errors"""
    app.logger.error(f"400 Error: {error}")
    error_details = str(error) if app.debug else None
    return render_template('errors/400.html', error_details=error_details), 400

@app.errorhandler(401)
def unauthorized_error(error):
    """Handle 401 Unauthorized errors"""
    app.logger.error(f"401 Error: {error}")
    return render_template('errors/401.html'), 401

@app.errorhandler(403)
def forbidden_error(error):
    """Handle 403 Forbidden errors"""
    app.logger.error(f"403 Error: {error}")
    return render_template('errors/403.html'), 403

@app.errorhandler(404)
def not_found_error(error):
    """Handle 404 Not Found errors"""
    app.logger.error(f"404 Error: {error}")
    return render_template('errors/404.html'), 404

@app.errorhandler(405)
def method_not_allowed_error(error):
    """Handle 405 Method Not Allowed errors"""
    app.logger.error(f"405 Error: {error}")
    allowed_methods = error.get_headers().get('Allow', '').split(', ') if hasattr(error, 'get_headers') else []
    return render_template('errors/405.html', allowed_methods=allowed_methods), 405

@app.errorhandler(429)
def too_many_requests_error(error):
    """Handle 429 Too Many Requests errors"""
    app.logger.error(f"429 Error: {error}")
    # Extract retry-after value if available
    retry_after = None
    if hasattr(error, 'description') and isinstance(error.description, dict):
        retry_after = error.description.get('retry_after')
    return render_template('errors/429.html', retry_after=retry_after), 429

@app.errorhandler(500)
def internal_server_error(error):
    """Handle 500 Internal Server errors"""
    # Generate a unique error ID for tracking
    error_id = f"ERR-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}-{os.urandom(3).hex()}"
    app.logger.critical(f"500 Error ID {error_id}: {error}")
    app.logger.exception("Exception details:")
    return render_template('errors/500.html', error_id=error_id), 500

@app.errorhandler(Exception)
def handle_unhandled_exception(error):
    """Handle any unhandled exceptions"""
    error_id = f"ERR-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}-{os.urandom(3).hex()}"
    app.logger.critical(f"Unhandled Exception ID {error_id}: {error}")
    app.logger.exception("Exception details:")
    return render_template('errors/500.html', error_id=error_id), 500

# CSRF error handler
@app.errorhandler(CSRFError)
def csrf_error(error):
    """Handle CSRF errors"""
    app.logger.error(f"CSRF Error: {error}")
    return render_template('errors/csrf_error.html'), 400