"""
Test script to verify that the wsgi.py file works correctly
and doesn't have any SQLAlchemy mapper conflicts.
"""
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

try:
    logger.info("Importing app from wsgi")
    from wsgi import app
    logger.info("Successfully imported app from wsgi")
    
    # Test accessing the User model
    with app.app_context():
        from wsgi import User
        logger.info(f"User model: {User}")
        logger.info("Table name: %s", User.__tablename__)
        
        # Test querying the database
        try:
            user_count = User.query.count()
            logger.info(f"User count: {user_count}")
        except Exception as e:
            logger.error(f"Error querying users: {e}")
    
    logger.info("WSGI import test completed successfully")
except Exception as e:
    logger.error(f"Error importing from wsgi: {e}")
    import traceback
    traceback.print_exc()