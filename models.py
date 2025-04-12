from datetime import datetime, timedelta
import hashlib
import uuid
import secrets
import os
import sys
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from sqlalchemy.sql import func

# Import db from db module instead of app
# This avoids circular imports between app and models
from db import db

# Prevent models from being registered multiple times
# This is needed for the SQLAlchemy mapper conflicts in production
_MODELS_REGISTERED = False

# This will help us detect when a model is being defined multiple times
_DEFINED_MODELS = set()

def register_model(model_cls):
    """Register an individual model with our tracking system"""
    model_name = model_cls.__name__
    
    # Check if the model has already been defined
    if model_name in _DEFINED_MODELS:
        # Already defined, just return the class without redefining it
        return True
    
    # Add to tracking set
    _DEFINED_MODELS.add(model_name)
    return False

def register_models():
    """Mark all models as registered to prevent duplicate registration"""
    global _MODELS_REGISTERED
    _MODELS_REGISTERED = True

# Track if models are being registered during initial import
register_models()

# Import db.is_first_import to check if this is the first time models.py is being loaded
from db import is_first_import
first_import = is_first_import()

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
    
    # User roles and subscription
    is_admin = db.Column(db.Boolean, default=False)
    is_premium = db.Column(db.Boolean, default=False)
    
    # Subscription details
    subscription_tier = db.Column(db.String(20), default='free')  # free, starter, pro, team
    subscription_start_date = db.Column(db.DateTime, nullable=True)
    subscription_end_date = db.Column(db.DateTime, nullable=True)
    
    # AI feature usage counters
    ai_calls_remaining = db.Column(db.Integer, default=0)
    ai_search_queries_remaining = db.Column(db.Integer, default=0)
    free_ai_trials_used = db.Column(db.Integer, default=0)  # Track free AI usage for non-premium users
    
    # Account security fields
    failed_login_attempts = db.Column(db.Integer, default=0)
    failed_reset_attempts = db.Column(db.Integer, default=0)
    account_locked_until = db.Column(db.DateTime, nullable=True)
    last_failed_attempt = db.Column(db.DateTime, nullable=True)
    
    # Account moderation fields
    is_banned = db.Column(db.Boolean, default=False)
    is_shadowbanned = db.Column(db.Boolean, default=False)
    ban_reason = db.Column(db.Text, nullable=True)
    banned_until = db.Column(db.DateTime, nullable=True)

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

    def is_admin_user(self):
        """Check if the user has admin privileges"""
        return self.is_admin
        
    def is_account_banned(self):
        """Check if the account is permanently or temporarily banned"""
        if not self.is_banned:
            return False
            
        # If banned_until is not set, it's a permanent ban
        if not self.banned_until:
            return True
            
        # Temporary ban (check if still active)
        if self.banned_until > datetime.utcnow():
            return True
            
        # Ban has expired, automatically unban the user
        self.is_banned = False
        db.session.commit()
        return False
        
    def get_shadowban_status(self):
        """Check if the user account is shadowbanned."""
        # Directly use the column value 
        return bool(self.is_shadowbanned)
    
    # Fixed the duplicate method error
    def get_ban_remaining_time(self):
        """Get the remaining time (in minutes) until ban expires"""
        if not self.is_banned or not self.banned_until:
            return 0
            
        remaining = self.banned_until - datetime.utcnow()
        return max(0, int(remaining.total_seconds() // 60))
    
    def get_account_status(self):
        """Get a user-friendly account status text"""
        if self.is_account_banned():
            if not self.banned_until:
                return "Permanently Banned"
            return f"Banned for {self.get_ban_remaining_time()} more minutes"
        elif self.is_shadowbanned:
            return "Shadowbanned"
        elif self.is_account_locked():
            return f"Locked for {self.get_lockout_remaining_time()} more minutes"
        elif self.is_admin:
            return "Administrator"
        elif self.subscription_tier != 'free':
            return f"{self.get_tier_display_name()} Subscriber"
        else:
            return "Active"
            
    def get_tier_display_name(self):
        """Get a user-friendly subscription tier name"""
        tier_names = {
            'free': 'Free',
            'starter': 'Starter AI',
            'pro': 'Pro AI',
            'team': 'Dev Team'
        }
        return tier_names.get(self.subscription_tier, 'Free')
        
    def is_subscription_active(self):
        """Check if user has an active subscription"""
        if self.subscription_tier == 'free':
            return False
        
        if not self.subscription_end_date:
            return False
            
        return self.subscription_end_date > datetime.utcnow()
        
    def get_subscription_days_remaining(self):
        """Get the number of days remaining in the subscription"""
        if not self.is_subscription_active():
            return 0
            
        remaining = self.subscription_end_date - datetime.utcnow()
        return max(0, remaining.days)
        
    def get_tier_limits(self):
        """Get the usage limits for the current subscription tier"""
        limits = {
            'free': {
                'ai_calls': 0,
                'ai_search_queries': 0,
                'live_collaboration': False,
                'team_seats': 0,
                'custom_themes': False,
                'analytics': False,
                'scheduled_publishing': False,
                'private_comments': False
            },
            'starter': {
                'ai_calls': 50,
                'ai_search_queries': 100,
                'live_collaboration': False,
                'team_seats': 0,
                'custom_themes': False,
                'analytics': True,
                'scheduled_publishing': False,
                'private_comments': False
            },
            'pro': {
                'ai_calls': 150,
                'ai_search_queries': 300,
                'live_collaboration': False,
                'team_seats': 0,
                'custom_themes': True,
                'analytics': True,
                'scheduled_publishing': True,
                'private_comments': True
            },
            'team': {
                'ai_calls': 500,
                'ai_search_queries': 1000,
                'live_collaboration': True,
                'team_seats': 5,
                'custom_themes': True,
                'analytics': True,
                'scheduled_publishing': True,
                'private_comments': True
            }
        }
        return limits.get(self.subscription_tier, limits['free'])
        
    def has_free_ai_trials_available(self):
        """Check if the user has free AI trials available"""
        # Maximum number of free trials
        MAX_FREE_TRIALS = 3
        
        # Check if user is logged in (not guest) and hasn't used up all trials
        return (self.id is not None and 
                self.subscription_tier == 'free' and 
                self.free_ai_trials_used < MAX_FREE_TRIALS)
    
    def get_remaining_free_trials(self):
        """Get the number of remaining free AI trials"""
        MAX_FREE_TRIALS = 3
        if self.subscription_tier != 'free':
            return 0
        return max(0, MAX_FREE_TRIALS - self.free_ai_trials_used)
    
    def use_free_ai_trial(self):
        """Use one free AI trial and return True if successful"""
        if not self.has_free_ai_trials_available():
            return False
            
        self.free_ai_trials_used += 1
        db.session.commit()
        return True
    
    def can_use_ai_feature(self):
        """Check if the user can use AI features based on subscription or free trials"""
        # First check if user has an active paid subscription with remaining calls
        if self.is_subscription_active() and self.ai_calls_remaining > 0:
            return True
            
        # Then check if they have free trials available
        return self.has_free_ai_trials_available()
        
    def can_use_ai_search(self):
        """Check if the user can use AI search based on subscription or free trials"""
        # First check if user has an active paid subscription with remaining searches
        if self.is_subscription_active() and self.ai_search_queries_remaining > 0:
            return True
            
        # Then check if they have free trials available
        return self.has_free_ai_trials_available()
        
    def use_ai_call(self):
        """Decrement AI call counter or use a free trial, and return True if successful"""
        # First check if user has an active subscription with remaining calls
        if self.is_subscription_active() and self.ai_calls_remaining > 0:
            self.ai_calls_remaining -= 1
            db.session.commit()
            return True
            
        # Then check if they have free trials available
        if self.has_free_ai_trials_available():
            return self.use_free_ai_trial()
            
        return False
        
    def use_ai_search(self):
        """Decrement AI search counter or use a free trial, and return True if successful"""
        # First check if user has an active subscription with remaining searches
        if self.is_subscription_active() and self.ai_search_queries_remaining > 0:
            self.ai_search_queries_remaining -= 1
            db.session.commit()
            return True
            
        # Then check if they have free trials available
        if self.has_free_ai_trials_available():
            return self.use_free_ai_trial()
            
        return False
        
    def reset_monthly_usage(self):
        """Reset AI feature usage counters based on subscription tier"""
        limits = self.get_tier_limits()
        self.ai_calls_remaining = limits['ai_calls']
        self.ai_search_queries_remaining = limits['ai_search_queries']
        db.session.commit()
        
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

class PasteCollection(db.Model):
    """
    Model for organizing pastes into collections/folders.
    Only available for registered users.
    """
    __tablename__ = 'paste_collections'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    is_public = db.Column(db.Boolean, default=False)
    
    # Relationship with User
    user = db.relationship('User', backref=db.backref('collections', lazy='dynamic'))
    
    # Relationship with Pastes will be defined in the Paste model
    
    def __repr__(self):
        return f'<PasteCollection {self.id}: {self.name} by user {self.user_id}>'
    
    def get_paste_count(self):
        """Get the number of pastes in this collection"""
        return Paste.query.filter_by(collection_id=self.id).count()


class Tag(db.Model):
    """
    Model for paste tags, allowing organization and searching of pastes by topic.
    """
    __tablename__ = 'tags'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False, unique=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_ai_generated = db.Column(db.Boolean, default=False)
    
    def __repr__(self):
        return f'<Tag {self.name}>'
    
    @classmethod
    def get_or_create(cls, tag_name):
        """Get an existing tag or create a new one if it doesn't exist"""
        tag = cls.query.filter(func.lower(cls.name) == func.lower(tag_name)).first()
        if not tag:
            tag = cls(name=tag_name)
            db.session.add(tag)
        return tag


# Association table for paste tags (many-to-many)
paste_tags = db.Table('paste_tags',
    db.Column('paste_id', db.Integer, db.ForeignKey('pastes.id', ondelete='CASCADE'), primary_key=True),
    db.Column('tag_id', db.Integer, db.ForeignKey('tags.id', ondelete='CASCADE'), primary_key=True)
)


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
    burn_after_read = db.Column(db.Boolean, default=False)
    
    # AI features
    ai_summary = db.Column(db.Text, nullable=True)
    
    # Encryption fields
    is_encrypted = db.Column(db.Boolean, default=False)
    encryption_method = db.Column(db.String(50), nullable=True)
    password_protected = db.Column(db.Boolean, default=False)
    password_hash = db.Column(db.String(256), nullable=True)
    encryption_salt = db.Column(db.String(128), nullable=True)
    
    # Add collection relationship
    collection_id = db.Column(db.Integer, db.ForeignKey('paste_collections.id'), nullable=True)
    
    # Forking relationship
    forked_from_id = db.Column(db.Integer, db.ForeignKey('pastes.id'), nullable=True)
    fork_count = db.Column(db.Integer, default=0)
    
    # Relationship for forks
    forks = db.relationship(
        'Paste', 
        backref=db.backref('forked_from', remote_side=[id]), 
        lazy='dynamic',
        foreign_keys='Paste.forked_from_id'
    )
    
    # Relationship for collection
    collection = db.relationship('PasteCollection', backref=db.backref('pastes', lazy='dynamic'))
    
    # Relationship for comments
    comments = db.relationship('Comment', backref='paste', lazy='dynamic', 
                               cascade='all, delete-orphan', 
                               primaryjoin="and_(Paste.id==Comment.paste_id, Comment.parent_id==None)")
                               
    # Relationship for tags
    tags = db.relationship('Tag', secondary=paste_tags, 
                          backref=db.backref('pastes', lazy='dynamic'),
                          lazy='dynamic')

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
        
    def save_revision(self, description=None):
        """
        Save the current state of the paste as a revision.
        Only for registered users (pastes with user_id).
        
        Args:
            description: Optional description of the changes made
            
        Returns:
            The created PasteRevision object or None if not applicable
        """
        if not self.user_id:
            # Anonymous pastes don't have revisions
            return None
            
        # Get the next revision number
        next_revision = 1
        latest_revision = PasteRevision.query.filter_by(
            paste_id=self.id
        ).order_by(PasteRevision.revision_number.desc()).first()
        
        if latest_revision:
            next_revision = latest_revision.revision_number + 1
            
        # Create a new revision
        revision = PasteRevision(
            paste_id=self.id,
            content=self.content,
            title=self.title,
            syntax=self.syntax,
            revision_number=next_revision,
            edit_description=description
        )
        
        db.session.add(revision)
        db.session.commit()
        
        return revision
        
    def get_revisions(self):
        """
        Get all revisions of this paste, ordered by newest first.
        Only for registered users (pastes with user_id).
        
        Returns:
            A list of PasteRevision objects or empty list if not applicable
        """
        if not self.user_id:
            # Anonymous pastes don't have revisions
            return []
            
        return PasteRevision.query.filter_by(
            paste_id=self.id
        ).order_by(PasteRevision.revision_number.desc()).all()

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

    def fork(self, user_id=None, visibility='public'):
        """
        Create a fork of this paste
        
        Args:
            user_id: The ID of the user creating the fork (None for anonymous)
            visibility: The visibility of the forked paste
            
        Returns:
            The newly created fork (Paste object)
        """
        # Generate a unique short_id for the fork
        short_id = str(uuid.uuid4())[:8]
        
        # Create the fork
        fork = Paste(
            title=f"Fork of {self.title}",
            content=self.content,
            syntax=self.syntax,
            user_id=user_id,
            visibility=visibility,
            short_id=short_id,
            forked_from_id=self.id,
            comments_enabled=self.comments_enabled
        )
        
        # Calculate the size of the fork
        fork.calculate_size()
        
        # Increment the fork count of the original paste
        self.fork_count += 1
        
        # Add and commit
        db.session.add(fork)
        db.session.commit()
        
        # If the user is logged in, update their total pastes count
        if user_id:
            user = User.query.get(user_id)
            if user:
                user.total_pastes += 1
                db.session.commit()
        
        return fork
        
    def set_password(self, password):
        """Hash and store a password for password-protected pastes"""
        if not password:
            self.password_protected = False
            self.password_hash = None
            return
            
        self.password_protected = True
        self.password_hash = generate_password_hash(password)
        
    def check_password(self, password):
        """Verify the password for password-protected pastes"""
        if not self.password_protected or not self.password_hash:
            return True  # No password needed
            
        return check_password_hash(self.password_hash, password)
        
    def encrypt(self, password=None):
        """
        Encrypt the paste content
        
        Args:
            password (str, optional): Password to use for encryption. 
                                      If None, uses random key encryption.
        
        Returns:
            bool: Whether encryption was successful
        """
        if self.is_encrypted:
            # Already encrypted
            return True
            
        # Import locally to avoid circular imports
        from utils import encrypt_content
        
        # Encrypt the content
        encrypted_content, salt, method = encrypt_content(self.content, password)
        
        if encrypted_content is None:
            # Encryption failed
            return False
            
        # Store the encrypted content and metadata
        self.content = encrypted_content
        self.encryption_salt = salt
        self.encryption_method = method
        self.is_encrypted = True
        
        # If a password was provided, also set it
        if password:
            self.set_password(password)
            
        return True
        
    def decrypt(self, password=None):
        """
        Decrypt the paste content
        
        Args:
            password (str, optional): Password to use for decryption,
                                      if the paste is password-protected.
        
        Returns:
            str or None: The decrypted content or None if decryption failed
        """
        if not self.is_encrypted:
            # Not encrypted, return as is
            return self.content
            
        # Check password if needed
        if self.password_protected and not self.check_password(password):
            return None
            
        # Import locally to avoid circular imports
        from utils import decrypt_content
        
        # Decrypt the content
        method = self.encryption_method or 'fernet-random'
        decrypted_content = decrypt_content(
            self.content,
            self.encryption_salt,
            method,
            password
        )
        
        return decrypted_content
        
    def get_content(self, password=None):
        """
        Get the content, decrypting it if necessary
        
        Args:
            password (str, optional): Password to use for decryption,
                                      if the paste is password-protected.
        
        Returns:
            str or None: The content or None if decryption failed
        """
        if self.is_encrypted:
            return self.decrypt(password)
        else:
            return self.content
    
    def add_tags(self, tag_names):
        """
        Add tags to the paste
        
        Args:
            tag_names: List of tag names to add
        """
        if not tag_names:
            return
            
        for tag_name in tag_names:
            tag_name = tag_name.strip()
            if tag_name:
                tag = Tag.get_or_create(tag_name)
                if tag not in self.tags.all():
                    self.tags.append(tag)
        
        db.session.commit()
    
    def remove_tag(self, tag_name):
        """Remove a tag from the paste"""
        tag = Tag.query.filter(func.lower(Tag.name) == func.lower(tag_name)).first()
        if tag and tag in self.tags.all():
            self.tags.remove(tag)
            db.session.commit()
            
    def clear_tags(self):
        """Remove all tags from the paste"""
        for tag in self.tags.all():
            self.tags.remove(tag)
        db.session.commit()
    
    def get_tag_names(self):
        """Get a list of tag names for this paste"""
        return [tag.name for tag in self.tags.all()]
        
    def get_tags_with_counts(self):
        """Get a list of tags with their paste counts"""
        return [{'name': tag.name, 'count': tag.pastes.count()} for tag in self.tags.all()]
    
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
        # Debug the session information
        import logging
        logging.debug(f"Session data: {session}")
        
        # Check for existing viewer_id
        session_id = session.get('viewer_id')
        logging.debug(f"Current session viewer_id: {session_id}")
        
        # If no session ID, generate a new one
        if not session_id:
            # Create a UUID based partly on IP address to ensure consistency for the same user
            # But still with randomness to maintain privacy
            import hashlib
            hash_base = hashlib.md5(ip_address.encode()).hexdigest()[:8]
            viewer_id = f"{hash_base}-{str(uuid.uuid4())}"
            session['viewer_id'] = viewer_id
            logging.debug(f"Created new viewer_id: {viewer_id}")
            return viewer_id
            
        return session_id


class PasteRevision(db.Model):
    """
    Model for paste revisions, tracking the edit history of pastes.
    Only available for registered users.
    """
    __tablename__ = 'paste_revisions'
    
    id = db.Column(db.Integer, primary_key=True)
    paste_id = db.Column(db.Integer, db.ForeignKey('pastes.id'), nullable=False)
    content = db.Column(db.Text, nullable=False)
    title = db.Column(db.String(255), nullable=False)
    syntax = db.Column(db.String(50), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    revision_number = db.Column(db.Integer, nullable=False)
    edit_description = db.Column(db.String(255), nullable=True)
    
    # Relationship back to Paste
    paste = db.relationship('Paste', backref=db.backref('revisions', lazy='dynamic', order_by='PasteRevision.revision_number.desc()'))
    
    def __repr__(self):
        return f'<PasteRevision {self.revision_number} of paste {self.paste_id}>'


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
        
        
class PasteTemplate(db.Model):
    """
    Model for paste templates, providing common layouts and snippets for users.
    These templates can be selected when creating a new paste.
    """
    __tablename__ = 'paste_templates'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=True)
    content = db.Column(db.Text, nullable=False)
    syntax = db.Column(db.String(50), default='text')
    category = db.Column(db.String(50), default='General')
    is_public = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    usage_count = db.Column(db.Integer, default=0)
    
    # Relationship back to User (creator)
    author = db.relationship('User', backref=db.backref('created_templates', lazy='dynamic'))
    
    def __repr__(self):
        return f'<PasteTemplate {self.id}: {self.name}>'
        
    @staticmethod
    def get_public_templates():
        """Get all public templates"""
        return PasteTemplate.query.filter_by(is_public=True).order_by(PasteTemplate.name).all()
        
    @staticmethod
    def get_templates_by_category():
        """Get all public templates grouped by category"""
        templates = PasteTemplate.query.filter_by(is_public=True).order_by(
            PasteTemplate.category, PasteTemplate.name
        ).all()
        
        # Group templates by category
        categorized = {}
        for template in templates:
            if template.category not in categorized:
                categorized[template.category] = []
            categorized[template.category].append(template)
            
        return categorized
        
    def increment_usage(self):
        """Increment the usage count for this template"""
        self.usage_count += 1
        db.session.commit()


class Notification(db.Model):
    """
    Notification model for user notification system.
    Stores notifications for users about various events (comments, forks, mentions, etc.)
    """
    __tablename__ = 'notifications'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    sender_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    paste_id = db.Column(db.Integer, db.ForeignKey('pastes.id'), nullable=True)
    comment_id = db.Column(db.Integer, db.ForeignKey('comments.id'), nullable=True)
    type = db.Column(db.String(50), nullable=False)  # comment, fork, mention, system
    message = db.Column(db.Text, nullable=False)
    read = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    user = db.relationship('User', foreign_keys=[user_id], 
                           backref=db.backref('notifications', lazy='dynamic'))
    sender = db.relationship('User', foreign_keys=[sender_id], 
                             backref=db.backref('sent_notifications', lazy='dynamic'))
    paste = db.relationship('Paste', backref=db.backref('notifications', lazy='dynamic'))
    comment = db.relationship('Comment', backref=db.backref('notifications', lazy='dynamic'))
    
    def __repr__(self):
        return f'<Notification {self.id}: {self.type} for user {self.user_id}>'
    
    @staticmethod
    def create_notification(user_id, type, message, sender_id=None, paste_id=None, comment_id=None):
        """
        Create a new notification
        """
        notification = Notification(
            user_id=user_id,
            sender_id=sender_id,
            paste_id=paste_id,
            comment_id=comment_id,
            type=type,
            message=message
        )
        db.session.add(notification)
        db.session.commit()
        return notification
    
    @staticmethod
    def mark_as_read(notification_id):
        """
        Mark a notification as read
        """
        notification = Notification.query.get(notification_id)
        if notification:
            notification.read = True
            db.session.commit()
            return True
        return False
    
    @staticmethod
    def mark_all_as_read(user_id):
        """
        Mark all notifications for a user as read
        """
        Notification.query.filter_by(user_id=user_id, read=False).update({'read': True})
        db.session.commit()
        
    @staticmethod
    def get_unread_count(user_id):
        """
        Get the count of unread notifications for a user
        """
        return Notification.query.filter_by(user_id=user_id, read=False).count()


class FlaggedPaste(db.Model):
    """
    Model for storing flagged pastes that require admin review
    """
    __tablename__ = 'flagged_pastes'
    
    id = db.Column(db.Integer, primary_key=True)
    paste_id = db.Column(db.Integer, db.ForeignKey('pastes.id'), nullable=False)
    reporter_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)  # Can be null for system/AI flags
    reason = db.Column(db.String(100), nullable=False)  # spam, abuse, illegal, etc.
    details = db.Column(db.Text, nullable=True)
    status = db.Column(db.String(20), default='pending')  # pending, approved, rejected
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    reviewed_at = db.Column(db.DateTime, nullable=True)
    reviewed_by_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)  # Admin who reviewed it
    
    # Relationships
    paste = db.relationship('Paste', backref=db.backref('flags', lazy='dynamic'))
    reporter = db.relationship('User', foreign_keys=[reporter_id], backref=db.backref('reported_pastes', lazy='dynamic'))
    reviewed_by = db.relationship('User', foreign_keys=[reviewed_by_id], backref=db.backref('reviewed_pastes', lazy='dynamic'))
    
    def __repr__(self):
        return f'<FlaggedPaste {self.id} for paste {self.paste_id} reason={self.reason}>'
        
    @staticmethod
    def get_pending_count():
        """Get count of pastes pending review"""
        return FlaggedPaste.query.filter_by(status='pending').count()


