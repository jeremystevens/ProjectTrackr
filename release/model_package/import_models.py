"""
Model import utility for safe model importing.

This module provides a function to safely import all models and ensure
they are only registered once with SQLAlchemy.
"""
import importlib
import sys

# Track if models have been imported
_MODELS_IMPORTED = False

def import_all_models():
    """
    Import all models from the model_package in a safe way.
    This function ensures models are only imported once to prevent
    SQLAlchemy mapper conflicts.
    """
    global _MODELS_IMPORTED
    
    # If models already imported, just return
    if _MODELS_IMPORTED:
        return
    
    # Mark as imported first to prevent reentry if there are circular imports
    _MODELS_IMPORTED = True
    
    # Import the necessary modules
    from model_package import user
    
    # Register models
    user.register_user_models()
    
    # Return success
    return True

def are_models_imported():
    """Check if models have already been imported"""
    return _MODELS_IMPORTED