"""
Advanced database connection test script.
Tests connection with different ports and parameters.
"""
import psycopg2
import socket
import time

# Database connection parameters
HOST = 'srv734.hstgr.io'
USER = 'u213077714_flaskbin'
PASSWORD = 'hOJ27K?5'
DATABASE = 'u213077714_flaskbin'
PORTS_TO_TRY = [5432, 3306, 5433, 25060]  # Standard PostgreSQL, MySQL, alternate PostgreSQL, and DigitalOcean default

def check_host_reachable():
    """Test if the host is reachable via basic socket connection."""
    print("\nTesting if host is reachable...")
    
    for port in PORTS_TO_TRY:
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(2)  # Short timeout for quick check
            result = sock.connect_ex((HOST, port))
            sock.close()
            
            if result == 0:
                print(f"✅ Host {HOST} is reachable on port {port}")
                return True, port
            else:
                print(f"❌ Host {HOST} is not reachable on port {port}")
        except Exception as e:
            print(f"❌ Error checking port {port}: {e}")
    
    return False, None

def try_connection_string():
    """Try connecting using a connection string format."""
    print("\nTrying connection string format...")
    try:
        # Connection string format
        conn_string = f"postgresql://{USER}:{PASSWORD}@{HOST}/{DATABASE}"
        print(f"Testing connection string: {conn_string.replace(PASSWORD, '****')}")
        
        conn = psycopg2.connect(conn_string, connect_timeout=5)
        conn.close()
        print("✅ Connection successful using connection string!")
        return True
    except Exception as e:
        print(f"❌ Connection failed: {e}")
        return False

def try_mysql_connection():
    """Try connecting as if it's a MySQL database."""
    print("\nTrying MySQL-style connection...")
    try:
        import pymysql
        conn = pymysql.connect(
            host=HOST,
            user=USER, 
            password=PASSWORD,
            database=DATABASE,
            connect_timeout=5
        )
        conn.close()
        print("✅ MySQL connection successful!")
        return True
    except ImportError:
        print("❌ pymysql module not installed, skipping MySQL test")
        return False
    except Exception as e:
        print(f"❌ MySQL connection failed: {e}")
        return False

def get_connection_url():
    """Construct what would be a valid DATABASE_URL environment variable."""
    # Standard PostgreSQL format
    pg_url = f"postgresql://{USER}:{PASSWORD}@{HOST}:5432/{DATABASE}"
    
    # MySQL format (just in case)
    mysql_url = f"mysql+pymysql://{USER}:{PASSWORD}@{HOST}:3306/{DATABASE}"
    
    print("\nPossible DATABASE_URL values:")
    print(f"PostgreSQL: {pg_url.replace(PASSWORD, '****')}")
    print(f"MySQL:      {mysql_url.replace(PASSWORD, '****')}")
    
    return pg_url

def main():
    """Run all tests and provide recommendations."""
    print("\n" + "="*60)
    print("ADVANCED DATABASE CONNECTION TEST")
    print("="*60)
    
    print(f"\nTarget Database:")
    print(f"  Host:     {HOST}")
    print(f"  User:     {USER}")
    print(f"  Database: {DATABASE}")
    
    # First check if host is reachable
    is_reachable, open_port = check_host_reachable()
    
    if is_reachable:
        print(f"\n✅ Found open port: {open_port}")
    else:
        print("\n❌ Could not reach host on any standard database port")
        print("This suggests the database server:")
        print("  1. Doesn't accept external connections")
        print("  2. Has a firewall blocking access from Replit")
        print("  3. Requires allowlisting the Replit IP address")
    
    # Try various connection methods
    pg_success = try_connection_string()
    mysql_success = try_mysql_connection()
    
    # Generate possible DATABASE_URL formats
    connection_url = get_connection_url()
    
    # Final recommendations
    print("\n" + "="*60)
    print("RECOMMENDATIONS")
    print("="*60)
    
    if not is_reachable:
        print("\n1. Contact your hosting provider to confirm:")
        print("   - Database is configured to accept external connections")
        print("   - You need to whitelist Replit's IP addresses")
        print("\n2. Check for any special connection requirements:")
        print("   - Non-standard ports")
        print("   - SSL requirements")
        print("   - VPN/SSH tunnel requirements")
    
    print("\n3. Check if the correct DATABASE_URL format is:")
    print(f"   {connection_url.replace(PASSWORD, '****')}")
    
    if not is_reachable and not pg_success and not mysql_success:
        print("\n❌ CONNECTION TESTS FAILED")
        print("The most likely issue is that this database server doesn't allow connections from external IP addresses.")
    
    print("\n" + "="*60)

if __name__ == "__main__":
    main()