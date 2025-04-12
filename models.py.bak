"""
Database models for FlaskBin application.

This module defines all database models using SQLAlchemy ORM.
"""
from datetime import datetime, timedelta
import secrets
import hashlib
import uuid
from app import db
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

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
        token_hash = hashlib.sha256(reset_token.encode()).hexdigest()
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


class PasteView(db.Model):
    """Tracks individual views of pastes."""
    __tablename__ = 'paste_views'
    
    id = db.Column(db.Integer, primary_key=True)
    paste_id = db.Column(db.Integer, db.ForeignKey('pastes.id'), nullable=False)
    viewer_ip = db.Column(db.String(64))
    user_agent = db.Column(db.String(256))
    viewed_at = db.Column(db.DateTime, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    
    paste = db.relationship('Paste', backref='views_log')
    user = db.relationship('User', backref='paste_views')
    
    def __repr__(self):
        return f'<PasteView {self.id} for Paste {self.paste_id}>'


class Comment(db.Model):
    """Comments on pastes."""
    __tablename__ = 'comments'
    
    id = db.Column(db.Integer, primary_key=True)
    paste_id = db.Column(db.Integer, db.ForeignKey('pastes.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    content = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_deleted = db.Column(db.Boolean, default=False)
    parent_id = db.Column(db.Integer, db.ForeignKey('comments.id'))
    
    paste = db.relationship('Paste', backref='comments')
    user = db.relationship('User', backref='comments')
    replies = db.relationship('Comment', backref=db.backref('parent', remote_side=[id]))
    
    def __repr__(self):
        return f'<Comment {self.id} for Paste {self.paste_id}>'


class PasteRevision(db.Model):
    """Revision history for pastes."""
    __tablename__ = 'paste_revisions'
    
    id = db.Column(db.Integer, primary_key=True)
    paste_id = db.Column(db.Integer, db.ForeignKey('pastes.id'), nullable=False)
    content = db.Column(db.Text, nullable=False)
    language = db.Column(db.String(30))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    revision_number = db.Column(db.Integer, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    title = db.Column(db.String(100))
    
    paste = db.relationship('Paste', backref='revisions')
    user = db.relationship('User', backref='paste_revisions')
    
    def __repr__(self):
        return f'<PasteRevision {self.revision_number} for Paste {self.paste_id}>'


class Notification(db.Model):
    """User notifications."""
    __tablename__ = 'notifications'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    content = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_read = db.Column(db.Boolean, default=False)
    notification_type = db.Column(db.String(20), nullable=False)
    related_id = db.Column(db.Integer)
    
    user = db.relationship('User', backref='notifications')
    
    def __repr__(self):
        return f'<Notification {self.id} for User {self.user_id}>'


class PasteCollection(db.Model):
    """Collections for organizing pastes."""
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
    """Tags for categorizing pastes."""
    __tablename__ = 'tags'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False, unique=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<Tag {self.name}>'


class PasteTag(db.Model):
    """Association table for paste-tag many-to-many relationship."""
    __tablename__ = 'paste_tags'
    
    paste_id = db.Column(db.Integer, db.ForeignKey('pastes.id'), primary_key=True)
    tag_id = db.Column(db.Integer, db.ForeignKey('tags.id'), primary_key=True)
    
    paste = db.relationship('Paste', backref=db.backref('tags_association', cascade='all, delete-orphan'))
    tag = db.relationship('Tag', backref=db.backref('pastes_association', cascade='all, delete-orphan'))


class FlaggedPaste(db.Model):
    """Reports of inappropriate pastes."""
    __tablename__ = 'flagged_pastes'
    
    id = db.Column(db.Integer, primary_key=True)
    paste_id = db.Column(db.Integer, db.ForeignKey('pastes.id'), nullable=False)
    reporter_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    reason = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    resolved = db.Column(db.Boolean, default=False)
    resolved_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    resolution_note = db.Column(db.Text)
    resolved_at = db.Column(db.DateTime)
    
    paste = db.relationship('Paste', backref='flags', foreign_keys=[paste_id])
    reporter = db.relationship('User', backref='reported_pastes', foreign_keys=[reporter_id])
    resolver = db.relationship('User', backref='resolved_paste_flags', foreign_keys=[resolved_by])
    
    def __repr__(self):
        return f'<FlaggedPaste {self.id} for Paste {self.paste_id}>'


class FlaggedComment(db.Model):
    """Reports of inappropriate comments."""
    __tablename__ = 'flagged_comments'
    
    id = db.Column(db.Integer, primary_key=True)
    comment_id = db.Column(db.Integer, db.ForeignKey('comments.id'), nullable=False)
    reporter_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    reason = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    resolved = db.Column(db.Boolean, default=False)
    resolved_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    resolution_note = db.Column(db.Text)
    resolved_at = db.Column(db.DateTime)
    
    comment = db.relationship('Comment', backref='flags')
    reporter = db.relationship('User', backref='reported_comments', foreign_keys=[reporter_id])
    resolver = db.relationship('User', backref='resolved_comment_flags', foreign_keys=[resolved_by])
    
    def __repr__(self):
        return f'<FlaggedComment {self.id} for Comment {self.comment_id}>'