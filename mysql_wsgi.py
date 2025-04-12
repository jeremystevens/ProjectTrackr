#!/usr/bin/env python3
"""
MySQL-only WSGI for Render deployment

A clean implementation of the FlaskBin application
without any PostgreSQL dependencies or monkey-patching.
"""
import os
import logging
from datetime import datetime, timedelta
import secrets

# Import Flask packages 
from flask import Flask, render_template, redirect, url_for, flash, request, jsonify, send_from_directory
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, current_user, login_required
from flask_wtf.csrf import CSRFProtect
from werkzeug.security import generate_password_hash, check_password_hash

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create Flask app
app = Flask(__name__)

# MySQL connection string - will be overridden by environment variable in production
MYSQL_URI = "mysql+pymysql://u213077714_flaskbin:hOJ27K?5@185.212.71.204:3306/u213077714_flaskbin"

# Configure app
app.config.update(
    SECRET_KEY=os.environ.get("SESSION_SECRET", "dev-secret-key"),
    SQLALCHEMY_DATABASE_URI=os.environ.get("DATABASE_URL", MYSQL_URI),
    SQLALCHEMY_TRACK_MODIFICATIONS=False,
    SQLALCHEMY_ENGINE_OPTIONS={
        "pool_recycle": 300,
        "pool_pre_ping": True,
    },
    MAX_CONTENT_LENGTH=5 * 1024 * 1024  # 5MB max upload
)

# Initialize extensions
db = SQLAlchemy(app)
login_manager = LoginManager(app)
csrf = CSRFProtect(app)

# Configure login_manager
login_manager.login_view = 'index'
login_manager.login_message = 'Please log in to access this page.'
login_manager.login_message_category = 'info'

# Define User model
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
    
    def __repr__(self):
        return f'<User {self.username}>'
    
    def set_password(self, password):
        """Set the user's password hash."""
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        """Check if the password matches."""
        return check_password_hash(self.password_hash, password)
    
    def get_reset_token(self, expires_in=3600):
        """Generate a password reset token."""
        reset_token = secrets.token_urlsafe(32)
        # In a real application, store this token in the database with expiration
        return reset_token
    
    def generate_api_key(self):
        """Generate a new API key for the user."""
        self.api_key = secrets.token_urlsafe(32)
        return self.api_key
    
    def is_account_locked(self):
        """Check if the account is locked due to failed login attempts."""
        if self.locked_until and self.locked_until > datetime.utcnow():
            return True
        return False
    
    @property
    def is_subscription_active(self):
        """Check if the user has an active subscription."""
        if self.subscription_tier == 'free':
            return False
        if not self.subscription_expires:
            return False
        return self.subscription_expires > datetime.utcnow()

# Define Paste model
class Paste(db.Model):
    """Paste model for storing code snippets and text."""
    __tablename__ = 'pastes'
    
    id = db.Column(db.Integer, primary_key=True)
    short_id = db.Column(db.String(10), unique=True, nullable=False, index=True)
    title = db.Column(db.String(100))
    content = db.Column(db.Text, nullable=False)
    language = db.Column(db.String(30))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    expires_at = db.Column(db.DateTime)
    views = db.Column(db.Integer, default=0)
    is_public = db.Column(db.Boolean, default=True)
    password_hash = db.Column(db.String(256))
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    burn_after_read = db.Column(db.Boolean, default=False)
    is_encrypted = db.Column(db.Boolean, default=False)
    encryption_salt = db.Column(db.String(64))
    encryption_iv = db.Column(db.String(64))
    parent_id = db.Column(db.Integer, db.ForeignKey('pastes.id'))
    fork_count = db.Column(db.Integer, default=0)
    comments_enabled = db.Column(db.Boolean, default=True)
    collection_id = db.Column(db.Integer, db.ForeignKey('paste_collections.id'))
    ai_summary = db.Column(db.Text)
    
    user = db.relationship('User', backref='pastes', foreign_keys=[user_id])
    parent = db.relationship('Paste', backref='forks', remote_side=[id], foreign_keys=[parent_id])
    
    def __repr__(self):
        return f'<Paste {self.short_id}>'
    
    def set_password(self, password):
        """Set the paste's password hash."""
        if password:
            self.password_hash = generate_password_hash(password)
        else:
            self.password_hash = None
    
    def check_password(self, password):
        """Check if the password matches."""
        if not self.password_hash:
            return True
        return check_password_hash(self.password_hash, password)
    
    def is_expired(self):
        """Check if the paste has expired."""
        if not self.expires_at:
            return False
        return self.expires_at < datetime.utcnow()
    
    @property
    def formatted_expiry(self):
        """Return formatted expiry time or 'Never'."""
        if not self.expires_at:
            return "Never"
        return self.expires_at.strftime("%Y-%m-%d %H:%M:%S")

# Define PasteCollection model
class PasteCollection(db.Model):
    """Collection model for organizing pastes."""
    __tablename__ = 'paste_collections'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_public = db.Column(db.Boolean, default=True)
    
    user = db.relationship('User', backref='collections')
    pastes = db.relationship('Paste', backref='collection')
    
    def __repr__(self):
        return f'<PasteCollection {self.name}>'

# User loader for Flask-Login
@login_manager.user_loader
def load_user(user_id):
    """Load a user by ID for Flask-Login."""
    return User.query.get(int(user_id))

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

# Error handlers
@app.errorhandler(404)
def not_found_error(error):
    """Handle 404 errors."""
    return render_template('errors/404.html'), 404

@app.errorhandler(500)
def internal_server_error(error):
    """Handle 500 errors."""
    db.session.rollback()
    logger.error(f"Internal server error: {error}")
    return render_template('errors/500.html'), 500

@app.errorhandler(403)
def handle_csrf_error(e):
    """Handle CSRF errors."""
    return render_template('errors/500.html', 
                           error="CSRF verification failed. Please try again."), 403

def handle_db_error(error):
    """Handle database errors."""
    db.session.rollback()
    logger.error(f"Database error: {error}")
    return render_template('errors/500.html',
                           error="A database error occurred. Please try again later."), 500

# Context processor for utility functions
@app.context_processor
def utility_processor():
    """Add utility functions to template context."""
    def is_ten_minute_expiration(paste):
        """Check if a paste has 10-minute expiration"""
        if not paste.expires_at:
            return False
        
        time_diff = paste.expires_at - paste.created_at
        return abs(time_diff.total_seconds() - 600) < 30  # Within 30 seconds of 10 minutes
    
    return {
        'now': datetime.utcnow,
        'is_ten_minute_expiration': is_ten_minute_expiration
    }

# Routes
@app.route('/')
def index():
    """Home page / paste creation form."""
    recent_pastes = Paste.query.filter_by(is_public=True).order_by(Paste.created_at.desc()).limit(10).all()
    return render_template('index.html', recent_pastes=recent_pastes)

@app.route('/health')
def health_check():
    """Health check endpoint for Render."""
    try:
        # Try a simple query to verify database connection
        User.query.first()
        return jsonify({
            'status': 'ok', 
            'database': 'mysql',
            'version': '1.0.0',
            'time': datetime.utcnow().isoformat()
        })
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

# Create tables and initialize database
with app.app_context():
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

# Run the app if executed directly
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)