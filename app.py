"""
Application factory module.
"""
import os
import logging
from datetime import datetime
from flask import Flask, g, render_template, request
from werkzeug.middleware.proxy_fix import ProxyFix
from flask_login import LoginManager
from flask_wtf.csrf import CSRFProtect, CSRFError
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

# Import db from db module
from db import db, init_db

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Initialize extensions without binding them to an app yet
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
    logger.info("Creating Flask application with factory pattern")
    
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

    with app.app_context():
        # Import models to register them with SQLAlchemy
        # We do this only once inside the app context
        import models
        
        # Import user model for login manager
        from models import User
        
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

        # Register blueprints with proper URL prefixes
        app.register_blueprint(auth_bp, url_prefix='/auth')
        app.register_blueprint(paste_bp, url_prefix='')  # Root path for paste_bp 
        app.register_blueprint(user_bp, url_prefix='/user')
        app.register_blueprint(search_bp, url_prefix='/search')
        app.register_blueprint(comment_bp, url_prefix='/comment')
        app.register_blueprint(notification_bp, url_prefix='/notification')
        app.register_blueprint(collection_bp, url_prefix='/collection')
        app.register_blueprint(admin_bp, url_prefix='/admin')
        app.register_blueprint(account_bp, url_prefix='/account')
        
        # Create database tables
        db.create_all()
        logger.info("Database tables created")
        
        # Register error handlers
        @app.errorhandler(404)
        def not_found_error(error):
            return render_template('errors/404.html'), 404

        @app.errorhandler(500)
        def internal_server_error(error):
            error_id = f"ERR-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}-{os.urandom(3).hex()}"
            logger.critical(f"500 Error ID {error_id}: {error}")
            return render_template('errors/500.html', error_id=error_id), 500

        @app.errorhandler(CSRFError)
        def csrf_error(error):
            logger.error(f"CSRF Error: {error}")
            return render_template('errors/csrf_error.html'), 400
    
    logger.info("Flask application creation complete")
    return app