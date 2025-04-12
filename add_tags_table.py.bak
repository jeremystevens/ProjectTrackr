#!/usr/bin/env python3
"""
Script to add tags table and paste_tags association table to the database.

This should be run as a one-time migration.
"""
import os
import sys
import sqlalchemy
from sqlalchemy import create_engine, MetaData, Table, Column, Integer, String, DateTime, ForeignKey, Boolean, Text
from datetime import datetime

# Database URL from environment
DATABASE_URL = os.environ.get('DATABASE_URL')

def add_tags_table():
    """Add tags table and paste_tags association table to the database"""
    try:
        # Create the database engine
        engine = create_engine(DATABASE_URL)
        
        # Create a metadata instance
        metadata = MetaData()
        
        # Reflect existing tables
        metadata.reflect(bind=engine)
        
        # Check if tags table already exists
        if 'tags' in metadata.tables:
            print("Tags table already exists.")
        else:
            # Create tags table
            tags = Table(
                'tags',
                metadata,
                Column('id', Integer, primary_key=True),
                Column('name', String(50), nullable=False, unique=True),
                Column('created_at', DateTime, default=datetime.utcnow),
                Column('is_ai_generated', Boolean, default=False)
            )
            tags.create(engine)
            print("Created tags table")
        
        # Check if paste_tags association table already exists
        if 'paste_tags' in metadata.tables:
            print("Paste tags association table already exists.")
        else:
            # Create paste_tags association table
            paste_tags = Table(
                'paste_tags',
                metadata,
                Column('paste_id', Integer, ForeignKey('pastes.id', ondelete='CASCADE'), primary_key=True),
                Column('tag_id', Integer, ForeignKey('tags.id', ondelete='CASCADE'), primary_key=True)
            )
            paste_tags.create(engine)
            print("Created paste_tags association table")
            
        print("Tags tables migration completed successfully.")
        return True
        
    except Exception as e:
        print(f"Error adding tags tables: {e}")
        return False

def main():
    """Main entry point for the script."""
    if not DATABASE_URL:
        print("DATABASE_URL environment variable not set!")
        sys.exit(1)
        
    print("Starting tags tables migration...")
    success = add_tags_table()
    
    if success:
        print("Tags tables migration completed successfully!")
    else:
        print("Tags tables migration failed!")
        sys.exit(1)

if __name__ == "__main__":
    main()