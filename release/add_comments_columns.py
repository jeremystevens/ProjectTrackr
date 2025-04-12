"""
Script to add comments table and comments_enabled column to the pastes table.

This should be run as a one-time migration.
"""
import os
import sys
from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, Text, Boolean, ForeignKey
from sqlalchemy import create_engine, MetaData, Table, inspect, text

def add_comments_table():
    """Add comments table and comments_enabled column to pastes table"""
    # Get database URL from environment or use default
    database_url = os.environ.get('DATABASE_URL')
    if not database_url:
        print("DATABASE_URL environment variable not set.")
        sys.exit(1)
        
    print(f"Connecting to database: {database_url}")
    engine = create_engine(database_url)
    metadata = MetaData()
    
    # Check if comments table already exists
    inspector = inspect(engine)
    if 'comments' in inspector.get_table_names():
        print("Comments table already exists.")
    else:
        print("Creating comments table...")
        # Define the comments table
        Table('comments', metadata,
            Column('id', Integer, primary_key=True),
            Column('content', Text, nullable=False),
            Column('user_id', Integer, ForeignKey('users.id'), nullable=False),
            Column('paste_id', Integer, ForeignKey('pastes.id'), nullable=False),
            Column('created_at', DateTime, default=datetime.utcnow),
            Column('updated_at', DateTime, default=datetime.utcnow, onupdate=datetime.utcnow),
            Column('parent_id', Integer, ForeignKey('comments.id'), nullable=True)
        )
        
        # Create the comments table
        metadata.create_all(engine, tables=[metadata.tables['comments']])
        print("Comments table created successfully.")
    
    # Check if comments_enabled column exists in pastes table
    pastes_columns = [column['name'] for column in inspector.get_columns('pastes')]
    if 'comments_enabled' in pastes_columns:
        print("comments_enabled column already exists in pastes table.")
    else:
        print("Adding comments_enabled column to pastes table...")
        # Add the comments_enabled column to the pastes table
        with engine.connect() as connection:
            connection.execute(text("ALTER TABLE pastes ADD COLUMN comments_enabled TINYINT(1) DEFAULT TRUE"))
            connection.commit()
        print("comments_enabled column added to pastes table successfully.")
    
    print("Migration complete.")

def main():
    """Main entry point for the script."""
    add_comments_table()

if __name__ == "__main__":
    main()