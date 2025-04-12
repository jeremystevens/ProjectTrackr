"""
Main application entry point for FlaskBin

This file serves as the entry point for the application when running locally.
It imports the Flask application instance from app.py and runs it.
"""
import os
import pymysql
from app import create_app

app = create_app()

if __name__ == "__main__":
    # Run the app with debug=True for local development
    app.run(host="0.0.0.0", port=5000, debug=True)