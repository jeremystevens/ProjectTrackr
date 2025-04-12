#!/usr/bin/env python3
"""
Main entry point for the MySQL-compatible FlaskBin application.
"""
from simple_app import app

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)