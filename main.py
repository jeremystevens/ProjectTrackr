import logging
logging.basicConfig(level=logging.DEBUG)

# Import app directly (don't import anything else from app.py)
from app import app

# Don't modify anything in this file - it's used by gunicorn
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
