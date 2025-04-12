"""
Base model package with database configuration.

This module handles the initialization and configuration of the SQLAlchemy database.
It provides a singleton pattern for model registration to avoid duplicate registrations.
"""

import os
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase

# Create a base class for SQLAlchemy models
class Base(DeclarativeBase):
    pass

# Initialize extensions without binding them to an app yet
db = SQLAlchemy(model_class=Base)

# Flag to track initialization status
_DB_INITIALIZED = False

def init_db(app):
    """Initialize the database with the Flask app"""
    # Configure the database
    app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL", "sqlite:///pastebin.db")
    app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
        "pool_recycle": 300,
        "pool_pre_ping": True,
    }
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    
    # Initialize the database with the app
    db.init_app(app)
    
    global _DB_INITIALIZED
    _DB_INITIALIZED = True

def is_db_initialized():
    """Check if the database has been initialized"""
    return _DB_INITIALIZED