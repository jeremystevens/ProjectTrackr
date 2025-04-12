#!/usr/bin/env python3
"""
Script to add burn_after_read column to the pastes table.

This should be run as a one-time migration.
"""
import os
import sys
from app import app, db
from sqlalchemy import Column, Boolean
from sqlalchemy.exc import OperationalError, ProgrammingError

def add_burn_after_read_column():
    """Add burn_after_read column to pastes table"""
    with app.app_context():
        try:
            # Check if the column already exists
            inspector = db.inspect(db.engine)
            columns = [col['name'] for col in inspector.get_columns('pastes')]
            
            if 'burn_after_read' not in columns:
                # Add the column using SQLAlchemy Core
                from sqlalchemy import text
                sql = text("ALTER TABLE pastes ADD COLUMN burn_after_read TINYINT(1) DEFAULT FALSE")
                db.session.execute(sql)
                db.session.commit()
                print("Successfully added burn_after_read column to pastes table")
            else:
                print("burn_after_read column already exists")
                
            return True
        except (OperationalError, ProgrammingError) as e:
            print(f"Error: {e}")
            return False

def main():
    """Main entry point for the script."""
    if not add_burn_after_read_column():
        sys.exit(1)
        
    print("Migration completed successfully.")
    
if __name__ == "__main__":
    main()