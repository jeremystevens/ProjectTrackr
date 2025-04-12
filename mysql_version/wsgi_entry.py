#!/usr/bin/env python3
"""
WSGI entry point specifically for Gunicorn to use in Replit workflows
"""
from simple_app import app

# This file is needed for gunicorn to correctly locate the app