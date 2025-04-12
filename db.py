"""
Database configuration module.

This module defines the SQLAlchemy instance and Base class used by models.
It is separate from app.py to avoid circular imports.
"""

import os
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase

# Create a base class for SQLAlchemy models
class Base(DeclarativeBase):
    pass

# Initialize extensions without binding them to an app yet
db = SQLAlchemy(model_class=Base)

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