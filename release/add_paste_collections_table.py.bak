"""
Script to add paste_collections table and collection_id column to the pastes table.

This should be run as a one-time migration.
"""
import os
import sys
from datetime import datetime

from sqlalchemy import create_engine, Column, Integer, String, Text, Boolean, DateTime, ForeignKey, MetaData, Table, text
from sqlalchemy.exc import OperationalError, SQLAlchemyError

def add_paste_collections_table():
    """Add paste_collections table and collection_id column to pastes table"""
    try:
        # Create the database engine
        engine = create_engine(os.environ.get('DATABASE_URL'))
        
        # Create a metadata instance
        metadata = MetaData()
        
        # Reflect existing tables
        metadata.reflect(bind=engine)
        
        # Check if paste_collections table already exists
        if 'paste_collections' in metadata.tables:
            print("Paste collections table already exists.")
        else:
            # Create paste_collections table
            paste_collections = Table(
                'paste_collections',
                metadata,
                Column('id', Integer, primary_key=True),
                Column('name', String(100), nullable=False),
                Column('description', Text, nullable=True),
                Column('user_id', Integer, ForeignKey('users.id'), nullable=False),
                Column('created_at', DateTime, default=datetime.utcnow),
                Column('updated_at', DateTime, default=datetime.utcnow, onupdate=datetime.utcnow),
                Column('is_public', Boolean, default=False)
            )
            paste_collections.create(engine)
            print("Created paste_collections table")
        
        # Now add the collection_id column to the pastes table if it doesn't exist
        pastes_table = metadata.tables['pastes']
        # Check if the column already exists
        column_exists = False
        for column in pastes_table.columns:
            if column.name == 'collection_id':
                column_exists = True
                break
        
        if not column_exists:
            # Add the collection_id column using text() and connection.execute
            with engine.connect() as conn:
                conn.execute(text('ALTER TABLE pastes ADD COLUMN collection_id INTEGER REFERENCES paste_collections(id)'))
                conn.commit()
            print("Added collection_id column to pastes table")
        else:
            print("Collection_id column already exists in pastes table")
            
        return True
    except OperationalError as e:
        print(f"Database error occurred: {e}")
        return False
    except SQLAlchemyError as e:
        print(f"SQLAlchemy error occurred: {e}")
        return False
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        return False

def main():
    """Main entry point for the script."""
    print("Starting migration to add paste collections table and collection_id column...")
    if add_paste_collections_table():
        print("Migration completed successfully.")
    else:
        print("Migration failed.")
        sys.exit(1)

if __name__ == '__main__':
    main()