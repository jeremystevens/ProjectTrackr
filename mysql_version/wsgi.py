#!/usr/bin/env python3
"""
WSGI entry point for the MySQL-compatible FlaskBin application.
"""
from simple_app import app as application

# For testing purposes
if __name__ == "__main__":
    import os
    application.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))