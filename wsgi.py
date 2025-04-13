"""
WSGI entry point with proper model initialization.
"""
import os
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
logger.info("Starting WSGI app")

# Import create_app
from app import create_app

# Create app instance
app = create_app()

# Import models through the centralized import function
from model_package.import_models import import_all_models, get_model

# Make models available at module level for convenience
User = get_model('User')
PasswordResetToken = get_model('PasswordResetToken')

# If running directly
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)