#!/usr/bin/env python3
"""
MySQL-only app for FlaskBin

This is a clean implementation that completely avoids PostgreSQL conflicts.
"""
import os
import logging
from datetime import datetime, timedelta
import secrets
import string
import json
from functools import wraps

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create the Flask application
from flask import Flask, render_template, redirect, url_for, flash, request, jsonify, abort
from flask import send_from_directory, make_response, session, g
from werkzeug.exceptions import HTTPException

# Create the Flask application
app = Flask(__name__)

# MySQL connection string
MYSQL_URI = os.environ.get("DATABASE_URL", "mysql+pymysql://u213077714_flaskbin:hOJ27K?5@185.212.71.204:3306/u213077714_flaskbin")

# Configure the application
app.config.update(
    SECRET_KEY=os.environ.get("SESSION_SECRET", "dev-secret-key"),
    SQLALCHEMY_DATABASE_URI=MYSQL_URI,
    SQLALCHEMY_TRACK_MODIFICATIONS=False,
    SQLALCHEMY_ENGINE_OPTIONS={
        "pool_recycle": 300,
        "pool_pre_ping": True,
    },
    MAX_CONTENT_LENGTH=5 * 1024 * 1024  # 5MB max upload
)

# Import MySQL modules directly (avoid psycopg2 completely)
import pymysql

# Extensions
from flask_wtf.csrf import CSRFProtect
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import LoginManager, UserMixin, current_user, login_required, login_user, logout_user

# Initialize SQLAlchemy but avoid importing until now
from flask_sqlalchemy import SQLAlchemy
db = SQLAlchemy(app)

# Initialize other extensions
login_manager = LoginManager(app)
csrf = CSRFProtect(app)

# Configure login manager
login_manager.login_view = 'index'
login_manager.login_message = 'Please log in to access this page.'
login_manager.login_message_category = 'info'

# Define models directly
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
    
    def __repr__(self):
        return f'<PasteCollection {self.name}>'

class Tag(db.Model):
    """Tag model for categorizing pastes."""
    __tablename__ = 'tags'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False, unique=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<Tag {self.name}>'

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
    collection = db.relationship('PasteCollection', backref='pastes')
    
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

# Association table for paste tags
paste_tags = db.Table('paste_tags',
    db.Column('paste_id', db.Integer, db.ForeignKey('pastes.id'), primary_key=True),
    db.Column('tag_id', db.Integer, db.ForeignKey('tags.id'), primary_key=True)
)