class FlaggedComment(db.Model):
    """
    Model for storing flagged comments that require admin review
    """
    __tablename__ = 'flagged_comments'
    
    id = db.Column(db.Integer, primary_key=True)
    comment_id = db.Column(db.Integer, db.ForeignKey('comments.id'), nullable=False)
    reporter_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)  # Can be null for system flags
    reason = db.Column(db.String(100), nullable=False)  # spam, abuse, illegal, etc.
    details = db.Column(db.Text, nullable=True)
    status = db.Column(db.String(20), default='pending')  # pending, approved, rejected
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    reviewed_at = db.Column(db.DateTime, nullable=True)
    reviewed_by_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)  # Admin who reviewed it
    
    # Relationships
    comment = db.relationship('Comment', backref=db.backref('flags', lazy='dynamic'))
    reporter = db.relationship('User', foreign_keys=[reporter_id], backref=db.backref('reported_comments', lazy='dynamic'))
    reviewed_by = db.relationship('User', foreign_keys=[reviewed_by_id], backref=db.backref('reviewed_comments', lazy='dynamic'))
    
    def __repr__(self):
        return f'<FlaggedComment {self.id} for comment {self.comment_id} reason={self.reason}>'
        
    @staticmethod
    def get_pending_count():
        """Get count of comments pending review"""
        return FlaggedComment.query.filter_by(status='pending').count()


