"""
MySQL Configuration Script

This script updates the application to use MySQL instead of PostgreSQL
and initializes the database tables.

Usage:
    python mysql_config.py
"""
import os
import sys
import pymysql

# MySQL Database configuration
DB_CONFIG = {
    'host': '185.212.71.204',
    'user': 'u213077714_flaskbin',
    'password': 'hOJ27K?5',
    'database': 'u213077714_flaskbin',
    'port': 3306
}

# The MySQL connection string to use in the application
MYSQL_CONNECTION_STRING = f"mysql+pymysql://{DB_CONFIG['user']}:{DB_CONFIG['password']}@{DB_CONFIG['host']}:{DB_CONFIG['port']}/{DB_CONFIG['database']}"

def check_database_connection():
    """Verify that we can connect to the MySQL database."""
    print(f"Connecting to MySQL database at {DB_CONFIG['host']}...")
    try:
        conn = pymysql.connect(
            host=DB_CONFIG['host'],
            user=DB_CONFIG['user'],
            password=DB_CONFIG['password'],
            database=DB_CONFIG['database'],
            port=DB_CONFIG['port']
        )
        conn.close()
        print("✅ Database connection successful!")
        return True
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        return False

def create_env_file():
    """Create a .env file with the correct MySQL database URL."""
    env_content = f"""# Environment variables for FlaskBin
DATABASE_URL="{MYSQL_CONNECTION_STRING}"
SESSION_SECRET="your-secure-session-secret-replace-in-production"
"""
    
    try:
        with open('.env', 'w') as f:
            f.write(env_content)
        print("✅ Created .env file with MySQL configuration")
        return True
    except Exception as e:
        print(f"❌ Failed to create .env file: {e}")
        return False

def update_wsgi_file():
    """Update the wsgi.py file to use MySQL instead of PostgreSQL."""
    wsgi_path = 'wsgi.py'
    
    # Check if file exists
    if not os.path.exists(wsgi_path):
        print(f"❌ File {wsgi_path} not found")
        return False
    
    try:
        # Read current content
        with open(wsgi_path, 'r') as f:
            content = f.read()
        
        # Replace PostgreSQL with MySQL in the content
        if 'SQLALCHEMY_DATABASE_URI' in content:
            # The file already has database configuration, update it
            modified_content = content.replace(
                'SQLALCHEMY_DATABASE_URI=os.environ.get("DATABASE_URL", "sqlite:///pastebin.db")',
                f'SQLALCHEMY_DATABASE_URI=os.environ.get("DATABASE_URL", "{MYSQL_CONNECTION_STRING}")'
            )
            
            # Add pymysql import
            if 'import pymysql' not in modified_content:
                modified_content = 'import pymysql\n' + modified_content
            
            # Write the modified content back
            with open(wsgi_path, 'w') as f:
                f.write(modified_content)
                
            print(f"✅ Updated {wsgi_path} to use MySQL")
            return True
        else:
            print(f"⚠️ Could not find database configuration in {wsgi_path}")
            return False
    except Exception as e:
        print(f"❌ Failed to update {wsgi_path}: {e}")
        return False

