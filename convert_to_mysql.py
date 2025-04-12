#!/usr/bin/env python
"""
Convert To MySQL Script

This script completely converts the FlaskBin project from PostgreSQL to MySQL,
updating all necessary files and configurations.
"""
import os
import sys
import re
import shutil
from pathlib import Path

# MySQL Database configuration
DB_CONFIG = {
    'host': '185.212.71.204',
    'user': 'u213077714_flaskbin',
    'password': 'hOJ27K?5',
    'database': 'u213077714_flaskbin',
    'port': 3306
}

# The MySQL connection string to use in the application
MYSQL_CONNECTION_STRING = f"mysql+pymysql://{DB_CONFIG['user']}:{DB_CONFIG['password']}@{DB_CONFIG['host']}:{DB_CONFIG['port']}/{DB_CONFIG['database']}"

# Required packages for MySQL
REQUIRED_PACKAGES = ["pymysql"]

def backup_file(file_path):
    """Create a backup of a file before modifying it."""
    if os.path.exists(file_path):
        backup_path = f"{file_path}.bak"
        shutil.copy2(file_path, backup_path)
        print(f"✅ Created backup: {backup_path}")
        return True
    return False

def update_file(file_path, replacements, create_backup=True):
    """
    Update a file with multiple replacements.
    
    Args:
        file_path: Path to the file to update
        replacements: List of (pattern, replacement) tuples
        create_backup: Whether to create a backup of the original file
    
    Returns:
        bool: True if successful, False otherwise
    """
    if not os.path.exists(file_path):
        print(f"⚠️ File not found: {file_path}")
        return False
    
    try:
        # Create backup if needed
        if create_backup:
            backup_file(file_path)
        
        with open(file_path, 'r', encoding='utf-8') as file:
            content = file.read()
        
        updated_content = content
        for pattern, replacement in replacements:
            if isinstance(pattern, str):
                # Simple string replacement
                updated_content = updated_content.replace(pattern, replacement)
            else:
                # Regex replacement
                updated_content = re.sub(pattern, replacement, updated_content)
        
        if content == updated_content:
            print(f"ℹ️ No changes needed in {file_path}")
            return True
        
        with open(file_path, 'w', encoding='utf-8') as file:
            file.write(updated_content)
        
        print(f"✅ Updated {file_path}")
        return True
    except Exception as e:
        print(f"❌ Error updating {file_path}: {e}")
        return False

