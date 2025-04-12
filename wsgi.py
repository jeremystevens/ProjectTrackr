"""
WSGI entry point for deployment to Render.

This file is now just a redirect to deploy_wsgi.py to avoid
the 'class already has a primary mapper defined' error in SQLAlchemy.
"""

# Import app directly from deploy_wsgi.py which is the correct setup for Render
from deploy_wsgi import app

# This file is now just a redirect to deploy_wsgi.py
# The full Flask application with proper SQLAlchemy model configuration
# is defined in deploy_wsgi.py