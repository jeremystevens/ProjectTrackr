"""
Script to set a user as an administrator.

Usage:
  python set_admin.py username
"""

import sys
from app import app, db
from models import User

def set_user_as_admin(username):
    """Set a user as an administrator"""
    with app.app_context():
        user = User.query.filter_by(username=username).first()
        
        if not user:
            print(f"Error: User '{username}' not found.")
            return False
            
        user.is_admin = True
        db.session.commit()
        
        print(f"Success: User '{username}' is now an administrator.")
        return True

def main():
    """Main entry point for the script."""
    # Check if username was provided as command line argument
    if len(sys.argv) != 2:
        print("Usage: python set_admin.py USERNAME")
        return
        
    username = sys.argv[1]
    set_user_as_admin(username)

if __name__ == "__main__":
    main()