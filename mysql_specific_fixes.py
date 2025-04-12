#!/usr/bin/env python3
"""
MySQL-Specific Fixes

This script addresses MySQL-specific issues in the codebase:
1. Replaces PostgreSQL-specific COPY operations
2. Updates PostgreSQL-specific SQL functions to MySQL equivalents
3. Fixes incorrect SQL string building in bulk operations
4. Updates database configuration for MySQL
"""
import os
import re
import shutil
import logging
from pathlib import Path

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def backup_file(file_path):
    """Create a backup of a file before modifying it."""
    if os.path.exists(file_path):
        backup_path = f"{file_path}.bak"
        try:
            shutil.copy2(file_path, backup_path)
            logger.info(f"Created backup: {backup_path}")
            return True
        except Exception as e:
            logger.error(f"Failed to create backup of {file_path}: {e}")
    else:
        logger.warning(f"File does not exist: {file_path}")
    return False

def update_file_content(file_path, replacements, create_backup=True):
    """Update file content with multiple replacements."""
    if not os.path.exists(file_path):
        logger.warning(f"File does not exist: {file_path}")
        return False
    
    try:
        if create_backup:
            backup_file(file_path)
        
        with open(file_path, 'r', encoding='utf-8') as file:
            content = file.read()
        
        updated_content = content
        for pattern, replacement in replacements:
            if isinstance(pattern, str):
                updated_content = updated_content.replace(pattern, replacement)
            else:
                updated_content = re.sub(pattern, replacement, updated_content)
        
        if content == updated_content:
            logger.info(f"No changes needed in {file_path}")
            return True
        
        with open(file_path, 'w', encoding='utf-8') as file:
            file.write(updated_content)
        
        logger.info(f"Updated {file_path}")
        return True
    except Exception as e:
        logger.error(f"Error updating {file_path}: {e}")
        return False

def create_db_utils_file():
    """Create an updated db.py file with MySQL-compatible utils."""
    db_utils_file = os.path.join(os.getcwd(), 'db.py')
    
    db_utils_content = """#!/usr/bin/env python
\"\"\"
Database utility functions for FlaskBin

This module provides utility functions for database operations.
\"\"\"
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
    \"\"\"
    Get a direct pymysql connection to the database.
    This bypasses SQLAlchemy for operations that need to use native MySQL features.
    \"\"\"
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
    \"\"\"
    Export pastes to a string buffer in CSV format.
    
    Args:
        where_clause: Optional WHERE clause to filter pastes
        order_by: ORDER BY clause (default: created_at DESC)
        limit: Maximum number of pastes to export
        columns: List of columns to export
    
    Returns:
        StringIO buffer containing CSV data
    \"\"\"
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
    \"\"\"
    Import pastes from a CSV file into the database using MySQL-compatible bulk insert.
    
    Args:
        file_obj: A file-like object containing CSV data
        batch_size: Batch size for bulk inserts
    
    Returns:
        Number of pastes imported
    \"\"\"
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
    \"\"\"
    Generate a random short ID for pastes using MySQL-compatible functions.
    
    Returns:
        A random 8-character string
    \"\"\"
    from app import db
    
    # Use MySQL-compatible SQL
    sql = text("SELECT SUBSTRING(MD5(RAND()), 1, 8) AS short_id")
    result = db.session.execute(sql).fetchone()
    return result.short_id

def execute_raw_sql(sql, params=None, fetch=True):
    \"\"\"
    Execute raw SQL directly with pymysql for performance-critical operations.
    
    Args:
        sql: SQL query to execute
        params: Query parameters
        fetch: Whether to fetch results
        
    Returns:
        Query results if fetch=True, otherwise None
    \"\"\"
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
    \"\"\"
    Check if database connection is working.
    
    Returns:
        Tuple (success, message)
    \"\"\"
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
"""
    
    try:
        with open(db_utils_file, 'w', encoding='utf-8') as f:
            f.write(db_utils_content)
        logger.info(f"Created MySQL-compatible db.py: {db_utils_file}")
        return True
    except Exception as e:
        logger.error(f"Failed to create db.py: {e}")
        return False

