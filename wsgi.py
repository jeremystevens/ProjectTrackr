"""
WSGI entry point for the MySQL version of FlaskBin.
This is the entry point for Gunicorn in production.
"""
import os
import sys

# Add the mysql_version directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'mysql_version'))

# Import the app from the MySQL version
from simple_app import app

# This variable is required for Gunicorn to find the application
application = app