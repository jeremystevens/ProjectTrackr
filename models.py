from datetime import datetime, timedelta
import hashlib
import uuid
from app import db
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
    
    # Relationships
    pastes = db.relationship('Paste', backref='author', lazy='dynamic', cascade='all, delete-orphan')
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
    
    def get_avatar_url(self, size=80):
        email_hash = hashlib.md5(self.email.lower().encode()).hexdigest()
        return f"https://www.gravatar.com/avatar/{email_hash}?s={size}&d=identicon"
    
    def __repr__(self):
        return f'<User {self.username}>'

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
    
    def is_expired(self):
        if self.expires_at is None:
            return False
        return datetime.utcnow() > self.expires_at
    
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
        now = datetime.utcnow()
        
        if expiry_option == '0':
            return None  # Never expires
        elif expiry_option == '1':
            # Exactly 10 minutes from now
            return now + timedelta(minutes=10)  # 10 minutes
        elif expiry_option == '2':
            return now + timedelta(hours=1)  # 1 hour
        elif expiry_option == '3':
            return now + timedelta(days=1)  # 1 day
        elif expiry_option == '4':
            return now + timedelta(days=30)  # 1 month
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
