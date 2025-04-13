"""
Diagnostic script to check PostgreSQL connectivity.

This script helps identify issues with the psycopg2 driver and PostgreSQL database connection.
Run it to diagnose issues with the database connection on Render:
python diagnose_psycopg2.py
"""

import os
import sys
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

def check_psycopg2():
    """Check if psycopg2 is installed and working properly."""
    try:
        logger.info("Checking for psycopg2 installation...")
        
        try:
            import psycopg2
            logger.info(f"✅ psycopg2 is installed (version: {psycopg2.__version__})")
            
            # Check psycopg2.extras
            try:
                from psycopg2 import extras
                logger.info("✅ psycopg2.extras is available")
            except ImportError:
                logger.error("❌ psycopg2.extras is missing! This will cause issues with SQLAlchemy.")
                return False
                
        except ImportError:
            logger.warning("⚠️ psycopg2 not found, checking for psycopg2-binary...")
            try:
                # Some environments use psycopg2-binary instead
                import psycopg2
                logger.info(f"✅ psycopg2-binary is installed (version: {psycopg2.__version__})")
            except ImportError:
                logger.error("❌ Neither psycopg2 nor psycopg2-binary is installed!")
                logger.error("Please install psycopg2-binary with: pip install psycopg2-binary==2.9.9")
                return False
        
        return True
    except Exception as e:
        logger.error(f"❌ Unexpected error checking psycopg2: {e}")
        return False

def check_database_connection():
    """Check if a PostgreSQL database connection can be established."""
    try:
        db_url = os.environ.get("DATABASE_URL")
        logger.info("Checking database connection...")
        
        if not db_url:
            logger.warning("⚠️ DATABASE_URL environment variable not found")
            # Check for other potential database URLs
            for var_name in ["RENDER_POSTGRES_DATABASE_URL", "DB_URL", "POSTGRES_URL"]:
                if var_name in os.environ:
                    db_url = os.environ.get(var_name)
                    logger.info(f"Using {var_name} instead")
                    break
            
            if not db_url:
                logger.error("❌ No database URL found in environment variables")
                return False
        
        # Log a sanitized version of the URL (hiding credentials)
        if db_url:
            if 'postgresql://' in db_url or 'postgres://' in db_url:
                parts = db_url.split('@')
                if len(parts) > 1:
                    sanitized_url = f"postgresql://****:****@{parts[1]}"
                    logger.info(f"Database URL: {sanitized_url}")
            else:
                logger.info(f"Database URL type: {db_url.split(':')[0]}")
        
        # Standardize URL format 
        if db_url.startswith('postgres://'):
            db_url = db_url.replace('postgres://', 'postgresql://', 1)
        
        # Try to connect
        import psycopg2
        conn = psycopg2.connect(db_url)
        
        # Check connection
        with conn.cursor() as cursor:
            cursor.execute("SELECT version();")
            version = cursor.fetchone()[0]
            logger.info(f"✅ Successfully connected to PostgreSQL: {version}")
        
        # Close connection
        conn.close()
        logger.info("✅ Connection closed successfully")
        
        return True
    except Exception as e:
        logger.error(f"❌ Database connection error: {e}")
        return False

def check_sqlalchemy():
    """Check if SQLAlchemy is installed and can connect to the database."""
    try:
        logger.info("Checking SQLAlchemy installation...")
        
        try:
            import sqlalchemy
            logger.info(f"✅ SQLAlchemy is installed (version: {sqlalchemy.__version__})")
            
            # Check available dialects
            from sqlalchemy.dialects import postgresql
            logger.info("✅ PostgreSQL dialect is available")
            
            # Get database URL
            db_url = os.environ.get("DATABASE_URL")
            if not db_url:
                for var_name in ["RENDER_POSTGRES_DATABASE_URL", "DB_URL", "POSTGRES_URL"]:
                    if var_name in os.environ:
                        db_url = os.environ.get(var_name)
                        break
            
            if not db_url:
                logger.warning("⚠️ No database URL found, skipping SQLAlchemy connection test")
                return False
            
            # Standardize URL format 
            if db_url.startswith('postgres://'):
                db_url = db_url.replace('postgres://', 'postgresql://', 1)
            
            # Try to create engine and connect
            engine = sqlalchemy.create_engine(db_url)
            connection = engine.connect()
            logger.info("✅ Successfully connected to database using SQLAlchemy")
            connection.close()
            engine.dispose()
            logger.info("✅ SQLAlchemy connection closed successfully")
            
            return True
        except ImportError:
            logger.error("❌ SQLAlchemy is not installed!")
            return False
            
    except Exception as e:
        logger.error(f"❌ Error with SQLAlchemy: {e}")
        return False

def main():
    """Run all diagnostic checks."""
    logger.info("=== PostgreSQL Connectivity Diagnostics ===")
    
    # Report Python version
    logger.info(f"Python version: {sys.version}")
    
    # Check psycopg2
    psycopg2_ok = check_psycopg2()
    
    # Check database connection
    if psycopg2_ok:
        db_ok = check_database_connection()
    else:
        logger.warning("⚠️ Skipping database connection check due to psycopg2 issues")
        db_ok = False
    
    # Check SQLAlchemy
    sqlalchemy_ok = check_sqlalchemy()
    
    # Summary
    logger.info("\n=== Diagnostics Summary ===")
    logger.info(f"psycopg2:   {'✅ OK' if psycopg2_ok else '❌ FAILED'}")
    logger.info(f"PostgreSQL: {'✅ OK' if db_ok else '❌ FAILED'}")
    logger.info(f"SQLAlchemy: {'✅ OK' if sqlalchemy_ok else '❌ FAILED'}")
    
    if psycopg2_ok and db_ok and sqlalchemy_ok:
        logger.info("✅ All checks passed! Your PostgreSQL setup is working correctly.")
        return 0
    else:
        logger.error("❌ Some checks failed. Please resolve the issues before deploying.")
        return 1

if __name__ == "__main__":
    sys.exit(main())