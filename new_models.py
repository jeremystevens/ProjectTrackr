"""
Models module.

This is a wrapper module to maintain backward compatibility with existing code.
It imports models from the model_package in a safe way to prevent mapper conflicts.
"""

# Import model utility functions
from model_package.import_models import import_all_models

# Trigger the import of all models
import_all_models()

# Now import specific models for backward compatibility
from model_package.user import User, PasswordResetToken

# Add other model imports as needed
# For example:
# from model_package.paste import Paste, Comment