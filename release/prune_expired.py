#!/usr/bin/env python
"""
Script to prune expired pastes from the database.
This should be run as a scheduled task (e.g., cron job) every 10 minutes.

Example cron entry:
*/10 * * * * /path/to/python /path/to/prune_expired.py
"""

import os
import sys
import logging
from datetime import datetime
import argparse

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('prune_expired.log')
    ]
)
logger = logging.getLogger('paste_pruner')

# Add the current directory to the path so we can import our app modules
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import our Flask app and models
from app import app, db
from models import Paste, PasteView

def prune_expired_pastes(dry_run=False):
    """
    Remove all expired pastes from the database.
    
    Args:
        dry_run (bool): If True, only log what would be deleted without actually removing anything
    
    Returns:
        int: Number of pastes pruned
    """
    now = datetime.utcnow()
    logger.info(f"Starting prune operation at {now} (UTC)")

    # Find all expired pastes
    expired_pastes = Paste.query.filter(
        (Paste.expires_at.isnot(None)) & (Paste.expires_at < now)
    ).all()
    
    count = len(expired_pastes)
    logger.info(f"Found {count} expired pastes to prune")

    if count == 0:
        return 0
    
    if dry_run:
        logger.info("DRY RUN: The following pastes would be pruned:")
        for paste in expired_pastes:
            logger.info(f"  ID: {paste.id}, Title: {paste.title}, Short ID: {paste.short_id}, Expired at: {paste.expires_at}")
        return count

    # Delete the expired pastes
    for paste in expired_pastes:
        logger.info(f"Pruning paste ID {paste.id}, Title: {paste.title}, Short ID: {paste.short_id}, Expired at: {paste.expires_at}")
        
        # First delete associated views to avoid foreign key constraint issues
        paste_views = PasteView.query.filter_by(paste_id=paste.id).all()
        logger.info(f"  Deleting {len(paste_views)} view records")
        for view in paste_views:
            db.session.delete(view)
        
        # Update user stats if this paste has an author
        if paste.user_id:
            # Update the author's total_pastes count if it's greater than 0
            if paste.author.total_pastes > 0:
                paste.author.total_pastes -= 1
                # Also subtract the view count from the user's total
                if paste.views > 0 and paste.author.total_views >= paste.views:
                    paste.author.total_views -= paste.views
        
        # Delete the paste
        db.session.delete(paste)
    
    # Commit the changes
    db.session.commit()
    logger.info(f"Successfully pruned {count} expired pastes")
    
    return count

def main():
    """Main entry point for the script."""
    parser = argparse.ArgumentParser(description='Prune expired pastes from the database')
    parser.add_argument('--dry-run', action='store_true', help='Only log what would be deleted without removing anything')
    args = parser.parse_args()
    
    with app.app_context():
        pruned = prune_expired_pastes(dry_run=args.dry_run)
        logger.info(f"Prune operation completed. {pruned} pastes {'would be' if args.dry_run else 'were'} pruned.")

if __name__ == '__main__':
    main()
