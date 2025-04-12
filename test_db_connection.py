"""
Test database connection script.
This script tests the connection to the database and prints the status.
"""
import sys
import psycopg2
import time

# Database connection parameters
DB_PARAMS = {
    'host': 'srv734.hstgr.io',
    'user': 'u213077714_flaskbin',
    'password': 'hOJ27K?5',
    'database': 'u213077714_flaskbin',
    'port': 5432  # Default PostgreSQL port
}

def test_connection():
    """Test the database connection and print results."""
    print("\n" + "="*50)
    print("DATABASE CONNECTION TEST")
    print("="*50)
    
    print(f"\nAttempting to connect to database:")
    print(f"  Host:     {DB_PARAMS['host']}")
    print(f"  Database: {DB_PARAMS['database']}")
    print(f"  User:     {DB_PARAMS['user']}")
    print(f"  Port:     {DB_PARAMS['port']}")
    
    try:
        # Attempt connection
        start_time = time.time()
        print("\nConnecting...", end="", flush=True)
        
        conn = psycopg2.connect(
            host=DB_PARAMS['host'],
            database=DB_PARAMS['database'],
            user=DB_PARAMS['user'],
            password=DB_PARAMS['password'],
            port=DB_PARAMS['port'],
            connect_timeout=10
        )
        
        # Check if we can execute a simple query
        cursor = conn.cursor()
        cursor.execute("SELECT 1")
        result = cursor.fetchone()
        
        end_time = time.time()
        connection_time = end_time - start_time
        
        print(f" SUCCESS! ({connection_time:.2f}s)")
        print("\n✅ DATABASE CONNECTION SUCCESSFUL")
        
        # Get PostgreSQL version to verify connectivity
        cursor.execute("SELECT version()")
        version = cursor.fetchone()[0]
        print(f"\nServer information:")
        print(f"  {version}")
        
        # List tables in the database
        try:
            print("\nTables in the database:")
            cursor.execute("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public'
                ORDER BY table_name
            """)
            tables = cursor.fetchall()
            
            if tables:
                for i, table in enumerate(tables, 1):
                    print(f"  {i}. {table[0]}")
            else:
                print("  No tables found in the public schema.")
        except Exception as e:
            print(f"  Could not list tables: {e}")
        
        # Close cursor and connection
        cursor.close()
        conn.close()
        
    except psycopg2.OperationalError as e:
        print(" FAILED!")
        print(f"\n❌ CONNECTION ERROR:")
        print(f"  {str(e).strip()}")
        print("\nPossible reasons:")
        print("  • Database server is not reachable")
        print("  • Incorrect host, username, or password")
        print("  • Database does not exist")
        print("  • Firewall blocking the connection")
        return False
        
    except Exception as e:
        print(" FAILED!")
        print(f"\n❌ UNEXPECTED ERROR:")
        print(f"  {type(e).__name__}: {str(e).strip()}")
        return False
    
    print("\n" + "="*50)
    return True

if __name__ == "__main__":
    success = test_connection()
    if not success:
        sys.exit(1)  # Exit with error code