def update_db_py():
    """Update db.py with MySQL configuration."""
    file_path = 'db.py'
    replacements = [
        # Update import statement
        (r"import psycopg2(\s+)", "import pymysql\\1"),
        
        # Update connection string
        (r"(DATABASE_URL\s*=\s*os\.environ\.get\(['\"]DATABASE_URL['\"][^)]*\))",
         f"DATABASE_URL = os.environ.get('DATABASE_URL', '{MYSQL_CONNECTION_STRING}')"),
        
        # Update get_direct_connection function
        (r"def get_direct_connection\(\)[^}]*?return\s+psycopg2\.connect\(([^)]*)\)",
         f"""def get_direct_connection():
    \"\"\"
    Get a direct pymysql connection to the database.
    This bypasses SQLAlchemy for operations that need to use native MySQL features.
    \"\"\"
    connection_params = {{}}
    
    # Parse the DATABASE_URL
    if 'mysql+pymysql://' in DATABASE_URL:
        # Parse MySQL URL format
        url_parts = DATABASE_URL.replace('mysql+pymysql://', '').split('@')
        auth_parts = url_parts[0].split(':')
        host_parts = url_parts[1].split('/')
        port_parts = host_parts[0].split(':')
        
        connection_params = {{
            'host': port_parts[0],
            'port': int(port_parts[1]) if len(port_parts) > 1 else 3306,
            'user': auth_parts[0],
            'password': auth_parts[1],
            'database': host_parts[1]
        }}
    else:
        # Use hardcoded parameters as fallback
        connection_params = {{
            'host': '{DB_CONFIG['host']}',
            'port': {DB_CONFIG['port']},
            'user': '{DB_CONFIG['user']}',
            'password': '{DB_CONFIG['password']}',
            'database': '{DB_CONFIG['database']}'
        }}
    
    return pymysql.connect(**connection_params)"""),
        
        # Update copy_from_csv function for MySQL
        (r"def copy_from_csv\([^)]*\):[^}]*?cur\.copy_from\([^)]*\)",
         """def copy_from_csv(file_obj, table_name, columns=None, delimiter=','):
    \"\"\"
    Use MySQL's LOAD DATA LOCAL INFILE to load data from a CSV file.
    
    Args:
        file_obj: A file-like object containing CSV data
        table_name: Target table name
        columns: List of column names to insert into
        delimiter: CSV delimiter character
    
    Returns:
        Number of rows inserted
    \"\"\"
    conn = get_direct_connection()
    cursor = conn.cursor()
    
    # Save file content to a temporary file
    import tempfile
    with tempfile.NamedTemporaryFile(mode='w+', delete=False) as temp_file:
        temp_file.write(file_obj.read())
        temp_path = temp_file.name
    
    try:
        # Build the SQL statement
        column_names = ''
        if columns:
            column_names = f"({', '.join(columns)})"
        
        # Execute the LOAD DATA INFILE statement
        sql = f\"\"\"
        LOAD DATA LOCAL INFILE '{temp_path}'
        INTO TABLE {table_name} 
        FIELDS TERMINATED BY '{delimiter}'
        LINES TERMINATED BY '\\n'
        IGNORE 1 ROWS
        {column_names}
        \"\"\"
        
        cursor.execute(sql)
        conn.commit()
        rows_affected = cursor.rowcount
        
        return rows_affected
    finally:
        cursor.close()
        conn.close()
        os.unlink(temp_path)"""),
        
        # Update copy_to_csv function for MySQL
        (r"def copy_to_csv\([^)]*\):[^}]*?cur\.copy_expert\([^)]*\)",
         """def copy_to_csv(file_obj, table_name, columns=None, delimiter=',', where_clause=None):
    \"\"\"
    Export data to a CSV file using MySQL.
    
    Args:
        file_obj: A file-like object to write CSV data to
        table_name: Source table name
        columns: List of column names to export
        delimiter: CSV delimiter character
        where_clause: Optional WHERE clause to filter data
    \"\"\"
    conn = get_direct_connection()
    cursor = conn.cursor()
    
    try:
        # Build column list
        column_expr = '*'
        if columns:
            column_expr = ', '.join(columns)
        
        # Build WHERE clause
        where_expr = ''
        if where_clause:
            where_expr = f"WHERE {where_clause}"
        
        # Execute the query
        sql = f"SELECT {column_expr} FROM {table_name} {where_expr}"
        cursor.execute(sql)
        
        # Write the header row
        if columns:
            file_obj.write(delimiter.join(columns) + '\\n')
        else:
            # Get column names from cursor description
            header = [column[0] for column in cursor.description]
            file_obj.write(delimiter.join(header) + '\\n')
        
        # Write the data rows
        for row in cursor:
            # Convert all values to strings and handle None values
            row_values = [str(value) if value is not None else '' for value in row]
            file_obj.write(delimiter.join(row_values) + '\\n')
    finally:
        cursor.close()
        conn.close()"""),
        
        # Update execute_raw_sql function
        (r"def execute_raw_sql\([^)]*\):.*?cur\.execute\([^)]*\)",
         """def execute_raw_sql(sql, params=None, fetch=True):
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
        cursor.execute(sql, params)"""),
    ]
    
    return update_file(file_path, replacements)

def update_app_py():
    """Update app.py with MySQL configuration."""
    file_path = 'app.py'
    replacements = [
        # Add pymysql import if needed
        (r"import os(\s+)", "import os\\1import pymysql\\1"),
        
        # Update database connection string
        (r'app\.config\["SQLALCHEMY_DATABASE_URI"\]\s*=\s*os\.environ\.get\(["\']DATABASE_URL["\'][^)]*\)',
         f'app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL", "{MYSQL_CONNECTION_STRING}")'),
    ]
    
    return update_file(file_path, replacements)

def update_main_py():
    """Update main.py with MySQL imports."""
    file_path = 'main.py'
    replacements = [
        # Add pymysql import if needed
        (r"import os(\s+)", "import os\\1import pymysql\\1"),
        
        # Update any PostgreSQL specific code
        ("psycopg2", "pymysql"),
    ]
    
    return update_file(file_path, replacements)

def update_wsgi_py():
    """Update wsgi.py with MySQL configuration."""
    file_path = 'wsgi.py'
    replacements = [
        # Add pymysql import at the top
        (r"import os(\s+)", "import os\\1import pymysql\\1"),
        
        # Update database connection string
        (r'SQLALCHEMY_DATABASE_URI=os\.environ\.get\(["\']DATABASE_URL["\'][^)]*\)',
         f'SQLALCHEMY_DATABASE_URI=os.environ.get("DATABASE_URL", "{MYSQL_CONNECTION_STRING}")'),
    ]
    
    return update_file(file_path, replacements)

