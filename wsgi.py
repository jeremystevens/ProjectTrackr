"""
Minimal WSGI entry point for production deployment on Render.

This file is designed to be as simple as possible to avoid SQLAlchemy
mapper conflicts that occur in more complex app structures.
"""
import os
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
logger.info("Starting deployment WSGI app")

# Configure database URL if needed
db_url = os.environ.get("DATABASE_URL", "sqlite:///pastebin.db")
# Fix URL format for different PostgreSQL URL styles
if db_url and db_url.startswith('postgres://'):
    db_url = db_url.replace('postgres://', 'postgresql://', 1)
    
os.environ["DATABASE_URL"] = db_url
logger.info(f"Using database URL type: {db_url.split(':')[0]}")

# Import app factory - this avoids circular imports and multiple
# model registrations by using application factory pattern
from app import create_app

# Create the application - this is the key step
# that ensures models are only registered once
app = create_app()

if __name__ == "__main__":
    # Run the app
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)