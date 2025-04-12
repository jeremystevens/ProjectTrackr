"""
The absolute simplest WSGI app that will work with the existing templates.
No database, no complex routing - just enough to make the site available.
"""
import os
import logging
from flask import Flask, render_template, redirect, url_for, flash, Blueprint

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)
logger.info("Starting super minimal WSGI app")

# Create Flask app
app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "dev-secret-key")

# Create a simple Blueprint with the same name used in templates
paste_bp = Blueprint('paste', __name__)

@paste_bp.route('/')
def index():
    return render_template('maintenance.html', message="FlaskBin is currently in maintenance mode")

@paste_bp.route('/<short_id>')
def view(short_id):
    return render_template('maintenance.html', message=f"Paste '{short_id}' is not available during maintenance")

# Register the blueprint to match existing url_for calls
app.register_blueprint(paste_bp, url_prefix='')

# Create a basic route for static assets
@app.route('/health')
def health():
    """Simple health check endpoint"""
    return {"status": "ok"}

# Error handlers
@app.errorhandler(404)
def not_found_error(error):
    return render_template('errors/404.html'), 404

@app.errorhandler(500)
def internal_server_error(error):
    error_id = f"ERR-{os.urandom(3).hex()}"
    logger.error(f"500 error encountered: {error}, ID: {error_id}")
    return render_template('errors/500.html', error_id=error_id), 500

if __name__ == "__main__":
    # For local testing only
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)), debug=True)