class AuditLog(db.Model):
    """
    Model for recording admin actions for auditing purposes
    """
    __tablename__ = 'audit_logs'
    
    id = db.Column(db.Integer, primary_key=True)
    admin_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    action = db.Column(db.String(100), nullable=False)  # ban_user, delete_paste, etc.
    entity_type = db.Column(db.String(50), nullable=False)  # user, paste, comment, etc.
    entity_id = db.Column(db.Integer, nullable=False)  # ID of the affected entity
    details = db.Column(db.Text, nullable=True)  # Additional details about the action
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    ip_address = db.Column(db.String(45), nullable=True)  # IPv6 can be up to 45 chars
    
    # Relationship back to the admin user
    admin = db.relationship('User', backref=db.backref('audit_logs', lazy='dynamic'))
    
    def __repr__(self):
        return f'<AuditLog {self.id} {self.action} on {self.entity_type}:{self.entity_id} by {self.admin_id}>'
        
    @staticmethod
    def log(admin_id, action, entity_type, entity_id, details=None, ip_address=None):
        """Create a new audit log entry"""
        log_entry = AuditLog(
            admin_id=admin_id,
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            details=details,
            ip_address=ip_address
        )
        db.session.add(log_entry)
        db.session.commit()
        return log_entry


class SiteSettings(db.Model):
    """
    Model for storing site-wide settings configurable by admins
    """
    __tablename__ = 'site_settings'
    
    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(100), unique=True, nullable=False)
    value = db.Column(db.Text, nullable=True)
    value_type = db.Column(db.String(20), default='string')  # string, integer, boolean, json
    description = db.Column(db.Text, nullable=True)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    updated_by_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    
    # Relationship back to the admin who updated it
    updated_by = db.relationship('User', backref=db.backref('updated_settings', lazy='dynamic'))
    
    @classmethod
    def get(cls, key, default=None):
        """Get a setting value by key"""
        setting = cls.query.filter_by(key=key).first()
        if not setting:
            return default
            
        # Convert value based on type
        if setting.value_type == 'integer':
            return int(setting.value)
        elif setting.value_type == 'boolean':
            return setting.value.lower() in ('true', '1', 'yes')
        elif setting.value_type == 'json':
            import json
            return json.loads(setting.value)
        else:
            return setting.value
            
    @classmethod
    def set(cls, key, value, value_type='string', description=None, updated_by_id=None):
        """Set a setting value by key"""
        import json
        # Convert value based on type
        if value_type == 'json' and not isinstance(value, str):
            value = json.dumps(value)
        elif value_type == 'boolean' and isinstance(value, bool):
            value = str(value).lower()
        elif value_type == 'integer':
            value = str(int(value))
            
        setting = cls.query.filter_by(key=key).first()
        if setting:
            setting.value = value
            setting.value_type = value_type
            if description:
                setting.description = description
            if updated_by_id:
                setting.updated_by_id = updated_by_id
        else:
            setting = cls(
                key=key, 
                value=value, 
                value_type=value_type, 
                description=description,
                updated_by_id=updated_by_id
            )
            db.session.add(setting)
            
        db.session.commit()
        return setting
