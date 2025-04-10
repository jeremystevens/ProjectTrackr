#!/usr/bin/env python3
"""
Script to add fork functionality columns to the pastes table.

This should be run as a one-time migration.
"""

import os
import sys
import sqlalchemy
from sqlalchemy import create_engine, MetaData, Table, Column, Integer, ForeignKey
from sqlalchemy.exc import OperationalError

DATABASE_URL = os.environ.get("DATABASE_URL")

def add_paste_fork_columns():
    """Add fork functionality columns to pastes table"""
    if not DATABASE_URL:
        print("Error: DATABASE_URL environment variable is not set.")
        sys.exit(1)

    print("\nAdding fork columns to pastes table...")

    # Connect to the database
    try:
        engine = create_engine(DATABASE_URL)
        metadata = MetaData()
        pastes = Table('pastes', metadata, autoload_with=engine)
        
        # Check if columns already exist
        column_names = [c.name for c in pastes.columns]
        
        # Add forked_from_id column if it doesn't exist
        if 'forked_from_id' not in column_names:
            print("Adding forked_from_id column...")
            
            # Create the forked_from_id column
            command = f"""
            ALTER TABLE pastes 
            ADD COLUMN forked_from_id INTEGER,
            ADD CONSTRAINT fk_paste_forked_from 
            FOREIGN KEY (forked_from_id) REFERENCES pastes(id) ON DELETE SET NULL;
            """
            
            with engine.connect() as conn:
                conn.execute(sqlalchemy.text(command))
                conn.commit()
            
            print("forked_from_id column added.")
        else:
            print("forked_from_id column already exists.")
            
        # Add fork_count column if it doesn't exist
        if 'fork_count' not in column_names:
            print("Adding fork_count column...")
            
            # Create the fork_count column
            command = """
            ALTER TABLE pastes 
            ADD COLUMN fork_count INTEGER DEFAULT 0 NOT NULL;
            """
            
            with engine.connect() as conn:
                conn.execute(sqlalchemy.text(command))
                conn.commit()
            
            print("fork_count column added.")
        else:
            print("fork_count column already exists.")
            
        print("Migration completed successfully.\n")
        
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)

def main():
    """Main entry point for the script."""
    add_paste_fork_columns()

if __name__ == "__main__":
    main()
