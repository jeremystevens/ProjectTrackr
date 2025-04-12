"""
WSGI entry point for Render deployment.

This file is specifically created for deployment to Render
and avoids the SQLAlchemy model mapping issues that can occur
when gunicorn imports the app.

IMPORTANT: This file MUST be used for deployment by using:
gunicorn --bind 0.0.0.0:$PORT wsgi:app
NOT:
gunicorn --bind 0.0.0.0:$PORT main:app
"""
import os
import logging
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase
from werkzeug.middleware.proxy_fix import ProxyFix
from flask_login import LoginManager
from flask_wtf.csrf import CSRFProtect
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

# Configure logging
logging.basicConfig(level=logging.DEBUG)

# Create a base class for SQLAlchemy models
class Base(DeclarativeBase):
    pass

# Initialize extensions without binding them to an app yet
db = SQLAlchemy(model_class=Base)
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
    
    # Configure the database
    app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL", "sqlite:///pastebin.db")
    app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
        "pool_recycle": 300,
        "pool_pre_ping": True,
    }
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    
    # Initialize extensions with the app
    db.init_app(app)
    login_manager.init_app(app)
    csrf.init_app(app)
    limiter.init_app(app)
    login_manager.login_view = 'auth.login'
    login_manager.login_message_category = 'info'
    
    with app.app_context():
        # Import models (must be done inside app context to avoid mapper conflicts)
        from models import User, Paste
        
        # Register blueprints after models are imported
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
        
        # Set up login manager loader 
        @login_manager.user_loader
        def load_user(user_id):
            return db.session.get(User, int(user_id))
        
        # Import other routes and functions as needed
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
        
        # Apply the same error handlers and filters 
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
        
        # Create all database tables
        db.create_all()
        
    return app

# Create and configure the application directly for WSGI servers
application = create_app()

# For backwards compatibility
app = application