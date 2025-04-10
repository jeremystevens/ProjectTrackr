#!/usr/bin/env python3
"""
Script to add paste_revisions table to the database.

This should be run as a one-time migration.
"""

import sys
import os
import logging
from sqlalchemy import text, inspect
from sqlalchemy.exc import SQLAlchemyError

# Add the current directory to the path so we can import the app
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

try:
    from app import db
    from models import PasteRevision
except ImportError as e:
    print(f"Error importing required modules: {e}")
    sys.exit(1)

def add_paste_revisions_table():
    """Add paste_revisions table to the database"""
    inspector = inspect(db.engine)
    
    # Check if the table already exists
    if 'paste_revisions' in inspector.get_table_names():
        print("paste_revisions table already exists. Skipping.")
        return False
        
    try:
        # Create the table using the model
        PasteRevision.__table__.create(db.engine)
        print("Successfully created paste_revisions table")
        return True
    except SQLAlchemyError as e:
        print(f"Error creating paste_revisions table: {e}")
        return False

def main():
    """Main entry point for the script."""
    print("Starting migration: Adding paste_revisions table...")
    
    from app import app
    with app.app_context():
        result = add_paste_revisions_table()
    
    if result:
        print("Migration completed successfully")
    else:
        print("Migration finished with errors or was skipped")

if __name__ == "__main__":
    main()