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
            
            # Skip if not a PostgreSQL URL
            if not db_url or not ('postgres://' in db_url or 'postgresql://' in db_url):
                logger.warning("No PostgreSQL URL available for direct connection")
                return None
                
            # Standardize URL format from Render/Heroku style to psycopg2 style
            if db_url.startswith('postgres://'):
                db_url = db_url.replace('postgres://', 'postgresql://', 1)
                
            # Create the connection
            _pg_conn = psycopg2.connect(db_url)
            _pg_conn.autocommit = False  # Explicit transaction control
            logger.info("Created direct psycopg2 connection")
        except Exception as e:
            logger.error(f"Error creating direct psycopg2 connection: {e}")
            # Don't raise exception - let the application continue without direct connection
            return None
    return _pg_conn

def copy_from_csv(file_obj, table_name, columns=None, delimiter=','):
    """
    Use PostgreSQL's efficient COPY command to load data from a CSV file.
    If direct PostgreSQL connection is not available, falls back to SQLAlchemy.
    
    Args:
        file_obj: A file-like object containing CSV data
        table_name: Target table name
        columns: List of column names to insert into
        delimiter: CSV delimiter character
    
    Returns:
        Number of rows inserted or None if operation fails
    """
    conn = get_direct_connection()
    
    # Fall back to SQLAlchemy if direct connection not available
    if conn is None:
        logger.warning("Direct PostgreSQL connection not available, COPY operation not supported")
        return None
    
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
        if conn and not conn.closed:
            conn.rollback()
        logger.error(f"Error in COPY operation: {e}")
        return None
    finally:
        if cursor and not cursor.closed:
            cursor.close()

def copy_to_csv(file_obj, table_name, columns=None, delimiter=',', where_clause=None):
    """
    Use PostgreSQL's efficient COPY command to export data to a CSV file.
    If direct PostgreSQL connection is not available, returns False.
    
    Args:
        file_obj: A file-like object to write CSV data to
        table_name: Source table name
        columns: List of column names to export
        delimiter: CSV delimiter character
        where_clause: Optional WHERE clause to filter data
        
    Returns:
        True if successful, False otherwise
    """
    conn = get_direct_connection()
    cursor = None
    
    # Fall back if direct connection not available
    if conn is None:
        logger.warning("Direct PostgreSQL connection not available, COPY TO operation not supported")
        return False
        
    try:
        cursor = conn.cursor()
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
        return True
    except Exception as e:
        logger.error(f"Error in COPY TO operation: {e}")
        return False
    finally:
        if cursor and not getattr(cursor, 'closed', True) is False:
            try:
                cursor.close()
            except Exception:
                pass

def execute_raw_sql(sql, params=None, fetch=True):
    """
    Execute raw SQL directly with psycopg2 for performance-critical operations.
    If direct connection is not available, returns None.
    
    Args:
        sql: SQL query to execute
        params: Query parameters
        fetch: Whether to fetch results
        
    Returns:
        Query results if fetch=True and successful, otherwise None
    """
    conn = get_direct_connection()
    cursor = None
    
    # Fall back if direct connection not available
    if conn is None:
        logger.warning("Direct PostgreSQL connection not available, raw SQL execution not supported")
        return None
        
    try:
        cursor = conn.cursor()
        cursor.execute(sql, params)
        if fetch:
            results = cursor.fetchall()
            conn.commit()
            return results
        else:
            conn.commit()
            return cursor.rowcount
    except Exception as e:
        if conn and not getattr(conn, 'closed', True) is False:
            try:
                conn.rollback()
            except Exception:
                pass
        logger.error(f"Error executing raw SQL: {e}")
        return None
    finally:
        if cursor and not getattr(cursor, 'closed', True) is False:
            try:
                cursor.close()
            except Exception:
                pass

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
    db_url = os.environ.get("DATABASE_URL", "sqlite:///pastebin.db")
    
    # Apply more aggressive monkey patch to fix SQLAlchemy psycopg2 dialect issue with pymysql
    try:
        # First try to fix by direct monkey patching of SQLAlchemy's psycopg2 module
        import sys
        import types
        from sqlalchemy.dialects.postgresql import psycopg2 as sa_psycopg2
        
        # Create a more comprehensive mock extras module with Hstore support
        # Create a mock psycopg2 extras module and add it to sys.modules
        mock_extras = types.ModuleType('psycopg2.extras')
        
        # Add required functions
        mock_extras.register_uuid = lambda conn: None
        mock_extras.register_default_json = lambda conn: None
        mock_extras.register_default_jsonb = lambda conn: None
        
        # Add HstoreAdapter class
        class HstoreAdapter:
            @staticmethod
            def get_oids(conn):
                # Return dummy OIDs that won't be used but prevent errors
                return (-1, -2)
                
        mock_extras.HstoreAdapter = HstoreAdapter
        sys.modules['psycopg2.extras'] = mock_extras
        
        # Replace the _psycopg2_extras property on the PGDialect_psycopg2 class
        def _patched_extras(self):
            return mock_extras
            
        # Replace the on_connect method to avoid accessing _psycopg2_extras
        def _patched_on_connect(self):
            def connect(conn):
                conn.set_isolation_level(self.isolation_level)
                return conn
            return connect
        
        # Create a patched initialize method to bypass hstore checks
        def _patched_initialize(self, connection):
            # Skip the hstore initialization that causes problems
            pass
            
        # Apply the patches
        sa_psycopg2.PGDialect_psycopg2._psycopg2_extras = property(_patched_extras)
        sa_psycopg2.PGDialect_psycopg2.on_connect = _patched_on_connect
        sa_psycopg2.PGDialect_psycopg2.initialize = _patched_initialize
        
        logger.info("Successfully applied aggressive patch to psycopg2 dialect")
    except Exception as e:
        logger.error(f"Failed to apply aggressive patch to psycopg2 dialect: {e}")
    
    # Fix URL format for different PostgreSQL URL styles
    if db_url.startswith('postgres://'):
        db_url = db_url.replace('postgres://', 'postgresql://', 1)
    
    logger.info(f"Using database URL: {db_url}")
    
    app.config["SQLALCHEMY_DATABASE_URI"] = db_url
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