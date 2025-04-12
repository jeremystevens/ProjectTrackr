"""
Script to add account lockout columns to the users table.

This should be run as a one-time migration.
"""

from app import db, app
import sys
from sqlalchemy import text

def add_account_lockout_columns():
    """Add account security columns to users table"""
    with app.app_context():
        try:
            # Check if columns already exist
            result = db.session.execute(text("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name='users' 
                AND column_name IN ('failed_login_attempts', 'failed_reset_attempts', 
                                    'account_locked_until', 'last_failed_attempt')
            """)).fetchall()
            
            existing_columns = [r[0] for r in result]
            
            # Add failed_login_attempts column if it doesn't exist
            if 'failed_login_attempts' not in existing_columns:
                print("Adding 'failed_login_attempts' column to users table...")
                db.session.execute(text("""
                    ALTER TABLE users 
                    ADD COLUMN failed_login_attempts INTEGER DEFAULT 0
                """))
                print("✓ Added 'failed_login_attempts' column")
            else:
                print("✓ 'failed_login_attempts' column already exists")
                
            # Add failed_reset_attempts column if it doesn't exist
            if 'failed_reset_attempts' not in existing_columns:
                print("Adding 'failed_reset_attempts' column to users table...")
                db.session.execute(text("""
                    ALTER TABLE users 
                    ADD COLUMN failed_reset_attempts INTEGER DEFAULT 0
                """))
                print("✓ Added 'failed_reset_attempts' column")
            else:
                print("✓ 'failed_reset_attempts' column already exists")
                
            # Add account_locked_until column if it doesn't exist
            if 'account_locked_until' not in existing_columns:
                print("Adding 'account_locked_until' column to users table...")
                db.session.execute(text("""
                    ALTER TABLE users 
                    ADD COLUMN account_locked_until TIMESTAMP
                """))
                print("✓ Added 'account_locked_until' column")
            else:
                print("✓ 'account_locked_until' column already exists")
                
            # Add last_failed_attempt column if it doesn't exist
            if 'last_failed_attempt' not in existing_columns:
                print("Adding 'last_failed_attempt' column to users table...")
                db.session.execute(text("""
                    ALTER TABLE users 
                    ADD COLUMN last_failed_attempt TIMESTAMP
                """))
                print("✓ Added 'last_failed_attempt' column")
            else:
                print("✓ 'last_failed_attempt' column already exists")
                
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
    print("Running database migration to add account lockout columns...")
    success = add_account_lockout_columns()
    
    if success:
        print("Migration completed successfully.")
        sys.exit(0)
    else:
        print("Migration failed.")
        sys.exit(1)

if __name__ == "__main__":
    main()