def update_models_py():
    """Update models.py if needed."""
    file_path = 'models.py'
    replacements = [
        # Update any PostgreSQL specific data types to MySQL equivalents
        ("BYTEA", "BLOB"),
        ("JSONB", "JSON"),
        ("TIMESTAMPTZ", "DATETIME"),
    ]
    
    return update_file(file_path, replacements)

def update_requirements_txt():
    """Update requirements.txt to include pymysql."""
    file_path = 'requirements.txt'
    
    # If file doesn't exist, create it
    if not os.path.exists(file_path):
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write("pymysql==1.1.0\n")
        print(f"✅ Created {file_path} with pymysql")
        return True
    
    # Otherwise update existing file
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Check if pymysql is already in requirements
    if 'pymysql' in content.lower():
        print(f"ℹ️ pymysql already in {file_path}")
        return True
    
    # Add pymysql to requirements
    with open(file_path, 'a', encoding='utf-8') as f:
        f.write("\npymysql==1.1.0\n")
    
    print(f"✅ Added pymysql to {file_path}")
    return True

def create_env_file():
    """Create or update .env file with MySQL configuration."""
    file_path = '.env'
    env_content = f"""# Environment variables for FlaskBin
DATABASE_URL="{MYSQL_CONNECTION_STRING}"
SESSION_SECRET="your-secure-session-secret-replace-in-production"
"""
    
    backup_file(file_path)
    
    try:
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(env_content)
        print(f"✅ Created {file_path} with MySQL configuration")
        return True
    except Exception as e:
        print(f"❌ Failed to create {file_path}: {e}")
        return False

def update_render_yaml():
    """Update render.yaml with MySQL environment variable."""
    file_path = 'render.yaml'
    if not os.path.exists(file_path):
        print(f"ℹ️ {file_path} not found, skipping")
        return True
    
    replacements = [
        (r"DATABASE_URL:[^\n]*",
         f'DATABASE_URL: "{MYSQL_CONNECTION_STRING}"')
    ]
    
    return update_file(file_path, replacements)

def update_migration_scripts():
    """Update database migration scripts to use MySQL."""
    # Find all Python files that might contain migration scripts
    migration_files = []
    for file in Path('.').glob('*.py'):
        if file.name.startswith('add_') or 'migration' in file.name.lower():
            migration_files.append(file)
    
    print(f"Found {len(migration_files)} potential migration scripts")
    
    for file_path in migration_files:
        replacements = [
            # Update imports
            (r"import psycopg2(\s+)", "import pymysql\\1"),
            
            # Update connection strings
            (r"psycopg2\.connect\([^)]*\)",
             f"pymysql.connect(host='{DB_CONFIG['host']}', user='{DB_CONFIG['user']}', password='{DB_CONFIG['password']}', database='{DB_CONFIG['database']}', port={DB_CONFIG['port']})"),
            
            # Update any PostgreSQL specific SQL syntax to MySQL
            ("SERIAL PRIMARY KEY", "INT AUTO_INCREMENT PRIMARY KEY"),
            ("BYTEA", "BLOB"),
            ("BOOLEAN", "TINYINT(1)"),
            ("TEXT[]", "TEXT"),
            ("JSONB", "JSON"),
            ("TIMESTAMPTZ", "DATETIME"),
            ("RETURNING", "/* RETURNING not supported in MySQL */"),
        ]
        
        update_file(str(file_path), replacements)
    
    return True

def create_mysql_docs():
    """Create documentation about MySQL migration."""
    file_path = 'MYSQL_MIGRATION.md'
    content = f"""# MySQL Migration Documentation

## Overview

This project has been migrated from PostgreSQL to MySQL. This document outlines the changes made and how to work with the MySQL database.

## Connection Details

The application now uses MySQL with the following connection parameters:

- **Host**: {DB_CONFIG['host']}
- **Port**: {DB_CONFIG['port']}
- **Database**: {DB_CONFIG['database']}
- **User**: {DB_CONFIG['user']}
- **Password**: `{DB_CONFIG['password']}`

The full connection string is:
```
{MYSQL_CONNECTION_STRING}
```

## Environment Variables

The `DATABASE_URL` environment variable should be set to the MySQL connection string in production environments:

```
DATABASE_URL={MYSQL_CONNECTION_STRING}
```

## Database Schema

The database schema has been created in MySQL with all the necessary tables. The schema is the same as the PostgreSQL schema, but using MySQL data types.

## MySQL vs PostgreSQL Differences

Some key differences to be aware of:

1. **Data Types**:
   - PostgreSQL `SERIAL` -> MySQL `AUTO_INCREMENT`
   - PostgreSQL `BYTEA` -> MySQL `BLOB`
   - PostgreSQL `BOOLEAN` -> MySQL `TINYINT(1)`
   - PostgreSQL arrays are not supported in MySQL
   - PostgreSQL `JSONB` -> MySQL `JSON`

2. **SQL Syntax**:
   - MySQL doesn't support `RETURNING` clauses
   - MySQL uses different string functions
   - MySQL has different transaction isolation levels

3. **Performance**:
   - Indexes work differently
   - Query optimization may require different approaches

## Accessing the Database

You can access the MySQL database using phpMyAdmin or any MySQL client like MySQL Workbench.

## Troubleshooting

Common issues when working with MySQL:

1. **Connection Errors**: Make sure the host is accessible and firewall rules allow connections
2. **Authentication Errors**: Verify username and password
3. **Schema Errors**: MySQL is case-sensitive for table names on some platforms

"""
    
    try:
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"✅ Created {file_path} with MySQL migration documentation")
        return True
    except Exception as e:
        print(f"❌ Failed to create {file_path}: {e}")
        return False

