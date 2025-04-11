"""
Script to add ban and shadowban columns to the users table.

This should be run as a one-time migration.
"""

import os
import sys
from datetime import datetime

# Add the parent directory to the Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import database models
from app import app, db
import sqlalchemy as sa
from sqlalchemy.exc import OperationalError


def add_user_ban_columns():
    """Add ban and shadowban columns to users table"""
    print("Adding ban and shadowban columns to users table...")
    
    with app.app_context():
        try:
            # Check if the columns already exist
            inspector = sa.inspect(db.engine)
            columns = [col['name'] for col in inspector.get_columns('users')]
            
            if 'is_banned' not in columns:
                # Add is_banned column
                db.session.execute(sa.text(
                    "ALTER TABLE users ADD COLUMN is_banned BOOLEAN NOT NULL DEFAULT FALSE"
                ))
                print("Added 'is_banned' column")
            else:
                print("Column 'is_banned' already exists")
                
            if 'is_shadowbanned' not in columns:
                # Add is_shadowbanned column
                db.session.execute(sa.text(
                    "ALTER TABLE users ADD COLUMN is_shadowbanned BOOLEAN NOT NULL DEFAULT FALSE"
                ))
                print("Added 'is_shadowbanned' column")
            else:
                print("Column 'is_shadowbanned' already exists")
                
            if 'ban_reason' not in columns:
                # Add ban_reason column
                db.session.execute(sa.text(
                    "ALTER TABLE users ADD COLUMN ban_reason TEXT"
                ))
                print("Added 'ban_reason' column")
            else:
                print("Column 'ban_reason' already exists")
                
            if 'banned_until' not in columns:
                # Add banned_until column
                db.session.execute(sa.text(
                    "ALTER TABLE users ADD COLUMN banned_until TIMESTAMP"
                ))
                print("Added 'banned_until' column")
            else:
                print("Column 'banned_until' already exists")
            
            # Commit the changes
            db.session.commit()
            print("Migration completed successfully!")
            
        except OperationalError as e:
            print(f"Error: {e}")
            db.session.rollback()
            return False
            
    return True


def main():
    """Main entry point for the script."""
    print("Starting migration...")
    if add_user_ban_columns():
        print("Migration completed successfully!")
    else:
        print("Migration failed!")


if __name__ == "__main__":
    main()