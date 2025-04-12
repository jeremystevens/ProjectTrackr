import logging
logging.basicConfig(level=logging.DEBUG)

# For Render deployment, we should use the app from wsgi.py
# This avoids circular imports and model mapping conflicts
from wsgi import app

# This file is used for local development
# For production deployment, use 'wsgi:app' instead of 'main:app'
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
