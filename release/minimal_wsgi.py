"""
Ultra-minimal WSGI entry point that strips out all complex functionality
to ensure the application can at least start in production.

This is a fallback solution when more complex approaches fail.
"""
import logging
import os
from flask import Flask, redirect, url_for, render_template

# Set up basic logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)
logger.info("Starting ultra-minimal WSGI app")

# Create the most basic Flask app
app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "dev-secret-key")

# Simplified database setup to avoid SQLAlchemy mapper conflicts
# You'll need to add SQLAlchemy later when the root issue is fixed
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL", "sqlite:///pastebin.db")
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

# Basic routes that don't rely on database
@app.route('/')
def index():
    return render_template('maintenance.html', message="FlaskBin is currently in maintenance mode")

@app.route('/health')
def health():
    """Simple health check endpoint"""
    return {"status": "ok", "version": "minimal-fallback"}

# Error handlers
@app.errorhandler(404)
def not_found_error(error):
    return render_template('errors/404.html'), 404

@app.errorhandler(500)
def internal_server_error(error):
    error_id = f"ERR-{os.urandom(3).hex()}"
    logger.error(f"500 error encountered: {error}, ID: {error_id}")
    return render_template('errors/500.html', error_id=error_id), 500

# Signal that this is a minimal version
logger.info("Ultra-minimal WSGI app initialization complete")

if __name__ == "__main__":
    # For local testing only
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)), debug=True)