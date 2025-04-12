#!/usr/bin/env python3
"""
Script to add administrator dashboard tables to the database.

This should be run as a one-time migration.
"""
import os
import sys
from datetime import datetime

# Add the project directory to the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from sqlalchemy import create_engine, MetaData, Table, Column, Integer, String, Text, Boolean, DateTime, ForeignKey, text
    from sqlalchemy.exc import SQLAlchemyError
except ImportError:
    print("SQLAlchemy is required. Please install it first.")
    sys.exit(1)

def add_admin_tables():
    """Add all admin-related tables to the database"""
    # Get database connection string from environment variable
    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        print("DATABASE_URL environment variable is not set.")
        sys.exit(1)

    # Create SQLAlchemy engine
    engine = create_engine(database_url)
    metadata = MetaData()
    
    # Initialize conn and trans to None to handle the unbound warning
    conn = None
    trans = None

    try:
        # Add is_admin and is_premium columns to users table if they don't exist
        conn = engine.connect()
        trans = conn.begin()

        # Check if is_admin column exists in users table
        result = conn.execute(text("SELECT column_name FROM information_schema.columns WHERE table_name='users' AND column_name='is_admin';"))
        if result.rowcount == 0:
            print("Adding is_admin column to users table...")
            conn.execute(text("ALTER TABLE users ADD COLUMN is_admin TINYINT(1) DEFAULT FALSE;"))
        
        # Check if is_premium column exists in users table
        result = conn.execute(text("SELECT column_name FROM information_schema.columns WHERE table_name='users' AND column_name='is_premium';"))
        if result.rowcount == 0:
            print("Adding is_premium column to users table...")
            conn.execute(text("ALTER TABLE users ADD COLUMN is_premium TINYINT(1) DEFAULT FALSE;"))

        # Create flagged_pastes table if it doesn't exist
        print("Creating flagged_pastes table...")
        flagged_pastes = Table(
            'flagged_pastes',
            metadata,
            Column('id', Integer, primary_key=True),
            Column('paste_id', Integer, ForeignKey('pastes.id'), nullable=False),
            Column('reporter_id', Integer, ForeignKey('users.id'), nullable=True),
            Column('reason', String(100), nullable=False),
            Column('details', Text, nullable=True),
            Column('status', String(20), default='pending'),
            Column('created_at', DateTime, default=datetime.utcnow),
            Column('reviewed_at', DateTime, nullable=True),
            Column('reviewed_by_id', Integer, ForeignKey('users.id'), nullable=True),
        )

        # Create flagged_comments table if it doesn't exist
        print("Creating flagged_comments table...")
        flagged_comments = Table(
            'flagged_comments',
            metadata,
            Column('id', Integer, primary_key=True),
            Column('comment_id', Integer, ForeignKey('comments.id'), nullable=False),
            Column('reporter_id', Integer, ForeignKey('users.id'), nullable=True),
            Column('reason', String(100), nullable=False),
            Column('details', Text, nullable=True),
            Column('status', String(20), default='pending'),
            Column('created_at', DateTime, default=datetime.utcnow),
            Column('reviewed_at', DateTime, nullable=True),
            Column('reviewed_by_id', Integer, ForeignKey('users.id'), nullable=True),
        )

        # Create audit_logs table if it doesn't exist
        print("Creating audit_logs table...")
        audit_logs = Table(
            'audit_logs',
            metadata,
            Column('id', Integer, primary_key=True),
            Column('admin_id', Integer, ForeignKey('users.id'), nullable=False),
            Column('action', String(100), nullable=False),
            Column('entity_type', String(50), nullable=False),
            Column('entity_id', Integer, nullable=False),
            Column('details', Text, nullable=True),
            Column('created_at', DateTime, default=datetime.utcnow),
            Column('ip_address', String(45), nullable=True),
        )

        # Create site_settings table if it doesn't exist
        print("Creating site_settings table...")
        site_settings = Table(
            'site_settings',
            metadata,
            Column('id', Integer, primary_key=True),
            Column('key', String(100), unique=True, nullable=False),
            Column('value', Text, nullable=True),
            Column('value_type', String(20), default='string'),
            Column('description', Text, nullable=True),
            Column('updated_at', DateTime, default=datetime.utcnow),
            Column('updated_by_id', Integer, ForeignKey('users.id'), nullable=True),
        )

        # Create all tables
        metadata.create_all(engine, tables=[flagged_pastes, flagged_comments, audit_logs, site_settings])
        trans.commit()
        print("Successfully added admin tables to the database.")

    except SQLAlchemyError as e:
        print(f"Error adding admin tables: {e}")
        if trans:
            trans.rollback()
        sys.exit(1)
    finally:
        if conn:
            conn.close()
        engine.dispose()

def main():
    """Main entry point for the script."""
    add_admin_tables()

if __name__ == "__main__":
    main()