def update_all_sql_references():
    """Scan all Python files for PostgreSQL-specific code and update to MySQL."""
    # Get list of all Python files
    python_files = list(Path('.').glob('**/*.py'))
    python_files = [file for file in python_files if 'venv' not in str(file) and '.git' not in str(file)]
    
    print(f"Scanning {len(python_files)} Python files for PostgreSQL references...")
    
    for file_path in python_files:
        # Skip the conversion script itself
        if file_path.name == 'convert_to_mysql.py':
            continue
            
        # Load file content
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                
            # Check if file contains PostgreSQL references
            contains_pg = any(term in content for term in [
                'psycopg2', 'postgresql', 'postgres', 'pg_', 'SERIAL', 'RETURNING', 'BYTEA'
            ])
            
            if contains_pg:
                print(f"Found PostgreSQL references in {file_path}")
                
                replacements = [
                    # Update imports
                    (r"import psycopg2(\s+)", "import pymysql\\1"),
                    (r"from psycopg2", "from pymysql"),
                    
                    # Update connection strings
                    (r"psycopg2\.connect\([^)]*\)",
                     f"pymysql.connect(host='{DB_CONFIG['host']}', user='{DB_CONFIG['user']}', password='{DB_CONFIG['password']}', database='{DB_CONFIG['database']}', port={DB_CONFIG['port']})"),
                     
                    # Update any PostgreSQL specific SQL syntax to MySQL
                    ("SERIAL PRIMARY KEY", "INT AUTO_INCREMENT PRIMARY KEY"),
                    ("BYTEA", "BLOB"),
                    ("BOOLEAN DEFAULT", "TINYINT(1) DEFAULT"),
                    ("TEXT[]", "TEXT"),
                    ("JSONB", "JSON"),
                    ("TIMESTAMPTZ", "DATETIME"),
                    
                    # Update connectionstrings
                    (r"postgresql://[^\"'\s]+", MYSQL_CONNECTION_STRING),
                    (r"postgres://[^\"'\s]+", MYSQL_CONNECTION_STRING),
                ]
                
                update_file(str(file_path), replacements, create_backup=False)
        except Exception as e:
            print(f"⚠️ Skipping {file_path}: {e}")
    
    return True

def main():
    """Main function to update the entire project to use MySQL."""
    print("\n" + "="*60)
    print("MYSQL MIGRATION - ENTIRE PROJECT")
    print("="*60)
    
    # Create backups directory if it doesn't exist
    if not os.path.exists('backups'):
        os.makedirs('backups')
        print("✅ Created backups directory")
    
    # Core configuration files
    print("\n📂 Updating core configuration files...")
    update_db_py()
    update_app_py()
    update_main_py()
    update_wsgi_py()
    update_models_py()
    
    # Supporting files
    print("\n📂 Updating supporting files...")
    update_requirements_txt()
    create_env_file()
    update_render_yaml()
    
    # Migration scripts
    print("\n📂 Updating migration scripts...")
    update_migration_scripts()
    
    # Scan all files for PostgreSQL references
    print("\n📂 Scanning all files for PostgreSQL references...")
    update_all_sql_references()
    
    # Create documentation
    print("\n📂 Creating documentation...")
    create_mysql_docs()
    
    print("\n" + "="*60)
    print("MYSQL MIGRATION COMPLETE")
    print("="*60)
    print("\nYour entire project has been updated to use MySQL.")
    print("The MySQL database URL is:")
    print(f"  {MYSQL_CONNECTION_STRING}")
    print("\nRestart your application to apply the changes.")
    print("See MYSQL_MIGRATION.md for more information about the migration.")

if __name__ == "__main__":
    main()