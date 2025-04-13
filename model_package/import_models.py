"""
Model import utility for safe model importing.

This module provides a function to safely import all models and ensure
they are only registered once with SQLAlchemy.
"""
import logging
from typing import Dict, Type

from model_package.base import db
from model_package.user import User, PasswordResetToken, register_user_models

logger = logging.getLogger(__name__)

# Track if models have been imported
_MODELS_IMPORTED = False

# Store model references
models: Dict[str, Type[db.Model]] = {}

def import_all_models():
    """
    Import all models from the model_package in a safe way.
    This function ensures models are only imported once to prevent
    SQLAlchemy mapper conflicts.
    """
    global _MODELS_IMPORTED, models
    
    # If models already imported, just return the models dict
    if _MODELS_IMPORTED:
        return models
    
    try:
        # Register user models
        register_user_models()
        
        # Store model references
        models.update({
            'User': User,
            'PasswordResetToken': PasswordResetToken
        })
        
        # Mark as imported
        _MODELS_IMPORTED = True
        logger.info("Successfully imported all models")
        
        return models
        
    except Exception as e:
        logger.error(f"Error importing models: {e}")
        raise

def are_models_imported():
    """Check if models have already been imported"""
    return _MODELS_IMPORTED

def get_model(model_name: str):
    """Get a model class by name"""
    if not _MODELS_IMPORTED:
        import_all_models()
    return models.get(model_name)