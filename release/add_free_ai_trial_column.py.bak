#!/usr/bin/env python3
"""
Script to add free_ai_trials_used column to the users table.

This should be run as a one-time migration.
"""

import os
import sys
from datetime import datetime, timedelta

try:
    # Try to import from app to use existing db connection
    from app import db
    print("Successfully imported db from app")
except ImportError:
    print("Could not import db from app, trying direct SQLAlchemy connection")
    import sqlalchemy as sa
    from sqlalchemy import create_engine, Column, Integer, MetaData, Table
    from sqlalchemy.exc import SQLAlchemyError
    
    # Get database URL from environment variable
    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        print("Error: DATABASE_URL environment variable not set")
        sys.exit(1)
        
    # Create engine and connect to the database
    try:
        engine = create_engine(database_url)
        connection = engine.connect()
        metadata = MetaData()
        print(f"Connected to database at {database_url}")
    except SQLAlchemyError as e:
        print(f"Error connecting to database: {e}")
        sys.exit(1)


def add_free_ai_trial_column():
    """Add free_ai_trials_used column to users table"""
    try:
        # Try using Flask-SQLAlchemy
        from app import db
        
        # Check if column already exists in the database
        with db.engine.connect() as conn:
            # Check if column exists
            result = conn.execute(db.text(
                "SELECT column_name FROM information_schema.columns WHERE table_name = 'users' AND column_name = 'free_ai_trials_used'"
            ))
            if result.fetchone():
                print("Column 'free_ai_trials_used' already exists in the users table")
                return
        
            # Add the column if it doesn't exist
            conn.execute(db.text('ALTER TABLE users ADD COLUMN free_ai_trials_used INTEGER DEFAULT 0'))
            conn.commit()
            
        print("Successfully added 'free_ai_trials_used' column to users table")
        
    except (ImportError, Exception) as e:
        print(f"Error using Flask-SQLAlchemy: {e}")
        print("Falling back to raw SQLAlchemy")
        
        try:
            # Use raw SQLAlchemy
            import sqlalchemy as sa
            from sqlalchemy import inspect
            
            engine = sa.create_engine(os.environ.get("DATABASE_URL"))
            insp = inspect(engine)
            
            # Check if column already exists
            columns = [c['name'] for c in insp.get_columns('users')]
            if 'free_ai_trials_used' in columns:
                print("Column 'free_ai_trials_used' already exists in the users table")
                return
                
            # Add the column
            with engine.connect() as conn:
                conn.execute(sa.text('ALTER TABLE users ADD COLUMN free_ai_trials_used INTEGER DEFAULT 0'))
                
            print("Successfully added 'free_ai_trials_used' column to users table")
            
        except Exception as e:
            print(f"Error adding column using raw SQLAlchemy: {e}")
            sys.exit(1)


def main():
    """Main entry point for the script."""
    print("Starting migration to add free AI trial usage column...")
    
    try:
        add_free_ai_trial_column()
        print("Migration completed successfully.")
    except Exception as e:
        print(f"Migration failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()