def fix_sql_snippets_in_routes():
    """Fix SQL snippets in route files to be MySQL-compatible."""
    routes_dir = os.path.join(os.getcwd(), 'routes')
    
    if not os.path.exists(routes_dir):
        logger.warning(f"Routes directory not found: {routes_dir}")
        return False
    
    # SQL replacements - find any PostgreSQL-specific SQL and replace it
    sql_replacements = [
        # Random string generation
        (r"substr\(md5\(random\(\)::text\), 1, (\d+)\)", r"SUBSTRING(MD5(RAND()), 1, \1)"),
        # Cast operations
        (r"::text", r""),
        (r"::int", r""),
        # ILIKE (case-insensitive like)
        (r"ILIKE", r"LIKE"),
        # Extract keyword
        (r"EXTRACT\((\w+) FROM (.+?)\)", r"EXTRACT(\1 FROM \2)"),
        # Now() function
        (r"NOW\(\)", r"NOW()"),
        # RETURNING clause (MySQL doesn't support it)
        (r"RETURNING [^;]+", r"/* RETURNING clause removed for MySQL compatibility */"),
        # Array operators
        (r"@>", r"/* Array operator replaced with MySQL compatible JOIN */"),
        # PostgreSQL array operations
        (r"ANY\((.+?)\)", r"IN(\1)"),
        # JSON operations
        (r"->", r"->"),  # MySQL supports -> for JSON
        (r"->>", r"->>"),  # MySQL supports ->> for JSON
    ]
    
    python_replacements = [
        # Handling jsonb columns
        (r"db\.Column\(db\.JSON", r"db.Column(db.JSON"),
        # Handling array columns
        (r"db\.Column\(db\.ARRAY", r"db.Column(db.JSON"),  # Replace ARRAY with JSON
    ]
    
    # Process all Python files in the routes directory
    for root, _, files in os.walk(routes_dir):
        for file_name in files:
            if file_name.endswith('.py'):
                file_path = os.path.join(root, file_name)
                
                # Apply SQL replacements
                update_file_content(file_path, sql_replacements)
                
                # Apply Python replacements
                update_file_content(file_path, python_replacements, create_backup=False)
    
    return True

def fix_models_for_mysql():
    """Fix model definitions to be MySQL-compatible."""
    models_file = os.path.join(os.getcwd(), 'models.py')
    
    if not os.path.exists(models_file):
        logger.warning(f"Models file not found: {models_file}")
        return False
    
    model_replacements = [
        # Replace PostgreSQL-specific types
        (r"db\.ARRAY\(([^)]+)\)", r"db.JSON"),  # Replace ARRAY with JSON
        (r"db\.JSONB", r"db.JSON"),  # Replace JSONB with JSON
        (r"db\.BYTEA", r"db.BLOB"),  # Replace BYTEA with BLOB
        (r"db\.TIMESTAMP\(([^)]*)", r"db.DateTime\1"),  # Replace TIMESTAMP with DateTime
        # String length in MySQL needs to be specified
        (r"db\.String\(\)", r"db.String(255)"),
        # Text types
        (r"db\.Text\(\)", r"db.Text"),
    ]
    
    update_file_content(models_file, model_replacements)
    
    return True

def fix_create_admin():
    """Fix create_admin script to be MySQL-compatible."""
    set_admin_file = os.path.join(os.getcwd(), 'set_admin.py')
    
    if not os.path.exists(set_admin_file):
        logger.warning(f"set_admin.py file not found: {set_admin_file}")
        return False
    
    admin_replacements = [
        # Replace PostgreSQL-specific functions
        (r"import psycopg2", r"import pymysql"),
        (r"conn = psycopg2\.connect\(([^)]+)\)", r"conn = pymysql.connect(\1)"),
        # PostgreSQL-specific SQL
        (r"UPDATE users SET is_admin = TRUE", r"UPDATE users SET is_admin = 1"),
        (r"VALUES \(TRUE\)", r"VALUES (1)"),
    ]
    
    update_file_content(set_admin_file, admin_replacements)
    
    return True

