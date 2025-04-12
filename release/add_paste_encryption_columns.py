#!/usr/bin/env python3
"""
Script to add encryption-related columns to the pastes table.

This should be run as a one-time migration.
"""

import os
import sys
import logging
from datetime import datetime

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Add the current directory to the path so we can import app
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

try:
    import sqlalchemy
    from sqlalchemy.exc import SQLAlchemyError
    from app import db, app
except ImportError as e:
    logger.error(f"Import error: {e}")
    sys.exit(1)

def add_paste_encryption_columns():
    """Add encryption-related columns to pastes table"""
    logger.info("Adding encryption-related columns to pastes table...")
    
    with app.app_context():
        try:
            # Check if the columns already exist
            inspector = sqlalchemy.inspect(db.engine)
            columns = [col['name'] for col in inspector.get_columns('pastes')]
            
            # Add is_encrypted column if it doesn't exist
            if 'is_encrypted' not in columns:
                logger.info("Adding 'is_encrypted' column")
                with db.engine.connect() as conn:
                    conn.execute(sqlalchemy.text('ALTER TABLE pastes ADD COLUMN is_encrypted TINYINT(1) DEFAULT FALSE'))
                    conn.commit()
            else:
                logger.info("Column 'is_encrypted' already exists")
                
            # Add encryption_method column if it doesn't exist
            if 'encryption_method' not in columns:
                logger.info("Adding 'encryption_method' column")
                with db.engine.connect() as conn:
                    conn.execute(sqlalchemy.text('ALTER TABLE pastes ADD COLUMN encryption_method VARCHAR(50)'))
                    conn.commit()
            else:
                logger.info("Column 'encryption_method' already exists")
                
            # Add password_protected column if it doesn't exist
            if 'password_protected' not in columns:
                logger.info("Adding 'password_protected' column")
                with db.engine.connect() as conn:
                    conn.execute(sqlalchemy.text('ALTER TABLE pastes ADD COLUMN password_protected TINYINT(1) DEFAULT FALSE'))
                    conn.commit()
            else:
                logger.info("Column 'password_protected' already exists")
                
            # Add password_hash column if it doesn't exist
            if 'password_hash' not in columns:
                logger.info("Adding 'password_hash' column")
                with db.engine.connect() as conn:
                    conn.execute(sqlalchemy.text('ALTER TABLE pastes ADD COLUMN password_hash VARCHAR(256)'))
                    conn.commit()
            else:
                logger.info("Column 'password_hash' already exists")
                
            # Add salt column if it doesn't exist (for encryption)
            if 'encryption_salt' not in columns:
                logger.info("Adding 'encryption_salt' column")
                with db.engine.connect() as conn:
                    conn.execute(sqlalchemy.text('ALTER TABLE pastes ADD COLUMN encryption_salt VARCHAR(128)'))
                    conn.commit()
            else:
                logger.info("Column 'encryption_salt' already exists")
                
            logger.info("Migration completed successfully")
            
        except SQLAlchemyError as e:
            logger.error(f"Error in migration: {e}")
            return False
            
    return True

def main():
    """Main entry point for the script."""
    logger.info("Starting migration to add encryption columns to pastes table")
    
    if add_paste_encryption_columns():
        logger.info("Migration completed successfully")
    else:
        logger.error("Migration failed")
        sys.exit(1)
        
if __name__ == "__main__":
    main()