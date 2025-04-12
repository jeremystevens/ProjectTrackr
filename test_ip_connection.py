"""
Database connection test using direct IP address.
"""
import psycopg2
import pymysql
import socket
import time

# Database connection parameters
HOST = '185.212.71.204'  # Using IP address instead of hostname
USER = 'u213077714_flaskbin'
PASSWORD = 'hOJ27K?5'
DATABASE = 'u213077714_flaskbin'
POSTGRES_PORT = 5432
MYSQL_PORT = 3306

def check_host_reachable():
    """Test if the host is reachable via basic socket connection."""
    print("\nTesting if IP address is reachable...")
    
    # Check PostgreSQL port
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(3)
        result = sock.connect_ex((HOST, POSTGRES_PORT))
        sock.close()
        
        if result == 0:
            print(f"✅ IP {HOST} is reachable on PostgreSQL port {POSTGRES_PORT}")
            postgres_reachable = True
        else:
            print(f"❌ IP {HOST} is not reachable on PostgreSQL port {POSTGRES_PORT}")
            postgres_reachable = False
    except Exception as e:
        print(f"❌ Error checking PostgreSQL port: {e}")
        postgres_reachable = False
    
    # Check MySQL port
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(3)
        result = sock.connect_ex((HOST, MYSQL_PORT))
        sock.close()
        
        if result == 0:
            print(f"✅ IP {HOST} is reachable on MySQL port {MYSQL_PORT}")
            mysql_reachable = True
        else:
            print(f"❌ IP {HOST} is not reachable on MySQL port {MYSQL_PORT}")
            mysql_reachable = False
    except Exception as e:
        print(f"❌ Error checking MySQL port: {e}")
        mysql_reachable = False
    
    return postgres_reachable, mysql_reachable

def try_postgres_connection():
    """Try connecting to PostgreSQL database."""
    print("\nTrying PostgreSQL connection...")
    try:
        # Using direct connection parameters
        conn = psycopg2.connect(
            host=HOST,
            port=POSTGRES_PORT,
            user=USER,
            password=PASSWORD,
            database=DATABASE,
            connect_timeout=5
        )
        
        cursor = conn.cursor()
        cursor.execute("SELECT version()")
        version = cursor.fetchone()
        
        print("✅ PostgreSQL connection successful!")
        print(f"Server version: {version[0]}")
        
        # Try to get table information
        cursor.execute("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public'
            LIMIT 5
        """)
        tables = cursor.fetchall()
        
        print("Sample tables:")
        for table in tables:
            print(f"  • {table[0]}")
            
        cursor.close()
        conn.close()
        return True
    except Exception as e:
        print(f"❌ PostgreSQL connection failed: {e}")
        return False

def try_mysql_connection():
    """Try connecting to MySQL database."""
    print("\nTrying MySQL connection...")
    try:
        conn = pymysql.connect(
            host=HOST,
            port=MYSQL_PORT,
            user=USER, 
            password=PASSWORD,
            database=DATABASE,
            connect_timeout=5
        )
        
        cursor = conn.cursor()
        cursor.execute("SELECT VERSION()")
        version = cursor.fetchone()
        
        print("✅ MySQL connection successful!")
        print(f"Server version: {version[0]}")
        
        # Try to get table information
        cursor.execute("SHOW TABLES")
        tables = cursor.fetchall()
        
        print("Sample tables:")
        for table in tables:
            print(f"  • {table[0]}")
            
        cursor.close()
        conn.close()
        return True
    except Exception as e:
        print(f"❌ MySQL connection failed: {e}")
        return False

def main():
    """Run all tests and provide recommendations."""
    print("\n" + "="*60)
    print("DATABASE CONNECTION TEST USING IP ADDRESS")
    print("="*60)
    
    print(f"\nTarget Database:")
    print(f"  IP Address: {HOST}")
    print(f"  User:       {USER}")
    print(f"  Database:   {DATABASE}")
    
    # Check if host is reachable on database ports
    pg_reachable, mysql_reachable = check_host_reachable()
    
    # Try connections based on what's reachable
    pg_success = False
    mysql_success = False
    
    if pg_reachable:
        pg_success = try_postgres_connection()
    
    if mysql_reachable:
        mysql_success = try_mysql_connection()
    
    # Connection string recommendations
    print("\nRecommended DATABASE_URL values:")
    
    if pg_success:
        pg_url = f"postgresql://{USER}:{PASSWORD}@{HOST}:{POSTGRES_PORT}/{DATABASE}"
        print(f"PostgreSQL: {pg_url.replace(PASSWORD, '****')}")
    
    if mysql_success:
        mysql_url = f"mysql+pymysql://{USER}:{PASSWORD}@{HOST}:{MYSQL_PORT}/{DATABASE}"
        print(f"MySQL:      {mysql_url.replace(PASSWORD, '****')}")
    
    # Summary
    print("\n" + "="*60)
    print("SUMMARY")
    print("="*60)
    
    if pg_success:
        print("\n✅ Successfully connected to PostgreSQL database")
        print("Use this format in your application:")
        print(f"DATABASE_URL=postgresql://{USER}:{PASSWORD}@{HOST}:{POSTGRES_PORT}/{DATABASE}")
    elif mysql_success:
        print("\n✅ Successfully connected to MySQL database")
        print("This is a MySQL database, not PostgreSQL.")
        print("Use this format in your application:")
        print(f"DATABASE_URL=mysql+pymysql://{USER}:{PASSWORD}@{HOST}:{MYSQL_PORT}/{DATABASE}")
    else:
        print("\n❌ Failed to connect to both PostgreSQL and MySQL databases")
        if pg_reachable or mysql_reachable:
            print("The database server is reachable but authentication failed.")
            print("Check your username, password, and database name.")
        else:
            print("The database server is not reachable on standard ports.")
            print("This could be due to firewall restrictions or the server being down.")
    
    print("\n" + "="*60)

if __name__ == "__main__":
    main()