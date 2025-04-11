#!/usr/bin/env python3
"""
Script to add notifications table to the database.

This should be run as a one-time migration.
"""
import os
import sys
from datetime import datetime

import sqlalchemy as sa
from sqlalchemy import inspect, text
from sqlalchemy.exc import SQLAlchemyError

# Add the parent directory to the path so we can import the app
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import app, db


def add_notifications_table():
    """Add notifications table to the database"""
    try:
        # Create a SQLAlchemy Inspector to check for existing tables
        inspector = inspect(db.engine)
        
        # Check if the notifications table already exists
        if 'notifications' in inspector.get_table_names():
            print("The notifications table already exists.")
            return True
            
        # Define the SQL for creating the notifications table
        sql = """
        CREATE TABLE notifications (
            id SERIAL PRIMARY KEY,
            user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            sender_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
            paste_id INTEGER REFERENCES pastes(id) ON DELETE CASCADE,
            comment_id INTEGER REFERENCES comments(id) ON DELETE CASCADE,
            type VARCHAR(50) NOT NULL,
            message TEXT NOT NULL,
            read BOOLEAN DEFAULT FALSE,
            created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT NOW()
        );
        CREATE INDEX idx_notifications_user_id ON notifications(user_id);
        CREATE INDEX idx_notifications_read ON notifications(read);
        """
        
        # Execute the SQL
        with db.engine.connect() as conn:
            conn.execute(text(sql))
            conn.commit()
            
        print("Successfully added notifications table.")
        return True
        
    except SQLAlchemyError as e:
        print(f"SQLAlchemy error: {e}")
        return False
    except Exception as e:
        print(f"Error: {e}")
        return False


def main():
    """Main entry point for the script."""
    with app.app_context():
        print("Starting migration: add notifications table")
        
        result = add_notifications_table()
        
        if result:
            print("Migration completed successfully.")
        else:
            print("Migration failed! See above for details.")
            sys.exit(1)


if __name__ == "__main__":
    main()