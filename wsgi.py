"""
WSGI entry point for production deployment on Render.

This is a minimal WSGI entry point that directly imports the app from deploy_wsgi.py,
which handles all the necessary initialization in a way that avoids mapper conflicts.

To use this file with Gunicorn:
gunicorn --bind 0.0.0.0:$PORT wsgi:app
"""

import os
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
logger.info("Starting WSGI wrapper")

try:
    # Import the app from deploy_wsgi.py
    from deploy_wsgi import app
    
    logger.info("Successfully imported app from deploy_wsgi")
except ImportError as e:
    logger.error(f"Failed to import app from deploy_wsgi: {e}")
    raise
except Exception as e:
    logger.error(f"Unexpected error during import: {e}")
    raise

logger.info("WSGI wrapper initialized successfully")