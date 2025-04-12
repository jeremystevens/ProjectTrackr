#!/usr/bin/env python
"""
Fixed Database Initialization Script

This script properly initializes the MySQL database tables with correct application context handling.
"""
import os
import sys
import pymysql
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash

# Database connection parameters
DB_CONFIG = {
    'host': '185.212.71.204',
    'user': 'u213077714_flaskbin',
    'password': 'hOJ27K?5',
    'database': 'u213077714_flaskbin',
    'port': 3306
}

# MySQL connection string
MYSQL_CONNECTION_STRING = f"mysql+pymysql://{DB_CONFIG['user']}:{DB_CONFIG['password']}@{DB_CONFIG['host']}:{DB_CONFIG['port']}/{DB_CONFIG['database']}"

def create_app():
    """Create a minimal Flask application for database initialization."""
    app = Flask(__name__)
    app.config['SQLALCHEMY_DATABASE_URI'] = MYSQL_CONNECTION_STRING
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    
    # Initialize SQLAlchemy
    db = SQLAlchemy(app)
    
    # Define models inside the application context
    from datetime import datetime, timedelta
    from flask_login import UserMixin
    
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
    
    class PasteView(db.Model):
        """Tracks individual views of pastes."""
        __tablename__ = 'paste_views'
        
        id = db.Column(db.Integer, primary_key=True)
        paste_id = db.Column(db.Integer, db.ForeignKey('pastes.id'), nullable=False)
        viewer_ip = db.Column(db.String(64))
        user_agent = db.Column(db.String(256))
        viewed_at = db.Column(db.DateTime, default=datetime.utcnow)
        user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    
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
    
    class PasteCollection(db.Model):
        """Collections for organizing pastes."""
        __tablename__ = 'paste_collections'
        
        id = db.Column(db.Integer, primary_key=True)
        name = db.Column(db.String(100), nullable=False)
        description = db.Column(db.Text)
        user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
        created_at = db.Column(db.DateTime, default=datetime.utcnow)
        is_public = db.Column(db.Boolean, default=True)
    
    class Tag(db.Model):
        """Tags for categorizing pastes."""
        __tablename__ = 'tags'
        
        id = db.Column(db.Integer, primary_key=True)
        name = db.Column(db.String(50), nullable=False, unique=True)
        created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    class PasteTag(db.Model):
        """Association table for paste-tag many-to-many relationship."""
        __tablename__ = 'paste_tags'
        
        paste_id = db.Column(db.Integer, db.ForeignKey('pastes.id'), primary_key=True)
        tag_id = db.Column(db.Integer, db.ForeignKey('tags.id'), primary_key=True)
    
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
    
    return app, db, User

def init_database():
    """Initialize the database with all tables and an admin user."""
    print("=" * 60)
    print("DATABASE INITIALIZATION")
    print("=" * 60)
    
    # First, check the connection
    try:
        conn = pymysql.connect(
            host=DB_CONFIG['host'],
            user=DB_CONFIG['user'],
            password=DB_CONFIG['password'],
            database=DB_CONFIG['database'],
            port=DB_CONFIG['port'],
            connect_timeout=5
        )
        conn.close()
        print("✅ Database connection verified")
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        sys.exit(1)
    
    # Create app and initialize database
    app, db, User = create_app()
    
    with app.app_context():
        try:
            print("\nCreating all database tables...")
            db.create_all()
            print("✅ Database tables created successfully!")
            
            # Create admin user
            print("\nCreating admin user...")
            admin = User.query.filter_by(username='admin').first()
            if not admin:
                admin = User(
                    username='admin',
                    email='admin@example.com',
                    password_hash=generate_password_hash('admin'),
                    is_admin=True
                )
                db.session.add(admin)
                db.session.commit()
                print("✅ Admin user created with username 'admin' and password 'admin'")
            else:
                print("⚠️ Admin user already exists, skipping creation")
            
            print("\n✅ Database initialization complete!")
            print("\nYou can now update your application to use this MySQL connection string:")
            print(f"DATABASE_URL={MYSQL_CONNECTION_STRING}")
            
            return True
        except Exception as e:
            print(f"\n❌ Error initializing database: {e}")
            return False

if __name__ == "__main__":
    success = init_database()
    if not success:
        sys.exit(1)