import logging
logging.basicConfig(level=logging.DEBUG)

# Import app instance from create_app.py
# The app is created by our robust application factory
from create_app import create_app

# Create the app using the factory function
app = create_app()

# This file is used by gunicorn as the WSGI entry point
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
