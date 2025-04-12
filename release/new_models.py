"""
Database models for the application.

This module defines all the SQLAlchemy models used by the application.
It imports the db instance from db.py to avoid circular imports.
"""
from datetime import datetime, timedelta
import uuid
import hashlib
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from sqlalchemy.sql import func

from new_db import db

# Define all models here
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
    
    # Security-related fields
    security_question = db.Column(db.String(200))
    security_answer_hash = db.Column(db.String(256))
    
    # Account lockout fields
    failed_login_attempts = db.Column(db.Integer, default=0)
    locked_until = db.Column(db.DateTime)
    
    # User ban fields
    is_banned = db.Column(db.Boolean, default=False)
    ban_reason = db.Column(db.String(200))
    is_shadowbanned = db.Column(db.Boolean, default=False)
    
    # Subscription fields
    subscription_tier = db.Column(db.String(20), default='free')
    subscription_expires = db.Column(db.DateTime)
    payment_id = db.Column(db.String(100))
    
    # AI usage tracking
    free_ai_trials_used = db.Column(db.Integer, default=0)
    
    # Relationships
    pastes = db.relationship('Paste', backref='author', lazy='dynamic')
    collections = db.relationship('PasteCollection', backref='owner', lazy='dynamic')
    comments = db.relationship('Comment', backref='author', lazy='dynamic')
    notifications = db.relationship('Notification', backref='user', lazy='dynamic')
    
    def set_password(self, password):
        """Set the user's password hash."""
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        """Check if the password matches the hash."""
        return check_password_hash(self.password_hash, password)
    
    def set_security_answer(self, answer):
        """Hash and set the security answer."""
        if answer:
            self.security_answer_hash = generate_password_hash(answer.lower())
    
    def check_security_answer(self, answer):
        """Check if the security answer matches."""
        if not self.security_answer_hash or not answer:
            return False
        return check_password_hash(self.security_answer_hash, answer.lower())
    
    def generate_api_key(self):
        """Generate a new API key for the user."""
        self.api_key = uuid.uuid4().hex
        return self.api_key
    
    def is_account_locked(self):
        """Check if the account is temporarily locked due to failed login attempts."""
        if self.locked_until and self.locked_until > datetime.utcnow():
            return True
        return False
    
    def register_failed_login(self):
        """Register a failed login attempt and lock the account if needed."""
        self.failed_login_attempts += 1
        
        # Lock account after 5 failed attempts
        if self.failed_login_attempts >= 5:
            # Lock for 15 minutes
            self.locked_until = datetime.utcnow() + timedelta(minutes=15)
        
        return self.is_account_locked()
    
    def reset_failed_login_attempts(self):
        """Reset the failed login attempts counter."""
        self.failed_login_attempts = 0
        self.locked_until = None
    
    def is_subscription_active(self):
        """Check if the user has an active paid subscription."""
        if self.subscription_tier == 'free':
            return False
        
        if not self.subscription_expires:
            return False
            
        return self.subscription_expires > datetime.utcnow()
    
    def can_use_ai_feature(self):
        """Check if user can use AI features (subscriber or has trials left)."""
        if self.is_subscription_active():
            return True
            
        # Free users get 3 trial uses
        return self.free_ai_trials_used < 3
    
    def use_ai_trial(self):
        """Use one AI trial and return remaining count."""
        if self.free_ai_trials_used < 3:
            self.free_ai_trials_used += 1
        return 3 - self.free_ai_trials_used
    
    def __repr__(self):
        return f'<User {self.username}>'


class Paste(db.Model):
    """Paste model for storing text snippets."""
    __tablename__ = 'pastes'
    
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False, default='Untitled')
    content = db.Column(db.Text, nullable=False)
    syntax = db.Column(db.String(30), default='text')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    expires_at = db.Column(db.DateTime)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    public = db.Column(db.Boolean, default=True)
    views = db.Column(db.Integer, default=0)
    slug = db.Column(db.String(20), unique=True, index=True)
    
    # Encryption fields
    is_encrypted = db.Column(db.Boolean, default=False)
    encryption_salt = db.Column(db.String(64))
    
    # Burn after reading option
    burn_after_read = db.Column(db.Boolean, default=False)
    has_been_read = db.Column(db.Boolean, default=False)
    
    # Fork-related fields
    fork_of = db.Column(db.Integer, db.ForeignKey('pastes.id'))
    fork_count = db.Column(db.Integer, default=0)
    
    # Collection relationship
    collection_id = db.Column(db.Integer, db.ForeignKey('paste_collections.id'))
    
    # AI summary
    ai_summary = db.Column(db.Text)
    
    # Comments
    comments_enabled = db.Column(db.Boolean, default=True)
    
    # Relationships
    comments = db.relationship('Comment', backref='paste', lazy='dynamic')
    revisions = db.relationship('PasteRevision', backref='paste', lazy='dynamic')
    reports = db.relationship('FlaggedPaste', backref='paste', lazy='dynamic')
    
    # Many-to-many relationship with tags
    tags = db.relationship('Tag', secondary='paste_tags', backref=db.backref('pastes', lazy='dynamic'))
    
    def __init__(self, **kwargs):
        super(Paste, self).__init__(**kwargs)
        if not self.slug:
            self.slug = self.generate_slug()
    
    def generate_slug(self):
        """Generate a short unique identifier for the paste."""
        return uuid.uuid4().hex[:8]
    
    def is_expired(self):
        """Check if the paste has expired."""
        if not self.expires_at:
            return False
        return self.expires_at < datetime.utcnow()
    
    def should_burn(self):
        """Check if a burn-after-read paste should be deleted."""
        return self.burn_after_read and self.has_been_read
    
    def is_owned_by(self, user):
        """Check if the paste is owned by the specified user."""
        if not user:
            return False
        return self.user_id == user.id
    
    def increment_view(self):
        """Increment the view counter."""
        self.views += 1
        
        # Mark as read if it's a burn after read paste
        if self.burn_after_read and not self.has_been_read:
            self.has_been_read = True
    
    def increment_fork_count(self):
        """Increment the fork counter."""
        self.fork_count += 1
    
    def __repr__(self):
        return f'<Paste {self.title[:20]}>'