def create_init_db_script():
    """Create a script to initialize the database tables."""
    init_db_script = """#!/usr/bin/env python
'''
Initialize Database Tables

This script creates all database tables defined in the models.
Run this script once before starting the application.
'''
import os
import sys
import pymysql
from flask import Flask
from flask_sqlalchemy import SQLAlchemy

# Create a minimal Flask app
app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get(
    'DATABASE_URL', 
    'mysql+pymysql://u213077714_flaskbin:hOJ27K?5@185.212.71.204:3306/u213077714_flaskbin'
)
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Initialize SQLAlchemy
db = SQLAlchemy(app)

# Import and define model classes
from datetime import datetime, timedelta
import uuid
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

class User(UserMixin, db.Model):
    '''User model for authentication and profile information.'''
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
    '''Paste model for storing code snippets and text.'''
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
    '''Tracks individual views of pastes.'''
    __tablename__ = 'paste_views'
    
    id = db.Column(db.Integer, primary_key=True)
    paste_id = db.Column(db.Integer, db.ForeignKey('pastes.id'), nullable=False)
    viewer_ip = db.Column(db.String(64))
    user_agent = db.Column(db.String(256))
    viewed_at = db.Column(db.DateTime, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))

class Comment(db.Model):
    '''Comments on pastes.'''
    __tablename__ = 'comments'
    
    id = db.Column(db.Integer, primary_key=True)
    paste_id = db.Column(db.Integer, db.ForeignKey('pastes.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    content = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_deleted = db.Column(db.Boolean, default=False)
    parent_id = db.Column(db.Integer, db.ForeignKey('comments.id'))

class PasteRevision(db.Model):
    '''Revision history for pastes.'''
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
    '''User notifications.'''
    __tablename__ = 'notifications'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    content = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_read = db.Column(db.Boolean, default=False)
    notification_type = db.Column(db.String(20), nullable=False)
    related_id = db.Column(db.Integer)

class PasteCollection(db.Model):
    '''Collections for organizing pastes.'''
    __tablename__ = 'paste_collections'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_public = db.Column(db.Boolean, default=True)

class Tag(db.Model):
    '''Tags for categorizing pastes.'''
    __tablename__ = 'tags'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False, unique=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class PasteTag(db.Model):
    '''Association table for paste-tag many-to-many relationship.'''
    __tablename__ = 'paste_tags'
    
    paste_id = db.Column(db.Integer, db.ForeignKey('pastes.id'), primary_key=True)
    tag_id = db.Column(db.Integer, db.ForeignKey('tags.id'), primary_key=True)

class FlaggedPaste(db.Model):
    '''Reports of inappropriate pastes.'''
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
    '''Reports of inappropriate comments.'''
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

def init_db():
    '''Initialize database tables.'''
    print("Creating all database tables...")
    try:
        db.create_all()
        print("✅ Database tables created successfully!")
        
        # Check if admin user exists
        admin = User.query.filter_by(username='admin').first()
        if not admin:
            print("Creating admin user...")
            admin = User(
                username='admin',
                email='admin@example.com',
                password_hash=generate_password_hash('admin'),
                is_admin=True
            )
            db.session.add(admin)
            db.session.commit()
            print("✅ Admin user created.")
        
        return True
    except Exception as e:
        print(f"❌ Failed to create database tables: {e}")
        return False

if __name__ == '__main__':
    print("=" * 60)
    print("DATABASE INITIALIZATION")
    print("=" * 60)
    
    success = init_db()
    
    if success:
        print("\n✅ Database initialized successfully!")
        print("\nYou can now start the application with:")
        print("  flask run")
        print("  or")
        print("  gunicorn --bind 0.0.0.0:5000 wsgi:app")
    else:
        print("\n❌ Database initialization failed.")
        sys.exit(1)
"""
    
    try:
        with open('init_db.py', 'w') as f:
            f.write(init_db_script)
        os.chmod('init_db.py', 0o755)  # Make executable
        print("✅ Created init_db.py script")
        return True
    except Exception as e:
        print(f"❌ Failed to create init_db.py: {e}")
        return False

def create_requirements_file():
    """Create or update requirements.txt to include pymysql."""
    requirements = """
bleach==6.0.0
email-validator==2.0.0
Flask==2.3.3
Flask-Login==0.6.2
Flask-SQLAlchemy==3.0.5
Flask-WTF==1.1.1
gunicorn==23.0.0
psycopg2-binary==2.9.9
Pygments==2.16.1
pymysql==1.1.0
python-dotenv==1.0.0
SQLAlchemy==2.0.19
Werkzeug==2.3.7
WTForms==3.0.1
"""
    
    try:
        with open('requirements.txt', 'w') as f:
            f.write(requirements)
        print("✅ Updated requirements.txt with pymysql")
        return True
    except Exception as e:
        print(f"❌ Failed to update requirements.txt: {e}")
        return False

def main():
    """Main function."""
    print("\n" + "="*60)
    print("MYSQL CONFIGURATION SETUP")
    print("="*60)
    
    # Check database connection
    if not check_database_connection():
        print("\n❌ Cannot proceed without database connection.")
        sys.exit(1)
    
    # Create .env file with MySQL configuration
    create_env_file()
    
    # Update wsgi.py to use MySQL
    update_wsgi_file()
    
    # Create init_db.py script
    create_init_db_script()
    
    # Update requirements.txt
    create_requirements_file()
    
    print("\n" + "="*60)
    print("SETUP COMPLETE")
    print("="*60)
    print("\nNext steps:")
    print("1. Run the database initialization script:")
    print("   python init_db.py")
    print("\n2. Start the application:")
    print("   gunicorn --bind 0.0.0.0:5000 wsgi:app")
    print("\nThe MySQL database URL is:")
    print(f"  {MYSQL_CONNECTION_STRING}")

if __name__ == "__main__":
    main()