"""
Main application entry point for local development.

This module imports the application from new_wsgi.py and runs it
with Flask's development server.
"""

from new_wsgi import app

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)