class PasteRevision(db.Model):
    """Revision history for pastes."""
    __tablename__ = 'paste_revisions'
    
    id = db.Column(db.Integer, primary_key=True)
    paste_id = db.Column(db.Integer, db.ForeignKey('pastes.id'), nullable=False)
    content = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    revision_number = db.Column(db.Integer, nullable=False)
    
    def __repr__(self):
        return f'<PasteRevision {self.paste_id}:{self.revision_number}>'


class Comment(db.Model):
    """Comment model for paste comments."""
    __tablename__ = 'comments'
    
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    paste_id = db.Column(db.Integer, db.ForeignKey('pastes.id'), nullable=False)
    parent_id = db.Column(db.Integer, db.ForeignKey('comments.id'))
    
    # Relationships
    replies = db.relationship('Comment', 
                              backref=db.backref('parent', remote_side=[id]),
                              lazy='dynamic')
    
    def __repr__(self):
        return f'<Comment {self.id}>'


class PasteCollection(db.Model):
    """Collection to organize pastes."""
    __tablename__ = 'paste_collections'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    public = db.Column(db.Boolean, default=False)
    slug = db.Column(db.String(20), unique=True, index=True)
    
    # Relationships
    pastes = db.relationship('Paste', backref='collection', lazy='dynamic')
    
    def __init__(self, **kwargs):
        super(PasteCollection, self).__init__(**kwargs)
        if not self.slug:
            self.slug = uuid.uuid4().hex[:8]
    
    def __repr__(self):
        return f'<Collection {self.name}>'


class Tag(db.Model):
    """Tag for pastes."""
    __tablename__ = 'tags'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(30), nullable=False, unique=True)
    
    def __repr__(self):
        return f'<Tag {self.name}>'


class PasteTag(db.Model):
    """Association table for many-to-many relationship between pastes and tags."""
    __tablename__ = 'paste_tags'
    
    paste_id = db.Column(db.Integer, db.ForeignKey('pastes.id'), primary_key=True)
    tag_id = db.Column(db.Integer, db.ForeignKey('tags.id'), primary_key=True)


class Notification(db.Model):
    """Notification model for user notifications."""
    __tablename__ = 'notifications'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    content = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    read = db.Column(db.Boolean, default=False)
    link = db.Column(db.String(255))
    notification_type = db.Column(db.String(20), default='info')  # info, comment, system
    
    def __repr__(self):
        return f'<Notification {self.id}>'


class FlaggedPaste(db.Model):
    """Model for reporting problematic pastes."""
    __tablename__ = 'flagged_pastes'
    
    id = db.Column(db.Integer, primary_key=True)
    paste_id = db.Column(db.Integer, db.ForeignKey('pastes.id'), nullable=False)
    reporter_id = db.Column(db.Integer, db.ForeignKey('users.id'))  # Can be null for anonymous reports
    reason = db.Column(db.String(100), nullable=False)
    details = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    status = db.Column(db.String(20), default='pending')  # pending, reviewed, rejected, actioned
    admin_notes = db.Column(db.Text)
    
    def __repr__(self):
        return f'<FlaggedPaste {self.paste_id}>'


class AdminAction(db.Model):
    """Model for logging administrative actions."""
    __tablename__ = 'admin_actions'
    
    id = db.Column(db.Integer, primary_key=True)
    admin_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    action_type = db.Column(db.String(50), nullable=False)
    target_id = db.Column(db.Integer)  # Generic reference to any entity ID
    target_type = db.Column(db.String(50))  # user, paste, comment, etc.
    details = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationship with admin user
    admin = db.relationship('User', backref='admin_actions')
    
    def __repr__(self):
        return f'<AdminAction {self.action_type} on {self.target_type}>'