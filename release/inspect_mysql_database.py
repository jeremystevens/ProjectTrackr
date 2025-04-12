"""
Inspect MySQL database structure and tables.
This script connects to the MySQL database and retrieves detailed information
about the database structure to help with migration.
"""
import pymysql
import sys
from tabulate import tabulate

# Database connection parameters
HOST = '185.212.71.204'
USER = 'u213077714_flaskbin'
PASSWORD = 'hOJ27K?5'
DATABASE = 'u213077714_flaskbin'
PORT = 3306

def connect_to_database():
    """Establish connection to the MySQL database."""
    try:
        print(f"Connecting to MySQL database at {HOST}...")
        conn = pymysql.connect(
            host=HOST,
            port=PORT,
            user=USER,
            password=PASSWORD,
            database=DATABASE,
            connect_timeout=10
        )
        print("✅ Connection successful!")
        return conn
    except Exception as e:
        print(f"❌ Connection failed: {e}")
        sys.exit(1)

def get_tables(conn):
    """Get list of tables in the database."""
    cursor = conn.cursor()
    cursor.execute("SHOW TABLES")
    tables = [table[0] for table in cursor.fetchall()]
    cursor.close()
    return tables

def get_table_structure(conn, table_name):
    """Get detailed structure of a specific table."""
    cursor = conn.cursor()
    cursor.execute(f"DESCRIBE `{table_name}`")
    columns = cursor.fetchall()
    
    structure = []
    for column in columns:
        structure.append({
            "Field": column[0],
            "Type": column[1],
            "Null": column[2],
            "Key": column[3],
            "Default": column[4],
            "Extra": column[5]
        })
    
    cursor.close()
    return structure

def count_rows(conn, table_name):
    """Count rows in a table."""
    cursor = conn.cursor()
    cursor.execute(f"SELECT COUNT(*) FROM `{table_name}`")
    count = cursor.fetchone()[0]
    cursor.close()
    return count

def get_foreign_keys(conn, table_name):
    """Get foreign key constraints for a table."""
    cursor = conn.cursor()
    cursor.execute(f"""
        SELECT 
            TABLE_NAME, COLUMN_NAME, 
            REFERENCED_TABLE_NAME, REFERENCED_COLUMN_NAME
        FROM
            INFORMATION_SCHEMA.KEY_COLUMN_USAGE
        WHERE
            REFERENCED_TABLE_SCHEMA = '{DATABASE}' AND
            TABLE_NAME = '{table_name}'
    """)
    fk_constraints = cursor.fetchall()
    cursor.close()
    return fk_constraints

def generate_flask_sqlalchemy_model(table_name, structure, foreign_keys):
    """Generate Flask-SQLAlchemy model representation."""
    model_name = ''.join(word.capitalize() for word in table_name.split('_'))
    
    model_code = [
        f"class {model_name}(db.Model):",
        f"    __tablename__ = '{table_name}'",
        ""
    ]
    
    for column in structure:
        field = column["Field"]
        col_type = column["Type"].lower()
        is_nullable = column["Null"] == "YES"
        is_primary = column["Key"] == "PRI"
        default = column["Default"]
        extra = column["Extra"]
        
        # Map MySQL types to SQLAlchemy types
        sa_type = "db.String"
        if "int" in col_type:
            sa_type = "db.Integer"
        elif "float" in col_type or "double" in col_type or "decimal" in col_type:
            sa_type = "db.Float"
        elif "datetime" in col_type or "timestamp" in col_type:
            sa_type = "db.DateTime"
        elif "date" in col_type:
            sa_type = "db.Date"
        elif "time" in col_type:
            sa_type = "db.Time"
        elif "text" in col_type:
            sa_type = "db.Text"
        elif "blob" in col_type:
            sa_type = "db.LargeBinary"
        elif "bool" in col_type or "tinyint(1)" in col_type:
            sa_type = "db.Boolean"
        elif "varchar" in col_type or "char" in col_type:
            # Extract length from type like varchar(255)
            length = col_type.split('(')[1].split(')')[0] if '(' in col_type else "255"
            sa_type = f"db.String({length})"
        
        # Build column definition
        column_def = f"    {field} = {sa_type}("
        
        # Add constraints
        constraints = []
        if is_primary:
            constraints.append("primary_key=True")
        if not is_nullable:
            constraints.append("nullable=False")
        if default is not None and default != "NULL":
            if "int" in col_type or "float" in col_type or "double" in col_type:
                constraints.append(f"default={default}")
            else:
                constraints.append(f"default='{default}'")
        if "auto_increment" in extra:
            constraints.append("autoincrement=True")
        
        column_def += ", ".join(constraints) + ")"
        model_code.append(column_def)
    
    # Add foreign key relationships
    for fk in foreign_keys:
        related_table = fk[2]
        related_model = ''.join(word.capitalize() for word in related_table.split('_'))
        field = fk[1]
        relationship_name = related_table.lower()
        
        model_code.append(f"    # Foreign key to {related_table}.{fk[3]}")
        model_code.append(f"    {relationship_name} = db.relationship('{related_model}', backref='{table_name}')")
    
    return "\n".join(model_code)

def main():
    """Main function to inspect MySQL database."""
    print("\n" + "="*60)
    print(f"MYSQL DATABASE INSPECTION: {DATABASE}")
    print("="*60)
    
    conn = connect_to_database()
    tables = get_tables(conn)
    
    print(f"\nFound {len(tables)} tables:")
    
    # Display tables and row counts
    table_data = []
    for i, table in enumerate(tables, 1):
        row_count = count_rows(conn, table)
        table_data.append([i, table, row_count])
    
    print(tabulate(table_data, headers=["#", "Table Name", "Row Count"], tablefmt="grid"))
    
    # Display detailed table information
    for table in tables:
        print("\n" + "-"*60)
        print(f"TABLE: {table}")
        print("-"*60)
        
        # Get and display table structure
        structure = get_table_structure(conn, table)
        headers = structure[0].keys() if structure else []
        rows = [list(col.values()) for col in structure]
        print("COLUMNS:")
        print(tabulate(rows, headers=headers, tablefmt="grid"))
        
        # Get and display foreign keys
        foreign_keys = get_foreign_keys(conn, table)
        if foreign_keys:
            print("\nFOREIGN KEYS:")
            fk_headers = ["Table", "Column", "Referenced Table", "Referenced Column"]
            print(tabulate(foreign_keys, headers=fk_headers, tablefmt="grid"))
        
        # Generate and display Flask-SQLAlchemy model
        print("\nFlask-SQLAlchemy Model:")
        model_code = generate_flask_sqlalchemy_model(table, structure, foreign_keys)
        print("-" * 60)
        print(model_code)
        print("-" * 60)
    
    conn.close()
    print("\n" + "="*60)
    print("INSPECTION COMPLETE")
    print("\nTo use this MySQL database with Flask, you will need:")
    print("1. Update your requirements.txt to include pymysql")
    print("2. Change your DATABASE_URL format to:")
    print(f"   mysql+pymysql://{USER}:{PASSWORD}@{HOST}:{PORT}/{DATABASE}")
    print("3. Ensure your SQLAlchemy models match the structure shown above")
    print("="*60)

if __name__ == "__main__":
    main()