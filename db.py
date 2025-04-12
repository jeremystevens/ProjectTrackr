"""
Database configuration module.

This module defines the SQLAlchemy instance and Base class used by models.
It also provides direct psycopg2 connection for efficient operations using COPY.
It is separate from app.py to avoid circular imports.
"""

import os
import psycopg2
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase
import logging

logger = logging.getLogger(__name__)

# Create a base class for SQLAlchemy models
class Base(DeclarativeBase):
    pass

# Initialize extensions without binding them to an app yet
db = SQLAlchemy(model_class=Base)

# Direct psycopg2 connection for efficient operations
_pg_conn = None

def get_direct_connection():
    """
    Get a direct psycopg2 connection to the database.
    This bypasses SQLAlchemy for operations that need to use native PostgreSQL features like COPY.
    """
    global _pg_conn
    if _pg_conn is None or _pg_conn.closed:
        try:
            db_url = os.environ.get("DATABASE_URL", "")
            _pg_conn = psycopg2.connect(db_url)
            _pg_conn.autocommit = False  # Explicit transaction control
            logger.info("Created direct psycopg2 connection")
        except Exception as e:
            logger.error(f"Error creating direct psycopg2 connection: {e}")
            raise
    return _pg_conn

def copy_from_csv(file_obj, table_name, columns=None, delimiter=','):
    """
    Use PostgreSQL's efficient COPY command to load data from a CSV file.
    
    Args:
        file_obj: A file-like object containing CSV data
        table_name: Target table name
        columns: List of column names to insert into
        delimiter: CSV delimiter character
    
    Returns:
        Number of rows inserted
    """
    conn = get_direct_connection()
    cursor = conn.cursor()
    try:
        # Create column string if provided
        col_str = ""
        if columns:
            col_str = f"({', '.join(columns)})"
        
        # Execute COPY command
        cursor.copy_expert(
            f"COPY {table_name} {col_str} FROM STDIN WITH CSV DELIMITER '{delimiter}'", 
            file_obj
        )
        
        # Get number of rows inserted
        count = cursor.rowcount
        
        # Commit transaction
        conn.commit()
        logger.info(f"Copied {count} rows to {table_name}")
        return count
    except Exception as e:
        conn.rollback()
        logger.error(f"Error in COPY operation: {e}")
        raise
    finally:
        cursor.close()

def copy_to_csv(file_obj, table_name, columns=None, delimiter=',', where_clause=None):
    """
    Use PostgreSQL's efficient COPY command to export data to a CSV file.
    
    Args:
        file_obj: A file-like object to write CSV data to
        table_name: Source table name
        columns: List of column names to export
        delimiter: CSV delimiter character
        where_clause: Optional WHERE clause to filter data
    """
    conn = get_direct_connection()
    cursor = conn.cursor()
    try:
        # Create column string if provided
        col_str = "*"
        if columns:
            col_str = f"({', '.join(columns)})"
        
        # Add WHERE clause if provided
        where_str = ""
        if where_clause:
            where_str = f" WHERE {where_clause}"
        
        # Execute COPY command
        query = f"COPY (SELECT {col_str} FROM {table_name}{where_str}) TO STDOUT WITH CSV DELIMITER '{delimiter}'"
        cursor.copy_expert(query, file_obj)
        
        logger.info(f"Exported data from {table_name} to CSV")
    except Exception as e:
        logger.error(f"Error in COPY TO operation: {e}")
        raise
    finally:
        cursor.close()

def execute_raw_sql(sql, params=None, fetch=True):
    """
    Execute raw SQL directly with psycopg2 for performance-critical operations.
    
    Args:
        sql: SQL query to execute
        params: Query parameters
        fetch: Whether to fetch results
        
    Returns:
        Query results if fetch=True, otherwise None
    """
    conn = get_direct_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(sql, params)
        if fetch:
            results = cursor.fetchall()
            conn.commit()
            return results
        else:
            conn.commit()
            return cursor.rowcount
    except Exception as e:
        conn.rollback()
        logger.error(f"Error executing raw SQL: {e}")
        raise
    finally:
        cursor.close()

def close_direct_connection():
    """Close the direct psycopg2 connection if it exists."""
    global _pg_conn
    if _pg_conn and not _pg_conn.closed:
        _pg_conn.close()
        _pg_conn = None
        logger.info("Closed direct psycopg2 connection")

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
    
    # Register teardown to close direct connection
    @app.teardown_appcontext
    def close_db_connection(exception=None):
        close_direct_connection()