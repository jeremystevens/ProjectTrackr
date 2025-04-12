"""
Main entry point for the FlaskBin application.

This file initializes and runs the Flask application with the correct database configuration.
It's designed to keep imports simple and avoid circular dependency issues.
"""
import os
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Import Flask and extensions
from flask import Flask
from flask_login import LoginManager
from flask_wtf.csrf import CSRFProtect

# Create Flask application
app = Flask(__name__)

# Configure essential settings
app.secret_key = os.environ.get("SESSION_SECRET", "dev-secret-key")

# Initialize database
from new_db import db, init_db
init_db(app)  # This configures the database connection

# Initialize login manager
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'auth.login'
login_manager.login_message_category = 'info'

# Initialize CSRF protection
csrf = CSRFProtect()
csrf.init_app(app)

# Import models after db initialization
from new_models import User, Paste

# Configure user loader
@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))

# Check if tables exist and create them if they don't
with app.app_context():
    db.create_all()

# Register all blueprints
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

# Run the application when executed directly
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)