#!/usr/bin/env python3
"""
MySQL-only WSGI application for FlaskBin

This is a clean implementation that completely avoids PostgreSQL conflicts.
"""
import os
import logging
import sys

# Add the current directory to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# MySQL connection string
MYSQL_URI = os.environ.get("DATABASE_URL", "mysql+pymysql://u213077714_flaskbin:hOJ27K?5@185.212.71.204:3306/u213077714_flaskbin")

# Import our clean application
try:
    # Import the application from the clean_app module
    from clean_app import app as application
    logger.info("Imported clean application successfully")
except ImportError as e:
    logger.error(f"Failed to import clean application: {e}")
    raise

# For direct execution
if __name__ == "__main__":
    application.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))