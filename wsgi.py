"""
WSGI entry point for deployment to Render.

This file is specifically designed to load models correctly to avoid
the 'class already has a primary mapper defined' error in SQLAlchemy.
"""
import os
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
logger.info("Starting WSGI entry point for Render")

# Create Flask application first
from flask import Flask
app = Flask(__name__)

# Configure app settings
app.config.update(
    SECRET_KEY=os.environ.get("SESSION_SECRET", "dev-secret-key"),
    SQLALCHEMY_DATABASE_URI=os.environ.get("DATABASE_URL", "sqlite:///pastebin.db"),
    SQLALCHEMY_TRACK_MODIFICATIONS=False,
    SQLALCHEMY_ENGINE_OPTIONS={
        "pool_recycle": 300,
        "pool_pre_ping": True,
    }
)

# Create database instance without binding to app yet
from flask_sqlalchemy import SQLAlchemy
db = SQLAlchemy()
db.init_app(app)

# Import models inside app context
with app.app_context():
    logger.info("Importing models")
    
    # Import all models here, not from another file 
    # to avoid SQLAlchemy mapper conflicts
    from datetime import datetime, timedelta
    import uuid
    from flask_login import UserMixin
    from werkzeug.security import generate_password_hash, check_password_hash
    
    # Define model classes inline to avoid import conflicts
    class User(UserMixin, db.Model):
        """User model for authentication and profile information."""
        __tablename__ = 'users'
        
        id = db.Column(db.Integer, primary_key=True)
        username = db.Column(db.String(64), unique=True, nullable=False, index=True)
        email = db.Column(db.String(120), unique=True, nullable=False, index=True)
        password_hash = db.Column(db.String(256), nullable=False)
        created_at = db.Column(db.DateTime, default=datetime.utcnow)
        last_login = db.Column(db.DateTime, default=datetime.utcnow)
        is_admin = db.Column(db.Boolean, default=False)
        api_key = db.Column(db.String(64), unique=True, index=True)
        security_question = db.Column(db.String(200))
        security_answer_hash = db.Column(db.String(256))
        failed_login_attempts = db.Column(db.Integer, default=0)
        locked_until = db.Column(db.DateTime)
        is_banned = db.Column(db.Boolean, default=False)
        ban_reason = db.Column(db.String(200))
        is_shadowbanned = db.Column(db.Boolean, default=False)
        subscription_tier = db.Column(db.String(20), default='free')
        subscription_expires = db.Column(db.DateTime)
        payment_id = db.Column(db.String(100))
        free_ai_trials_used = db.Column(db.Integer, default=0)
        
        def check_password(self, password):
            return check_password_hash(self.password_hash, password)
    
    # Create tables
    logger.info("Creating tables")
    db.create_all()
    
    # Initialize Flask-Login
    from flask_login import LoginManager
    login_manager = LoginManager()
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'
    
    # Setup user loader
    @login_manager.user_loader
    def load_user(user_id):
        try:
            return db.session.get(User, int(user_id))
        except:
            return None
    
    # Initialize CSRF protection
    from flask_wtf.csrf import CSRFProtect
    csrf = CSRFProtect()
    csrf.init_app(app)
    
    # Import and register blueprints AFTER models
    logger.info("Registering blueprints")
    
    # We need to make sure models are loaded correctly
    # The application is already live, so let's not mess with working code
    
    try:
        from routes.auth import auth_bp
        from routes.paste import paste_bp
        from routes.user import user_bp
        from routes.search import search_bp
        from routes.comment import comment_bp
        from routes.notification import notification_bp
        from routes.collection import collection_bp
        from routes.admin import admin_bp
        from routes.account import account_bp
        
        app.register_blueprint(auth_bp)
        app.register_blueprint(paste_bp)
        app.register_blueprint(user_bp)
        app.register_blueprint(search_bp)
        app.register_blueprint(comment_bp)
        app.register_blueprint(notification_bp)
        app.register_blueprint(collection_bp)
        app.register_blueprint(admin_bp)
        app.register_blueprint(account_bp)
        logger.info("All blueprints registered successfully")
    except Exception as e:
        logger.error(f"Error registering blueprints: {e}")

# Add error handlers
from flask import render_template
from flask_wtf.csrf import CSRFError
from sqlalchemy.exc import SQLAlchemyError

@app.errorhandler(404)
def not_found_error(error):
    return render_template('errors/404.html'), 404

@app.errorhandler(500)
def internal_server_error(error):
    return render_template('errors/500.html', error_id="SRV-ERROR"), 500

@app.errorhandler(CSRFError)
def handle_csrf_error(e):
    return render_template('errors/csrf_error.html'), 400

@app.errorhandler(SQLAlchemyError)
def handle_db_error(error):
    app.logger.error(f"Database error: {error}")
    return render_template('errors/500.html', error_id="DB-ERROR"), 500

logger.info("WSGI setup complete")