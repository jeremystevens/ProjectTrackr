"""
User models for the application.

This module contains the User model and related models like PasswordResetToken.
"""

from datetime import datetime, timedelta
import hashlib
import secrets
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

from model_package.base import db

# Track if models have been registered
_USER_MODEL_REGISTERED = False

class AltUser(UserMixin, db.Model):
    """User model for authentication and profile management"""
    __tablename__ = 'alt_users'
    
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

    def set_password(self, password):
        """Set the user's password (hashed)"""
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        """Verify the user's password"""
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
        """Get the user's avatar URL from Gravatar"""
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
    
    # Define the relationship on this side too for bidirectional access
    user = db.relationship('User', back_populates='password_reset_tokens')
    
    def is_expired(self):
        """Check if the token has expired"""
        return self.expires_at < datetime.utcnow()
        
    def __repr__(self):
        return f'<PasswordResetToken user_id={self.user_id}>'

# Update the User model to establish the bidirectional relationship
User.password_reset_tokens = db.relationship('PasswordResetToken', back_populates='user', lazy='dynamic', cascade='all, delete-orphan')


def register_user_models():
    """Mark user models as registered to prevent duplicate registration"""
    global _USER_MODEL_REGISTERED
    _USER_MODEL_REGISTERED = True

def are_user_models_registered():
    """Check if user models have been registered"""
    return _USER_MODEL_REGISTERED