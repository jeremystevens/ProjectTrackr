"""
WSGI entry point for FlaskBin in production.

This file is specifically designed to avoid SQLAlchemy mapper conflicts when deployed.
It uses a completely flat structure with careful import ordering.
"""
import os
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
logger.info("Starting WSGI application")

# Import Flask and create the app
from flask import Flask
app = Flask(__name__)

# Configure app
app.config.update(
    SECRET_KEY=os.environ.get("SESSION_SECRET", "dev-secret-key"),
    SQLALCHEMY_DATABASE_URI=os.environ.get("DATABASE_URL", "sqlite:///pastebin.db"),
    SQLALCHEMY_TRACK_MODIFICATIONS=False,
    SQLALCHEMY_ENGINE_OPTIONS={
        "pool_recycle": 300,
        "pool_pre_ping": True,
    }
)

# Import SQLAlchemy instance
from new_db import db
db.init_app(app)

# Set up extensions within app context
with app.app_context():
    # Import models after db initialization
    logger.info("Importing models")
    from new_models import User, Paste, PasteRevision, Comment, PasteCollection, Tag, PasteTag
    
    # Create tables if they don't exist
    logger.info("Creating database tables")
    db.create_all()
    
    # Initialize Flask-Login
    from flask_login import LoginManager
    login_manager = LoginManager()
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'
    login_manager.login_message_category = 'info'
    
    # Configure user loader
    @login_manager.user_loader
    def load_user(user_id):
        return db.session.get(User, int(user_id))
    
    # Initialize CSRF protection
    from flask_wtf.csrf import CSRFProtect
    csrf = CSRFProtect()
    csrf.init_app(app)
    
    # Register Blueprints AFTER model imports to avoid circular references
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
    
    app.register_blueprint(auth_bp)
    app.register_blueprint(paste_bp)
    app.register_blueprint(user_bp)
    app.register_blueprint(search_bp)
    app.register_blueprint(comment_bp)
    app.register_blueprint(notification_bp)
    app.register_blueprint(collection_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(account_bp)

# Now register error handlers outside app context
from flask import render_template
from flask_wtf.csrf import CSRFError
from sqlalchemy.exc import SQLAlchemyError

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

logger.info("WSGI application initialization complete")