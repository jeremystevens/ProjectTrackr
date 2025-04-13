"""
Database configuration module with singleton pattern.
"""
import os
import logging
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase

logger = logging.getLogger(__name__)

# Create a base class for SQLAlchemy models
class Base(DeclarativeBase):
    pass

# Initialize SQLAlchemy with our base class
db = SQLAlchemy(model_class=Base)

# Singleton pattern - track initialization
_DB_INITIALIZED = False

def init_db(app):
    """Initialize the database with the Flask app - only once"""
    global _DB_INITIALIZED
    
    # Don't initialize twice
    if _DB_INITIALIZED:
        logger.info("Database already initialized, skipping")
        return
    
    # Configure the database
    db_url = os.environ.get("DATABASE_URL", "sqlite:///pastebin.db")
    
    # Fix URL format for different PostgreSQL URL styles
    if db_url and db_url.startswith('postgres://'):
        db_url = db_url.replace('postgres://', 'postgresql://', 1)
        logger.info("Fixed PostgreSQL URL format")
    
    # Log database connection (sanitized)
    if db_url and 'postgresql://' in db_url:
        parts = db_url.split('@')
        if len(parts) > 1:
            sanitized_url = f"postgresql://****:****@{parts[1]}"
            logger.info(f"Using database URL: {sanitized_url}")
        else:
            logger.info("Using PostgreSQL database")
    else:
        logger.info(f"Using database URL: {db_url}")
    
    # Configure SQLAlchemy
    app.config["SQLALCHEMY_DATABASE_URI"] = db_url
    app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
        "pool_recycle": 300,
        "pool_pre_ping": True,
    }
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    
    # Initialize the database with the app
    db.init_app(app)
    
    # Mark as initialized
    _DB_INITIALIZED = True
    logger.info("Database initialized successfully")

def is_db_initialized():
    """Check if the database has been initialized"""
    return _DB_INITIALIZED