"""
Application factory for Flask application.

This factory pattern ensures that SQLAlchemy models are only registered once,
solving the "class already has a primary mapper defined" error in deployment environments.
"""
import os
import logging
from datetime import datetime, timedelta

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
logger.info("Starting application factory")

def create_app(test_config=None):
    """Create and configure the Flask application using the factory pattern"""
    # Import Flask dependencies
    from flask import Flask, render_template, g, request, abort, session, url_for
    from flask_login import LoginManager
    from flask_wtf.csrf import CSRFProtect
    
    # Create Flask app
    app = Flask(__name__)
    
    # Configure from test config if provided, otherwise from environment
    if test_config:
        app.config.from_mapping(test_config)
    else:
        app.secret_key = os.environ.get("SESSION_SECRET", "dev-secret-key")
        
        # Configure database
        db_url = os.environ.get("DATABASE_URL")
        if db_url and db_url.startswith('postgres://'):
            db_url = db_url.replace('postgres://', 'postgresql://', 1)
        app.config["SQLALCHEMY_DATABASE_URI"] = db_url
        app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
        app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
            "pool_recycle": 300,
            "pool_pre_ping": True,
        }
    
    # Apply psycopg2 patch BEFORE importing SQLAlchemy models
    try:
        # Monkey patch SQLAlchemy's psycopg2 module to avoid extras import error
        import sys
        import types
        from sqlalchemy.dialects.postgresql import psycopg2 as sa_psycopg2
        
        # Create a mock extras module with required components
        mock_extras = types.ModuleType('psycopg2.extras')
        mock_extras.register_uuid = lambda conn: None
        mock_extras.register_default_json = lambda conn: None
        mock_extras.register_default_jsonb = lambda conn: None
        
        # Add HstoreAdapter class
        class HstoreAdapter:
            @staticmethod
            def get_oids(conn):
                return (-1, -2)  # Dummy OIDs
                
        mock_extras.HstoreAdapter = HstoreAdapter
        sys.modules['psycopg2.extras'] = mock_extras
        
        # Patch SQLAlchemy's psycopg2 dialect
        def _patched_extras(self):
            return mock_extras
            
        def _patched_on_connect(self):
            def connect(conn):
                conn.set_isolation_level(self.isolation_level)
                return conn
            return connect
        
        def _patched_initialize(self, connection):
            pass  # Skip problematic initialization
            
        # Apply patches
        sa_psycopg2.PGDialect_psycopg2._psycopg2_extras = property(_patched_extras)
        sa_psycopg2.PGDialect_psycopg2.on_connect = _patched_on_connect
        sa_psycopg2.PGDialect_psycopg2.initialize = _patched_initialize
        
        logger.info("Successfully applied psycopg2 patch in application factory")
    except Exception as e:
        logger.error(f"Failed to apply psycopg2 patch in application factory: {e}")
    
    # Configure extensions
    from db import db
    from flask_login import LoginManager
    from flask_wtf.csrf import CSRFProtect
    
    # Initialize database
    db.init_app(app)
    
    # Initialize login manager
    login_manager = LoginManager()
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'
    login_manager.login_message_category = 'info'
    
    # Initialize CSRF protection
    csrf = CSRFProtect()
    csrf.init_app(app)
    
    # Import models once
    with app.app_context():
        # Import all models
        import models
        from models import User
        
        # Create tables
        db.create_all()
        
        # Define user loader callback
        @login_manager.user_loader
        def load_user(user_id):
            return db.session.get(User, int(user_id))
        
        # Register blueprints
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
        app.register_blueprint(paste_bp)  # Root path for pastes
        app.register_blueprint(user_bp, url_prefix='/user')
        app.register_blueprint(search_bp, url_prefix='/search')
        app.register_blueprint(comment_bp, url_prefix='/comment')
        app.register_blueprint(notification_bp, url_prefix='/notification')
        app.register_blueprint(collection_bp, url_prefix='/collection')
        app.register_blueprint(admin_bp, url_prefix='/admin')
        app.register_blueprint(account_bp, url_prefix='/account')
    
    # Register error handlers
    @app.errorhandler(404)
    def not_found_error(error):
        return render_template('errors/404.html'), 404
    
    @app.errorhandler(500)
    def internal_server_error(error):
        error_id = f"ERR-{os.urandom(3).hex()}"
        return render_template('errors/500.html', error_id=error_id), 500
    
    # Register template filters and context processors
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
    
    logger.info("Application factory complete")
    return app