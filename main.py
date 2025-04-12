"""
Main entry point for the FlaskBin application.
This file delegates to the MySQL-compatible version to avoid SQLAlchemy dialect conflicts.
"""
import os
import sys

# Add the mysql_version directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'mysql_version'))

# Import the app from the MySQL version
from simple_app import app

# This variable is required for Gunicorn to find the application
application = app

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)), debug=True)