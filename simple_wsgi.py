"""
Simplified WSGI entry point for deployment on Render.

This file avoids SQLAlchemy mapper conflicts by using a minimal approach.
"""
import os
import sys
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create Flask application here directly
from flask import Flask
app = Flask(__name__)
app.config.update(
    SECRET_KEY=os.environ.get("SESSION_SECRET", "dev-secret-key"),
    SQLALCHEMY_DATABASE_URI=os.environ.get("DATABASE_URL", "sqlite:///pastebin.db"),
    SQLALCHEMY_TRACK_MODIFICATIONS=False,
    SQLALCHEMY_ENGINE_OPTIONS={
        "pool_recycle": 300,
        "pool_pre_ping": True,
    }
)

# Initialize database
from flask_sqlalchemy import SQLAlchemy
db = SQLAlchemy(app)

# Import and load error handlers
from flask import render_template
@app.errorhandler(404)
def not_found_error(error):
    return render_template('errors/404.html'), 404

@app.errorhandler(500)
def internal_server_error(error):
    error_id = f"ERR-{os.urandom(3).hex()}"
    return render_template('errors/500.html', error_id=error_id), 500

# Create User model directly
from datetime import datetime
from flask_login import UserMixin
from werkzeug.security import check_password_hash

class User(UserMixin, db.Model):
    """User model for authentication"""
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), nullable=False)
    email = db.Column(db.String(120), nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_admin = db.Column(db.Boolean, default=False)
    
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

# Initialize Flask-Login
from flask_login import LoginManager
login_manager = LoginManager(app)
login_manager.login_view = 'auth.login'

@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))

# Create tables (but only if they don't exist)
with app.app_context():
    try:
        # Just verify the table exists
        User.query.first()
    except:
        # Create tables if needed
        db.create_all()

# Import and register the auth blueprint only
try:
    from routes.auth import auth_bp
    from routes.paste import paste_bp
    app.register_blueprint(auth_bp)
    app.register_blueprint(paste_bp)
except Exception as e:
    logger.error(f"Error loading blueprints: {e}")

# End of file - app is now loaded and ready for gunicorn