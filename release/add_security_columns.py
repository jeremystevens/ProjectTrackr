"""
Script to add security question columns to the users table.

This should be run as a one-time migration.
"""

from app import db, app
import sys
from sqlalchemy import text

def add_security_columns():
    """Add security_question and security_answer_hash columns to users table"""
    with app.app_context():
        try:
            # Check if columns already exist
            result = db.session.execute(text("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name='users' 
                AND (column_name='security_question' OR column_name='security_answer_hash')
            """)).fetchall()
            
            existing_columns = [r[0] for r in result]
            
            # Add security_question column if it doesn't exist
            if 'security_question' not in existing_columns:
                print("Adding 'security_question' column to users table...")
                db.session.execute(text("""
                    ALTER TABLE users 
                    ADD COLUMN security_question VARCHAR(255)
                """))
                print("✓ Added 'security_question' column")
            else:
                print("✓ 'security_question' column already exists")
                
            # Add security_answer_hash column if it doesn't exist
            if 'security_answer_hash' not in existing_columns:
                print("Adding 'security_answer_hash' column to users table...")
                db.session.execute(text("""
                    ALTER TABLE users 
                    ADD COLUMN security_answer_hash VARCHAR(256)
                """))
                print("✓ Added 'security_answer_hash' column")
            else:
                print("✓ 'security_answer_hash' column already exists")
                
            # Commit changes
            db.session.commit()
            print("✓ Migration completed successfully!")
            return True
            
        except Exception as e:
            print(f"Error: {e}")
            db.session.rollback()
            return False

def main():
    """Main entry point for the script."""
    print("Running database migration to add security question columns...")
    success = add_security_columns()
    
    if success:
        print("Migration completed successfully.")
        sys.exit(0)
    else:
        print("Migration failed.")
        sys.exit(1)

if __name__ == "__main__":
    main()