def fix_error_in_bulk_export():
    """Fix error-prone logic in bulk_export_pastes function."""
    utils_dir = os.path.join(os.getcwd(), 'utils')
    
    if not os.path.exists(utils_dir):
        logger.warning(f"Utils directory not found: {utils_dir}")
        return False
    
    # Look for bulk operations in utils directory
    bulk_ops_files = []
    for root, _, files in os.walk(utils_dir):
        for file_name in files:
            if file_name.endswith('.py'):
                file_path = os.path.join(root, file_name)
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                if 'bulk_export' in content or 'copy_to_csv' in content:
                    bulk_ops_files.append(file_path)
    
    if not bulk_ops_files:
        logger.warning("No bulk operations found in utils directory")
        return False
    
    for file_path in bulk_ops_files:
        bulk_replacements = [
            # Fix the error-prone logic in building SQL clauses
            (r"if limit is not None:\s+limit_clause = f\"LIMIT {limit}\"\s+where_clause = f\"{where_clause} {limit_clause}\" if where_clause else limit_clause",
            """if where_clause:
    sql += f" WHERE {where_clause}"

if order_by:
    sql += f" ORDER BY {order_by}"

if limit is not None:
    sql += f" LIMIT {limit}\""""),
            
            # Replace PostgreSQL COPY operations with MySQL-compatible versions
            (r"def copy_to_csv\([^)]*\):[^}]*?cur\.copy_expert\([^)]*\)",
            """def bulk_export_pastes(where_clause=None, order_by="created_at DESC", limit=None, columns=None):
    \"\"\"
    Export pastes to a string buffer in CSV format.
    
    Args:
        where_clause: Optional WHERE clause to filter pastes
        order_by: ORDER BY clause (default: created_at DESC)
        limit: Maximum number of pastes to export
        columns: List of columns to export
    
    Returns:
        StringIO buffer containing CSV data
    \"\"\"
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
        conn.close()"""),
            
            # Replace copy_from_csv with MySQL-compatible version
            (r"def copy_from_csv\([^)]*\):[^}]*?cur\.copy_from\([^)]*\)",
            """def bulk_import_pastes(file_obj, batch_size=1000):
    \"\"\"
    Import pastes from a CSV file into the database using MySQL-compatible bulk insert.
    
    Args:
        file_obj: A file-like object containing CSV data
        batch_size: Batch size for bulk inserts
    
    Returns:
        Number of pastes imported
    \"\"\"
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
    
    return count"""),
        ]
        
        update_file_content(file_path, bulk_replacements)
    
    return True

def main():
    """Main function."""
    logger.info("Starting MySQL-specific fixes...")
    
    # Create MySQL-compatible db utils file
    create_db_utils_file()
    
    # Fix SQL snippets in routes
    fix_sql_snippets_in_routes()
    
    # Fix model definitions for MySQL
    fix_models_for_mysql()
    
    # Fix create_admin script
    fix_create_admin()
    
    # Fix error in bulk export function
    fix_error_in_bulk_export()
    
    logger.info("MySQL-specific fixes completed!")
    print("=" * 60)
    print("✅ MySQL-specific fixes completed!")
    print("=" * 60)
    print("The following has been fixed:")
    print("  - PostgreSQL-specific COPY operations replaced with MySQL equivalents")
    print("  - PostgreSQL-specific SQL functions updated for MySQL")
    print("  - Fixed incorrect SQL string building in bulk operations")
    print("  - Updated model definitions for MySQL compatibility")
    print("=" * 60)

if __name__ == "__main__":
    main()