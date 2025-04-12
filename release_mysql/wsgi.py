#!/usr/bin/env python3
"""
WSGI entry point for MySQL version of FlaskBin.
This module simply imports the app object from app.py.
"""
from app import app

if __name__ == "__main__":
    app.run()