import os
import sys
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_database_connection():
    """Test database connection using SQLAlchemy."""
    logger.info("Testing database connection...")
    
    # Get database URL from environment
    db_url = os.environ.get("DATABASE_URL")
    if not db_url:
        logger.error("No DATABASE_URL environment variable found!")
        return False
        
    # Fix URL format if needed
    if db_url.startswith('postgres://'):
        db_url = db_url.replace('postgres://', 'postgresql://', 1)
    
    # Log a sanitized version of the URL (hiding credentials)
    if 'postgresql://' in db_url:
        parts = db_url.split('@')
        if len(parts) > 1:
            sanitized_url = f"postgresql://****:****@{parts[1]}"
            logger.info(f"Using database URL: {sanitized_url}")
        else:
            logger.info("Using PostgreSQL database")
    else:
        logger.info(f"Using database URL type: {db_url.split(':')[0]}")
    
    try:
        # Import SQLAlchemy and psycopg2 specifically for PostgreSQL
        import psycopg2
        from sqlalchemy import create_engine, text
        
        # Create engine specifically for PostgreSQL
        engine = create_engine(
            db_url,
            connect_args={"sslmode": "require"},
            pool_pre_ping=True,
            pool_recycle=300
        )
        
        # Test connection
        with engine.connect() as connection:
            result = connection.execute(text("SELECT 1")).fetchone()
            logger.info(f"Database connection successful! Test query result: {result}")
            
            # Try to get database version for more information
            version = connection.execute(text("SELECT version()")).fetchone()
            logger.info(f"Database version: {version[0]}")
            
            return True
    except ImportError as e:
        logger.error(f"Missing required database driver: {e}")
        logger.info("Make sure psycopg2-binary is installed for PostgreSQL connections")
        return False
    except Exception as e:
        logger.error(f"Database connection error: {e}")
        logger.error(f"Error type: {type(e).__name__}")
        return False

if __name__ == "__main__":
    success = test_database_connection()
    sys.exit(0 if success else 1)