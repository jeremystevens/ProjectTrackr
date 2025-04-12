import logging
logging.basicConfig(level=logging.DEBUG)

# Import app instance from app.py
# The app is created by the app.py create_app() function
from app import app

# This file is used by gunicorn as the WSGI entry point
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
