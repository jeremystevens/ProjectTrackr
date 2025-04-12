"""
WSGI configuration module for production deployment.

This module creates a Flask application using the factory pattern,
configures it for production, and makes it available as a WSGI application.
"""

import os

# Flask imports
from flask import Flask, render_template, g, jsonify
from werkzeug.middleware.proxy_fix import ProxyFix
from flask_login import LoginManager
from flask_wtf.csrf import CSRFProtect, CSRFError
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

# Import database items
from new_db import db, init_db

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
    """Create and configure the Flask application"""
    # Create the Flask application
    app = Flask(__name__)
    
    # Basic app configuration
    app.secret_key = os.environ.get("SESSION_SECRET", "dev-secret-key")
    app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)
    
    # Initialize database with the app - this just configures the db, doesn't create tables
    init_db(app)
    
    # Initialize other extensions with the app
    login_manager.init_app(app)
    csrf.init_app(app)
    limiter.init_app(app)
    login_manager.login_view = 'auth.login'
    login_manager.login_message_category = 'info'
    
    # Configure the app outside of app_context to avoid circular imports
    @login_manager.user_loader
    def load_user(user_id):
        # Import User model - this is safe because models are already initialized
        from new_models import User
        return db.session.get(User, int(user_id))
    
    # Use a single app_context for all initialization
    with app.app_context():
        # Import models - new approach with safe import utility
        from model_package.import_models import import_all_models
        import_all_models()
        
        # Now import and register blueprints
        from routes.auth import auth_bp
        from routes.paste import paste_bp
        from routes.user import user_bp
        from routes.search import search_bp
        from routes.comment import comment_bp
        from routes.notification import notification_bp
        from routes.collection import collection_bp
        from routes.admin import admin_bp
        from routes.account import account_bp
        
        # Register all the blueprints
        app.register_blueprint(auth_bp)
        app.register_blueprint(paste_bp)
        app.register_blueprint(user_bp)
        app.register_blueprint(search_bp)
        app.register_blueprint(comment_bp)
        app.register_blueprint(notification_bp)
        app.register_blueprint(collection_bp)
        app.register_blueprint(admin_bp)
        app.register_blueprint(account_bp)
        
        # Import other routes and functions 
        from app import (
            timesince_filter, 
            utility_processor,
            bad_request_error,
            unauthorized_error,
            forbidden_error,
            not_found_error,
            method_not_allowed_error,
            too_many_requests_error,
            internal_server_error,
            handle_unhandled_exception,
            csrf_error
        )
        
        # Apply error handlers and filters 
        app.template_filter('timesince')(timesince_filter)
        app.context_processor(utility_processor)
        app.errorhandler(400)(bad_request_error)
        app.errorhandler(401)(unauthorized_error)
        app.errorhandler(403)(forbidden_error)
        app.errorhandler(404)(not_found_error)
        app.errorhandler(405)(method_not_allowed_error)
        app.errorhandler(429)(too_many_requests_error)
        app.errorhandler(500)(internal_server_error)
        app.errorhandler(Exception)(handle_unhandled_exception)
        
        # Create all database tables if needed
        db.create_all()
        
    return app

# Create the application instance for WSGI servers
application = create_app()

# For backwards compatibility
app = application