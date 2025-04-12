#!/usr/bin/env python3
"""
This script adds subscription-related fields to the User model.
Run this script to update your database schema.

Usage:
  python add_subscription_fields.py
"""

import os
import sys
from datetime import datetime
import sqlalchemy as sa
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.declarative import declarative_base

try:
    # Try to import from the app
    from app import db, app
    
    # If we get here, we can use the app context
    with app.app_context():
        try:
            print("Checking if subscription fields already exist...")
            # Check if the subscription_tier column exists - more robust check
            from sqlalchemy import inspect
            inspector = inspect(db.engine)
            columns = [col['name'] for col in inspector.get_columns('users')]
            if 'subscription_tier' in columns:
                print("Subscription fields already exist. Exiting.")
                sys.exit(0)
            else:
                print("Subscription fields don't exist yet. Will create them now.")
                
            print("Adding subscription fields to the users table...")
            
            # Create new columns using SQLAlchemy
            with db.engine.begin() as conn:
                # Add subscription tier column (default: free)
                conn.execute(sa.text(
                    "ALTER TABLE users ADD COLUMN subscription_tier VARCHAR(20) DEFAULT 'free'"
                ))
                
                # Add subscription start date column
                conn.execute(sa.text(
                    "ALTER TABLE users ADD COLUMN subscription_start_date TIMESTAMP"
                ))
                
                # Add subscription end date column
                conn.execute(sa.text(
                    "ALTER TABLE users ADD COLUMN subscription_end_date TIMESTAMP"
                ))
                
                # Add AI feature usage counters
                conn.execute(sa.text(
                    "ALTER TABLE users ADD COLUMN ai_calls_remaining INTEGER DEFAULT 0"
                ))
                
                conn.execute(sa.text(
                    "ALTER TABLE users ADD COLUMN ai_search_queries_remaining INTEGER DEFAULT 0"
                ))
            
            print("Subscription fields added successfully.")
            print("You can now use the subscription features in the application.")
            
        except SQLAlchemyError as e:
            print(f"Error: {e}")
            sys.exit(1)
            
except ImportError:
    print("Error: Could not import app. Make sure you're in the correct directory.")
    sys.exit(1)