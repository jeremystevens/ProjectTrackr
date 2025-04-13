"""
Minimal WSGI entry point to prevent SQLAlchemy mapper conflicts.
"""
import os
import sys
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
logger.info("Starting minimal WSGI app")

# Import app from app.py with create_app pattern
from app import create_app

# Create app instance
app = create_app()

# If running directly
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)