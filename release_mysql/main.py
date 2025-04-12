#!/usr/bin/env python3
"""
Main entry point for the FlaskBin application.
"""
from clean_app import app

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)