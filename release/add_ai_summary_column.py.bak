"""
Script to add ai_summary column to the pastes table.

This should be run as a one-time migration.
"""

from app import app, db
import sqlalchemy as sa
from sqlalchemy.schema import Column
from sqlalchemy.exc import OperationalError

def add_ai_summary_column():
    """Add ai_summary column to pastes table for AI-generated code summaries"""
    
    # Use raw SQL directly instead of SQLAlchemy reflection
    try:
        # First check if the column exists
        inspector = sa.inspect(db.engine)
        columns = [col['name'] for col in inspector.get_columns('pastes')]
        
        if 'ai_summary' not in columns:
            with db.engine.connect() as conn:
                conn.execute(sa.text("ALTER TABLE pastes ADD COLUMN ai_summary TEXT"))
                conn.commit()
            print("Successfully added 'ai_summary' column to pastes table.")
        else:
            print("Column 'ai_summary' already exists in pastes table.")
        return True
    except Exception as e:
        print(f"Failed to add column: {str(e)}")
        return False

def main():
    """Main entry point for the script."""
    print("Adding AI summary column to pastes table...")
    
    # Use the application context to access database
    with app.app_context():
        success = add_ai_summary_column()
    
        if success:
            print("Migration completed successfully.")
        else:
            print("Migration failed.")

if __name__ == "__main__":
    main()