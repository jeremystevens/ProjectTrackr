#!/usr/bin/env python3
"""
WSGI entry point for the FlaskBin application.
"""
from clean_app import app as application

if __name__ == "__main__":
    import os
    application.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))