class Comment(db.Model):
    """Comment model for paste comments."""
    __tablename__ = 'comments'
    
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    paste_id = db.Column(db.Integer, db.ForeignKey('pastes.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    
    paste = db.relationship('Paste', backref='comments')
    user = db.relationship('User', backref='comments')
    
    def __repr__(self):
        return f'<Comment {self.id}>'

class PasteRevision(db.Model):
    """PasteRevision model for tracking paste history."""
    __tablename__ = 'paste_revisions'
    
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    paste_id = db.Column(db.Integer, db.ForeignKey('pastes.id'), nullable=False)
    
    paste = db.relationship('Paste', backref='revisions')
    
    def __repr__(self):
        return f'<PasteRevision {self.id}>'

class Notification(db.Model):
    """Notification model for user notifications."""
    __tablename__ = 'notifications'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    content = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    read = db.Column(db.Boolean, default=False)
    type = db.Column(db.String(20), default='info')
    
    user = db.relationship('User', backref='notifications')
    
    def __repr__(self):
        return f'<Notification {self.id}>'

class FlaggedPaste(db.Model):
    """FlaggedPaste model for reporting inappropriate pastes."""
    __tablename__ = 'flagged_pastes'
    
    id = db.Column(db.Integer, primary_key=True)
    paste_id = db.Column(db.Integer, db.ForeignKey('pastes.id'), nullable=False)
    reporter_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    reason = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    resolved = db.Column(db.Boolean, default=False)
    resolved_at = db.Column(db.DateTime)
    resolution_notes = db.Column(db.Text)
    
    paste = db.relationship('Paste', backref='flags')
    reporter = db.relationship('User', backref='reported_pastes')
    
    def __repr__(self):
        return f'<FlaggedPaste {self.id}>'

class FlaggedComment(db.Model):
    """FlaggedComment model for reporting inappropriate comments."""
    __tablename__ = 'flagged_comments'
    
    id = db.Column(db.Integer, primary_key=True)
    comment_id = db.Column(db.Integer, db.ForeignKey('comments.id'), nullable=False)
    reporter_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    reason = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    resolved = db.Column(db.Boolean, default=False)
    resolved_at = db.Column(db.DateTime)
    resolution_notes = db.Column(db.Text)
    
    comment = db.relationship('Comment', backref='flags')
    reporter = db.relationship('User', backref='reported_comments')
    
    def __repr__(self):
        return f'<FlaggedComment {self.id}>'

class PasteView(db.Model):
    """PasteView model for tracking paste views."""
    __tablename__ = 'paste_views'
    
    id = db.Column(db.Integer, primary_key=True)
    paste_id = db.Column(db.Integer, db.ForeignKey('pastes.id'), nullable=False)
    viewer_ip = db.Column(db.String(45))
    viewer_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    paste = db.relationship('Paste', backref='view_records')
    viewer = db.relationship('User', backref='viewed_pastes')
    
    def __repr__(self):
        return f'<PasteView {self.id}>'

# MySQL-specific utility functions
def generate_short_id():
    """Generate a random short ID for pastes using MySQL functions."""
    characters = string.ascii_letters + string.digits
    return ''.join(secrets.choice(characters) for _ in range(8))

# User loader for Flask-Login
@login_manager.user_loader
def load_user(user_id):
    """Load a user by ID for Flask-Login."""
    return User.query.get(int(user_id))

# Template filters
@app.template_filter('timesince')
def timesince_filter(dt):
    """Format datetime as relative time since."""
    if not dt:
        return "never"
        
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

# Create a context processor for utility functions
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

# Add error handlers
@app.errorhandler(404)
def not_found_error(error):
    """Handle 404 errors."""
    return render_template('errors/404.html'), 404

@app.errorhandler(500)
def internal_server_error(error):
    """Handle 500 errors."""
    db.session.rollback()
    logger.error(f"Internal server error: {error}")
    return render_template('errors/500.html', error=str(error)), 500

@app.errorhandler(403)
def handle_csrf_error(e):
    """Handle CSRF errors."""
    return render_template('errors/500.html', 
                           error="CSRF verification failed. Please try again."), 403

@app.errorhandler(Exception)
def handle_exception(e):
    """Handle all other exceptions."""
    if isinstance(e, HTTPException):
        return e
    
    logger.error(f"Unhandled exception: {e}")
    db.session.rollback()
    return render_template('errors/500.html', error=str(e)), 500

# Add routes
@app.route('/', methods=['GET', 'POST'])
def index():
    """Home page / paste creation form."""
    if request.method == 'POST':
        # Handle paste creation
        title = request.form.get('title', '').strip() or 'Untitled Paste'
        content = request.form.get('content', '')
        language = request.form.get('language', 'plaintext')
        expiration = request.form.get('expiration', 'never')
        is_public = 'is_public' in request.form
        burn_after_read = 'burn_after_read' in request.form
        
        # Validate content
        if not content:
            flash('Paste content cannot be empty.', 'danger')
            return redirect(url_for('index'))
        
        # Set expiration date
        expires_at = None
        if expiration != 'never':
            if expiration == '10min':
                expires_at = datetime.utcnow() + timedelta(minutes=10)
            elif expiration == '1hour':
                expires_at = datetime.utcnow() + timedelta(hours=1)
            elif expiration == '1day':
                expires_at = datetime.utcnow() + timedelta(days=1)
            elif expiration == '1week':
                expires_at = datetime.utcnow() + timedelta(weeks=1)
            elif expiration == '1month':
                expires_at = datetime.utcnow() + timedelta(days=30)
        
        # Create new paste
        new_paste = Paste(
            short_id=generate_short_id(),
            title=title,
            content=content,
            language=language,
            expires_at=expires_at,
            is_public=is_public,
            burn_after_read=burn_after_read,
            user_id=current_user.id if current_user.is_authenticated else None
        )
        
        db.session.add(new_paste)
        db.session.commit()
        
        # Redirect to the new paste
        flash('Paste created successfully!', 'success')
        return redirect(url_for('view_paste', short_id=new_paste.short_id))
    
    # GET request - show form with recent pastes
    recent_pastes = Paste.query.filter_by(is_public=True).order_by(Paste.created_at.desc()).limit(10).all()
    return render_template('index.html', recent_pastes=recent_pastes)

@app.route('/<short_id>')
def view_paste(short_id):
    """View a paste."""
    paste = Paste.query.filter_by(short_id=short_id).first_or_404()
    
    # Check if paste is expired
    if paste.is_expired():
        db.session.delete(paste)
        db.session.commit()
        flash('This paste has expired.', 'warning')
        return redirect(url_for('index'))
    
    # Check if burn after read
    if paste.burn_after_read:
        # Keep content but mark for deletion
        content = paste.content
        title = paste.title
        language = paste.language
        
        # Delete the paste
        db.session.delete(paste)
        db.session.commit()
        
        # Render special template for burn-after-read
        flash('This was a burn-after-read paste and has been deleted.', 'warning')
        return render_template('view_burn.html', 
                              title=title, 
                              content=content, 
                              language=language)
    
    # Increment view count
    paste.views += 1
    db.session.commit()
    
    return render_template('view.html', paste=paste)

@app.route('/report/<short_id>', methods=['GET', 'POST'])
def report_paste(short_id):
    """Report a paste for inappropriate content."""
    paste = Paste.query.filter_by(short_id=short_id).first_or_404()
    
    if request.method == 'POST':
        reason = request.form.get('reason', '').strip()
        
        if not reason:
            flash('Please provide a reason for reporting this paste.', 'danger')
            return redirect(url_for('report_paste', short_id=short_id))
        
        # Create flag record
        flag = FlaggedPaste(
            paste_id=paste.id,
            reporter_id=current_user.id if current_user.is_authenticated else None,
            reason=reason
        )
        
        db.session.add(flag)
        db.session.commit()
        
        flash('Thank you for your report. Our moderators will review it.', 'success')
        return redirect(url_for('view_paste', short_id=short_id))
    
    return render_template('report.html', paste=paste)

@app.route('/health')
def health_check():
    """Health check endpoint for Render."""
    try:
        # Try a simple query to verify database connection
        db.session.execute(db.select(User).limit(1))
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

@app.route('/download/<short_id>')
def download_paste(short_id):
    """Download a paste as a text file."""
    paste = Paste.query.filter_by(short_id=short_id).first_or_404()
    
    # Check if paste is expired
    if paste.is_expired():
        db.session.delete(paste)
        db.session.commit()
        flash('This paste has expired.', 'warning')
        return redirect(url_for('index'))
    
    # Set filename based on paste title
    filename = f"{paste.title or 'untitled'}.txt"
    filename = "".join(c for c in filename if c.isalnum() or c in (' ', '.', '-', '_')).strip()
    
    # Create response with file download
    response = make_response(paste.content)
    response.headers["Content-Disposition"] = f"attachment; filename={filename}"
    response.headers["Content-Type"] = "text/plain"
    
    return response

@app.route('/raw/<short_id>')
def raw_paste(short_id):
    """View raw paste content."""
    paste = Paste.query.filter_by(short_id=short_id).first_or_404()
    
    # Check if paste is expired
    if paste.is_expired():
        db.session.delete(paste)
        db.session.commit()
        flash('This paste has expired.', 'warning')
        return redirect(url_for('index'))
    
    # Return plain text response
    response = make_response(paste.content)
    response.headers["Content-Type"] = "text/plain; charset=utf-8"
    
    return response

@app.route('/fork/<short_id>', methods=['GET', 'POST'])
def fork_paste(short_id):
    """Fork a paste to create a new one."""
    parent = Paste.query.filter_by(short_id=short_id).first_or_404()
    
    # Check if paste is expired
    if parent.is_expired():
        db.session.delete(parent)
        db.session.commit()
        flash('This paste has expired.', 'warning')
        return redirect(url_for('index'))
    
    if request.method == 'POST':
        title = request.form.get('title', '').strip() or f"Fork of {parent.title or 'Untitled Paste'}"
        content = request.form.get('content', '')
        language = request.form.get('language', parent.language)
        expiration = request.form.get('expiration', 'never')
        is_public = 'is_public' in request.form
        
        # Validate content
        if not content:
            flash('Paste content cannot be empty.', 'danger')
            return redirect(url_for('fork_paste', short_id=short_id))
        
        # Set expiration date
        expires_at = None
        if expiration != 'never':
            if expiration == '10min':
                expires_at = datetime.utcnow() + timedelta(minutes=10)
            elif expiration == '1hour':
                expires_at = datetime.utcnow() + timedelta(hours=1)
            elif expiration == '1day':
                expires_at = datetime.utcnow() + timedelta(days=1)
            elif expiration == '1week':
                expires_at = datetime.utcnow() + timedelta(weeks=1)
            elif expiration == '1month':
                expires_at = datetime.utcnow() + timedelta(days=30)
        
        # Create new paste as fork
        fork = Paste(
            short_id=generate_short_id(),
            title=title,
            content=content,
            language=language,
            expires_at=expires_at,
            is_public=is_public,
            user_id=current_user.id if current_user.is_authenticated else None,
            parent_id=parent.id
        )
        
        # Update the parent's fork count
        parent.fork_count += 1
        
        db.session.add(fork)
        db.session.commit()
        
        flash('Paste forked successfully!', 'success')
        return redirect(url_for('view_paste', short_id=fork.short_id))
    
    return render_template('fork.html', paste=parent)

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
        
    logger.info("Database initialized successfully")

# Run the app if executed directly
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)), debug=True)