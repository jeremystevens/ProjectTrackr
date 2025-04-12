#!/usr/bin/env python
"""
Database utility functions for FlaskBin

This module provides utility functions for database operations.
"""
import os
import io
import csv
import logging
from flask import current_app
from sqlalchemy import text

# Configure logging
logger = logging.getLogger(__name__)

# Database URL is set in app.py, this is just a reference
DATABASE_URL = os.environ.get("DATABASE_URL", "mysql+pymysql://u213077714_flaskbin:hOJ27K?5@185.212.71.204:3306/u213077714_flaskbin")

def get_direct_connection():
    """
    Get a direct pymysql connection to the database.
    This bypasses SQLAlchemy for operations that need to use native MySQL features.
    """
    import pymysql
    connection_params = {}
    
    # Parse the DATABASE_URL
    if 'mysql+pymysql://' in DATABASE_URL:
        # Parse MySQL URL format
        url_parts = DATABASE_URL.replace('mysql+pymysql://', '').split('@')
        auth_parts = url_parts[0].split(':')
        host_parts = url_parts[1].split('/')
        port_parts = host_parts[0].split(':')
        
        connection_params = {
            'host': port_parts[0],
            'port': int(port_parts[1]) if len(port_parts) > 1 else 3306,
            'user': auth_parts[0],
            'password': auth_parts[1],
            'database': host_parts[1]
        }
    else:
        # Use hardcoded parameters as fallback
        connection_params = {
            'host': '185.212.71.204',
            'port': 3306,
            'user': 'u213077714_flaskbin',
            'password': 'hOJ27K?5',
            'database': 'u213077714_flaskbin'
        }
    
    return pymysql.connect(**connection_params)

def bulk_export_pastes(where_clause=None, order_by="created_at DESC", limit=None, columns=None):
    """
    Export pastes to a string buffer in CSV format.
    
    Args:
        where_clause: Optional WHERE clause to filter pastes
        order_by: ORDER BY clause (default: created_at DESC)
        limit: Maximum number of pastes to export
        columns: List of columns to export
    
    Returns:
        StringIO buffer containing CSV data
    """
    from app import db
    
    # Build SQL query using proper MySQL syntax
    column_expr = '*'
    if columns:
        column_expr = ', '.join(columns)
    
    sql = f"SELECT {column_expr} FROM pastes"
    
    if where_clause:
        sql += f" WHERE {where_clause}"
    
    if order_by:
        sql += f" ORDER BY {order_by}"
    
    if limit is not None:
        sql += f" LIMIT {limit}"
    
    # Execute the query
    conn = get_direct_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute(sql)
        
        # Create CSV in memory
        output = io.StringIO()
        writer = csv.writer(output)
        
        # Write header row
        if columns:
            writer.writerow(columns)
        else:
            # Get column names from cursor description
            header = [column[0] for column in cursor.description]
            writer.writerow(header)
        
        # Write data rows
        for row in cursor:
            # Convert all values to strings and handle None values
            row_values = [str(value) if value is not None else '' for value in row]
            writer.writerow(row_values)
        
        # Reset buffer position for reading
        output.seek(0)
        return output
    finally:
        cursor.close()
        conn.close()

def bulk_import_pastes(file_obj, batch_size=1000):
    """
    Import pastes from a CSV file into the database using MySQL-compatible bulk insert.
    
    Args:
        file_obj: A file-like object containing CSV data
        batch_size: Batch size for bulk inserts
    
    Returns:
        Number of pastes imported
    """
    from app import db
    from models import Paste
    import csv
    
    csv_reader = csv.DictReader(file_obj)
    paste_list = []
    count = 0
    
    for row in csv_reader:
        # Create Paste object
        paste = Paste()
        
        # Map columns from CSV to Paste attributes
        for key, value in row.items():
            if hasattr(paste, key) and value:
                setattr(paste, key, value)
        
        paste_list.append(paste)
        count += 1
        
        # Process in batches
        if len(paste_list) >= batch_size:
            db.session.bulk_save_objects(paste_list)
            db.session.commit()
            paste_list = []
    
    # Insert any remaining pastes
    if paste_list:
        db.session.bulk_save_objects(paste_list)
        db.session.commit()
    
    return count

def generate_short_id():
    """
    Generate a random short ID for pastes using MySQL-compatible functions.
    
    Returns:
        A random 8-character string
    """
    from app import db
    
    # Use MySQL-compatible SQL
    sql = text("SELECT SUBSTRING(MD5(RAND()), 1, 8) AS short_id")
    result = db.session.execute(sql).fetchone()
    return result.short_id

def execute_raw_sql(sql, params=None, fetch=True):
    """
    Execute raw SQL directly with pymysql for performance-critical operations.
    
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
            return results
        else:
            conn.commit()
            return cursor.rowcount
    finally:
        cursor.close()
        conn.close()

def check_database_connection():
    """
    Check if database connection is working.
    
    Returns:
        Tuple (success, message)
    """
    try:
        conn = get_direct_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT VERSION()")
        version = cursor.fetchone()
        
        cursor.close()
        conn.close()
        
        return True, f"Connected to MySQL {version[0]}"
    except Exception as e:
        return False, f"Failed to connect to database: {str(e)}"
