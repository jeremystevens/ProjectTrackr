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
from flask import Flask, render_template
from flask_login import LoginManager
from flask_wtf.csrf import CSRFProtect, CSRFError
from sqlalchemy.exc import SQLAlchemyError

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
    
    app.register_blueprint(auth_bp)
    app.register_blueprint(paste_bp)
    app.register_blueprint(user_bp)
    app.register_blueprint(search_bp)
    app.register_blueprint(comment_bp)
    app.register_blueprint(notification_bp)
    app.register_blueprint(collection_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(account_bp)

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

# Report successful setup
logger.info("Render deployment WSGI app initialization complete")