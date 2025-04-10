from datetime import datetime, timedelta
import hashlib
import uuid
import secrets
import os
from app import db, app
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from sqlalchemy.sql import func

class User(UserMixin, db.Model):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_login = db.Column(db.DateTime, default=datetime.utcnow)
    bio = db.Column(db.Text, nullable=True)
    website = db.Column(db.String(255), nullable=True)
    location = db.Column(db.String(100), nullable=True)
    total_pastes = db.Column(db.Integer, default=0)
    total_views = db.Column(db.Integer, default=0)
    security_question = db.Column(db.String(255), nullable=True)
    security_answer_hash = db.Column(db.String(256), nullable=True)
    
    # Account security fields
    failed_login_attempts = db.Column(db.Integer, default=0)
    failed_reset_attempts = db.Column(db.Integer, default=0)
    account_locked_until = db.Column(db.DateTime, nullable=True)
    last_failed_attempt = db.Column(db.DateTime, nullable=True)

    # Relationships
    pastes = db.relationship('Paste', backref='author', lazy='dynamic', cascade='all, delete-orphan')
    password_reset_tokens = db.relationship('PasswordResetToken', backref='user', lazy='dynamic', cascade='all, delete-orphan')

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
        
    def set_security_answer(self, answer):
        """Hash and store the security answer"""
        self.security_answer_hash = generate_password_hash(answer.lower().strip())
        
    def check_security_answer(self, answer):
        """Verify the security answer"""
        if not self.security_answer_hash:
            return False
        return check_password_hash(self.security_answer_hash, answer.lower().strip())
        
    def is_account_locked(self):
        """Check if the account is temporarily locked"""
        if self.account_locked_until and self.account_locked_until > datetime.utcnow():
            return True
        return False
        
    def get_lockout_remaining_time(self):
        """Get the remaining time (in minutes) until account is unlocked"""
        if not self.is_account_locked():
            return 0
            
        remaining = self.account_locked_until - datetime.utcnow()
        return max(0, int(remaining.total_seconds() // 60))
        
    def record_failed_login(self):
        """Record a failed login attempt and lock account if needed"""
        self.failed_login_attempts += 1
        self.last_failed_attempt = datetime.utcnow()
        
        # Lock account after 5 failed attempts
        if self.failed_login_attempts >= 5:
            lockout_minutes = min(15 * (self.failed_login_attempts - 4), 60)  # Progressive lockout
            self.account_locked_until = datetime.utcnow() + timedelta(minutes=lockout_minutes)
            
        db.session.commit()
        
    def record_failed_reset_attempt(self):
        """Record a failed password reset attempt and lock reset functionality if needed"""
        self.failed_reset_attempts += 1
        self.last_failed_attempt = datetime.utcnow()
        
        # Lock account after 3 failed reset attempts (stricter than login)
        if self.failed_reset_attempts >= 3:
            lockout_minutes = min(30 * (self.failed_reset_attempts - 2), 120)  # Progressive lockout
            self.account_locked_until = datetime.utcnow() + timedelta(minutes=lockout_minutes)
            
        db.session.commit()
        
    def reset_failed_attempts(self, login_only=False):
        """Reset failed attempt counters after successful authentication"""
        self.failed_login_attempts = 0
        
        if not login_only:
            self.failed_reset_attempts = 0
            
        db.session.commit()

    def get_avatar_url(self, size=80):
        email_hash = hashlib.md5(self.email.lower().encode()).hexdigest()
        return f"https://www.gravatar.com/avatar/{email_hash}?s={size}&d=identicon"
        
    def generate_reset_token(self):
        """Generate a secure password reset token that expires in 24 hours"""
        # First, invalidate any existing tokens
        PasswordResetToken.query.filter_by(user_id=self.id).delete()
        
        # Create a new token
        token = PasswordResetToken(
            user_id=self.id,
            token=secrets.token_urlsafe(32),  # Generate a secure random token
            expires_at=datetime.utcnow() + timedelta(hours=24)
        )
        
        db.session.add(token)
        db.session.commit()
        
        return token.token
    
    @staticmethod
    def verify_reset_token(token):
        """Verify a password reset token and return the user if valid"""
        if not token:
            return None
            
        # Find the token in the database
        token_obj = PasswordResetToken.query.filter_by(token=token).first()
        
        # Check if token exists and is not expired
        if token_obj and token_obj.expires_at > datetime.utcnow():
            return token_obj.user
            
        return None

    def __repr__(self):
        return f'<User {self.username}>'

class PasswordResetToken(db.Model):
    """Model for password reset tokens"""
    __tablename__ = 'password_reset_tokens'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    token = db.Column(db.String(100), unique=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    expires_at = db.Column(db.DateTime, nullable=False)
    
    def is_expired(self):
        """Check if the token has expired"""
        return self.expires_at < datetime.utcnow()
        
    def __repr__(self):
        return f'<PasswordResetToken user_id={self.user_id}>'

class Paste(db.Model):
    __tablename__ = 'pastes'

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(255), nullable=False, default='Untitled')
    content = db.Column(db.Text, nullable=False)
    syntax = db.Column(db.String(50), default='text')
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    expires_at = db.Column(db.DateTime, nullable=True)
    views = db.Column(db.Integer, default=0)
    visibility = db.Column(db.String(20), default='public')  # public, private, unlisted
    short_id = db.Column(db.String(16), unique=True, nullable=False)
    size = db.Column(db.Integer, default=0)
    comments_enabled = db.Column(db.Boolean, default=True)
    
    # Relationship for comments
    comments = db.relationship('Comment', backref='paste', lazy='dynamic', 
                               cascade='all, delete-orphan', 
                               primaryjoin="and_(Paste.id==Comment.paste_id, Comment.parent_id==None)")

    def is_expired(self):
        if self.expires_at is None:
            return False
        return datetime.utcnow() > self.expires_at

    def is_ten_minute_expiration(self):
        """Check if this paste has a 10-minute expiration"""
        if not self.expires_at or not self.created_at:
            return False

        # Calculate the difference between expiration and creation time
        diff = self.expires_at - self.created_at
        minutes = diff.total_seconds() / 60

        # If it's close to 10 minutes (between 9 and 11)
        return 9 <= minutes <= 11
        
    def get_expiration_text(self):
        """Get human-readable expiration text"""
        if not self.expires_at:
            return "Never"

        # First check if this is a 10-minute paste by checking time diff from creation
        if self.is_ten_minute_expiration():
            return "10 M"

        now = datetime.utcnow()
        remaining = self.expires_at - now

        if remaining.total_seconds() <= 0:
            return "Expired"

        minutes = int(remaining.total_seconds() // 60)
        hours = minutes // 60
        minutes = minutes % 60

        if hours == 0:
            return f"{minutes} M"
        else:
            return f"{hours} H : {minutes} M"

    def update_view_count(self, viewer_id=None):
        """
        Update view count only if this is a unique viewer

        Args:
            viewer_id: A unique identifier for the viewer (session ID or IP-based)

        Returns:
            bool: True if this was a new view, False if it was a repeat view
        """
        if not viewer_id:
            return False

        # Check if this viewer has already viewed this paste
        existing_view = PasteView.query.filter_by(
            paste_id=self.id,
            viewer_id=viewer_id
        ).first()

        if existing_view:
            # This viewer has already seen this paste
            return False

        # This is a new view, create a record and increment counters
        new_view = PasteView(paste_id=self.id, viewer_id=viewer_id)
        db.session.add(new_view)

        # Increment the paste's view counter
        self.views += 1

        # Also update author's total views if paste has an author
        if self.user_id:
            self.author.total_views += 1

        db.session.commit()
        return True

    def calculate_size(self):
        """Calculate and update the paste size in bytes"""
        self.size = len(self.content.encode('utf-8'))

    @staticmethod
    def get_recent_public_pastes(limit=10):
        """Get recent public pastes that haven't expired"""
        return Paste.query.filter(
            (Paste.visibility == 'public') & 
            ((Paste.expires_at.is_(None)) | (Paste.expires_at > datetime.utcnow()))
        ).order_by(Paste.created_at.desc()).limit(limit).all()

    @staticmethod
    def set_expiration(expiry_option):
        """Set the expiration date based on the selected option"""
        import logging
        # Always use UTC for consistency across server and client
        now = datetime.utcnow()
        logging.debug(f"Setting expiration from current time (UTC): {now}")

        # Convert to int if it's a string
        if isinstance(expiry_option, str):
            expiry_option = int(expiry_option)

        if expiry_option == 0:
            return None  # Never expires
        elif expiry_option == 1:
            # Force actual 10 minute expiration
            minutes_to_add = 10
            # Add exactly 10 minutes from now to ensure timezone consistency
            expiry_time = now + timedelta(minutes=minutes_to_add)
            logging.debug(f"Setting 10-minute expiration to (UTC): {expiry_time}")
            return expiry_time
        elif expiry_option == 2:
            # 1 hour expiration
            expiry_time = now + timedelta(hours=1)
            logging.debug(f"Setting 1-hour expiration to (UTC): {expiry_time}")
            return expiry_time
        elif expiry_option == 3:
            # 1 day expiration
            expiry_time = now + timedelta(days=1)
            logging.debug(f"Setting 1-day expiration to (UTC): {expiry_time}")
            return expiry_time
        elif expiry_option == 4:
            # 1 month expiration
            expiry_time = now + timedelta(days=30)
            logging.debug(f"Setting 1-month expiration to (UTC): {expiry_time}")
            return expiry_time
        else:
            return None

    def __repr__(self):
        return f'<Paste {self.id}: {self.title}>'

class PasteView(db.Model):
    """
    Model to track unique views of pastes by storing viewer information
    (session ID or IP address) to avoid counting repeated views.
    """
    __tablename__ = 'paste_views'

    id = db.Column(db.Integer, primary_key=True)
    paste_id = db.Column(db.Integer, db.ForeignKey('pastes.id'), nullable=False)
    viewer_id = db.Column(db.String(64), nullable=False)  # Session ID or hashed IP
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Define a unique constraint to ensure one view per viewer per paste
    __table_args__ = (
        db.UniqueConstraint('paste_id', 'viewer_id', name='_paste_viewer_uc'),
    )

    # Relationship back to Paste
    paste = db.relationship('Paste', backref=db.backref('views_data', lazy='dynamic'))

    @staticmethod
    def get_or_create_viewer_id(session, ip_address):
        """
        Get or create a unique viewer ID based on session ID or IP address
        """
        # Use session ID if available
        if session.get('viewer_id'):
            return session['viewer_id']

        # Otherwise generate one based on IP address and a random component
        # to protect privacy while still being consistent per visitor
        viewer_id = str(uuid.uuid4())
        session['viewer_id'] = viewer_id
        return viewer_id


class Comment(db.Model):
    """
    Model for comments on pastes, allowing users to discuss and collaborate on code snippets.
    """
    __tablename__ = 'comments'

    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.Text, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    paste_id = db.Column(db.Integer, db.ForeignKey('pastes.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    parent_id = db.Column(db.Integer, db.ForeignKey('comments.id'), nullable=True)
    
    # Relationships
    user = db.relationship('User', backref=db.backref('comments', lazy='dynamic'))
    replies = db.relationship(
        'Comment', 
        backref=db.backref('parent', remote_side=[id]),
        lazy='dynamic'
    )
    
    def __repr__(self):
        return f'<Comment {self.id}: by {self.user.username if self.user else "unknown"} on paste {self.paste_id}>'
