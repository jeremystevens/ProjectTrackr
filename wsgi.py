"""
WSGI entry point for production deployment on Render.

This file uses the final approved Flask application factory pattern with
SQLAlchemy initialization that avoids mapper conflicts.
"""
from create_app import create_app

# Initialize the app using the factory function
app = create_app()