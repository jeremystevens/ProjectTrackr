"""
Database configuration module.

This module defines the SQLAlchemy instance and Base class used by models.
It is separate from app.py to avoid circular imports.
"""
import os
from flask_sqlalchemy import SQLAlchemy

# Create database instance first without binding to an app
db = SQLAlchemy()

def init_db(app):
    """Initialize the database with the Flask app"""
    # Configure database
    app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL", "sqlite:///pastebin.db")
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
        "pool_recycle": 300,
        "pool_pre_ping": True,
    }
    
    # Initialize db with the app
    db.init_app(app)