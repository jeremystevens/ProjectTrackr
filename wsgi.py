"""
WSGI entry point for production deployment on Render.

This is a minimal WSGI entry point that directly uses the deploy_wsgi app
without any additional imports or configurations to avoid mapper conflicts.
"""

# Import the app from deploy_wsgi.py directly
# The app is fully configured in deploy_wsgi.py
from deploy_wsgi import app