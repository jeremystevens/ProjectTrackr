"""
FlaskBin - A modern pastebin application

This module contains the factory function for creating the Flask application.
It initializes all extensions, registers blueprints, and sets up error handlers.
"""
import os
import logging
import pymysql

# Setup PyMySQL as the dialect used
import sqlalchemy.dialects.mysql
sqlalchemy.dialects.mysql.dialect = sqlalchemy.dialects.mysql.pymysql.dialect
sqlalchemy.dialects.mysql.base.dialect = sqlalchemy.dialects.mysql.pymysql.dialect

# Patch sqlalchemy dialect's imports to prevent PostgreSQL dependency loading
import types
import sqlalchemy.dialects.postgresql
sqlalchemy.dialects.postgresql.psycopg2 = types.ModuleType('psycopg2_stub')
sqlalchemy.dialects.postgresql.psycopg2.dialect = type('dialect', (), {})
sqlalchemy.dialects.postgresql.psycopg2.dialect.dbapi = pymysql
sqlalchemy.dialects.postgresql.psycopg2.dialect.on_connect = lambda: None
sqlalchemy.dialects.postgresql.psycopg2._psycopg2_extras = types.ModuleType('_psycopg2_extras_stub')

from datetime import datetime, timedelta
from flask import Flask, render_template, redirect, url_for, flash, request, jsonify, send_from_directory
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, current_user, login_required
from flask_wtf.csrf import CSRFProtect
from werkzeug.middleware.proxy_fix import ProxyFix
from werkzeug.security import generate_password_hash, check_password_hash
import secrets

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize extensions
db = SQLAlchemy()
login_manager = LoginManager()
csrf = CSRFProtect()

# MySQL connection string - will be overridden by environment variable in production
MYSQL_CONNECTION_STRING = "mysql+pymysql://u213077714_flaskbin:hOJ27K?5@185.212.71.204:3306/u213077714_flaskbin"

def create_app():
    """Create and configure the Flask application."""
    app = Flask(__name__)
    
    # Configure app
    app.config.update(
        SECRET_KEY=os.environ.get("SESSION_SECRET", "dev-secret-key"),
        SQLALCHEMY_DATABASE_URI=os.environ.get("DATABASE_URL", MYSQL_CONNECTION_STRING),
        SQLALCHEMY_TRACK_MODIFICATIONS=False,
        SQLALCHEMY_ENGINE_OPTIONS={
            "pool_recycle": 300,
            "pool_pre_ping": True,
        },
        MAX_CONTENT_LENGTH=5 * 1024 * 1024  # 5MB max upload
    )
    
    # Initialize extensions with app
    db.init_app(app)
    login_manager.init_app(app)
    csrf.init_app(app)
    
    # Configure login_manager
    login_manager.login_view = 'index'
    login_manager.login_message = 'Please log in to access this page.'
    login_manager.login_message_category = 'info'
    
    # Fix for use behind proxy
    app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)
    
    # Import models inside app context to avoid circular imports
    with app.app_context():
        # Import models
        from models import User, Paste
        
        # Create all tables if they don't exist
        db.create_all()
        
        # Ensure admin user exists
        admin_user = User.query.filter_by(username='admin').first()
        if not admin_user:
            admin_user = User(
                username='admin',
                email='admin@example.com',
                is_admin=True,
                api_key=secrets.token_urlsafe(32)
            )
            admin_user.set_password('adminpassword')
            db.session.add(admin_user)
            db.session.commit()
            logger.info("Created admin user")
        
        # Base routes
        @app.route('/')
        def index():
            """Render the home page."""
            recent_pastes = Paste.query.filter_by(is_public=True).order_by(Paste.created_at.desc()).limit(10).all()
            return render_template('index.html', recent_pastes=recent_pastes)
            
        @app.route('/health')
        def health_check():
            """Health check endpoint for Render."""
            return {'status': 'ok', 'database': 'mysql'}
            
        @app.route('/favicon.ico')
        def favicon():
            """Serve favicon."""
            return send_from_directory(os.path.join(app.root_path, 'static'),
                                      'favicon.ico', mimetype='image/vnd.microsoft.icon')
            
        # Static routes
        @app.route('/robots.txt')
        def robots_txt():
            """Serve robots.txt"""
            return send_from_directory(os.path.join(app.root_path, 'static'),
                                       'robots.txt', mimetype='text/plain')
        
        # Add error handlers
        @app.errorhandler(404)
        def not_found_error(error):
            """Handle 404 errors."""
            return render_template('errors/404.html'), 404
            
        @app.errorhandler(500)
        def internal_error(error):
            """Handle 500 errors."""
            db.session.rollback()
            logger.error(f"Internal server error: {error}")
            return render_template('errors/500.html'), 500
            
        # Template filters
        @app.template_filter('timesince')
        def timesince_filter(dt):
            """Format datetime as relative time since."""
            now = datetime.utcnow()
            diff = now - dt
            
            if diff.days > 365:
                years = diff.days // 365
                return f"{years} year{'s' if years != 1 else ''} ago"
            elif diff.days > 30:
                months = diff.days // 30
                return f"{months} month{'s' if months != 1 else ''} ago"
            elif diff.days > 0:
                return f"{diff.days} day{'s' if diff.days != 1 else ''} ago"
            elif diff.seconds > 3600:
                hours = diff.seconds // 3600
                return f"{hours} hour{'s' if hours != 1 else ''} ago"
            elif diff.seconds > 60:
                minutes = diff.seconds // 60
                return f"{minutes} minute{'s' if minutes != 1 else ''} ago"
            else:
                return "just now"
                
        # User loader for Flask-Login
        @login_manager.user_loader
        def load_user(user_id):
            """Load a user by ID for Flask-Login."""
            return User.query.get(int(user_id))
            
        # Import and register blueprints if they exist - but wrapped in try/except
        try:
            from routes.auth import auth_bp
            app.register_blueprint(auth_bp)
            logger.info("Registered auth_bp blueprint")
        except ImportError:
            logger.warning("Could not import auth_bp")
            
        try:
            from routes.paste import paste_bp
            app.register_blueprint(paste_bp)
            logger.info("Registered paste_bp blueprint")
        except ImportError:
            logger.warning("Could not import paste_bp")
            
        try:
            from routes.user import user_bp
            app.register_blueprint(user_bp)
            logger.info("Registered user_bp blueprint")
        except ImportError:
            logger.warning("Could not import user_bp")
            
        try:
            from routes.admin import admin_bp
            app.register_blueprint(admin_bp)
            logger.info("Registered admin_bp blueprint")
        except ImportError:
            logger.warning("Could not import admin_bp")
        
        # Context processors
        @app.context_processor
        def utility_processor():
            """Add utility functions to the template context."""
            return {
                'now': datetime.utcnow
            }
        
    # Return the app
    return app