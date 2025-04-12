#!/usr/bin/env python3
"""
Test MySQL database connection.

This script tests the MySQL connection and verifies that the database is accessible.
"""
import os
import sys
import logging
import pymysql
from sqlalchemy import create_engine, text
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# MySQL connection string
MYSQL_URI = "mysql+pymysql://u213077714_flaskbin:hOJ27K?5@185.212.71.204:3306/u213077714_flaskbin"

def test_direct_connection():
    """Test the MySQL connection directly with pymysql."""
    logger.info("Testing direct pymysql connection...")
    
    connection_params = {
        'host': '185.212.71.204',
        'port': 3306,
        'user': 'u213077714_flaskbin',
        'password': 'hOJ27K?5',
        'database': 'u213077714_flaskbin'
    }
    
    try:
        conn = pymysql.connect(**connection_params)
        cursor = conn.cursor()
        
        # Test a simple query
        cursor.execute("SELECT VERSION()")
        version = cursor.fetchone()
        logger.info(f"MySQL version: {version[0]}")
        
        # Test listing tables
        cursor.execute("SHOW TABLES")
        tables = cursor.fetchall()
        logger.info("Tables in database:")
        for table in tables:
            logger.info(f"  - {table[0]}")
        
        cursor.close()
        conn.close()
        logger.info("✅ Direct connection test successful")
        return True
    except Exception as e:
        logger.error(f"❌ Direct connection test failed: {e}")
        return False

def test_sqlalchemy_connection():
    """Test the MySQL connection using SQLAlchemy."""
    logger.info("Testing SQLAlchemy connection...")
    
    try:
        # Create engine
        engine = create_engine(MYSQL_URI)
        
        # Test connection
        with engine.connect() as conn:
            # Test a simple query
            result = conn.execute(text("SELECT VERSION()"))
            version = result.fetchone()[0]
            logger.info(f"MySQL version: {version}")
            
            # Test listing tables
            result = conn.execute(text("SHOW TABLES"))
            tables = result.fetchall()
            logger.info("Tables in database:")
            for table in tables:
                logger.info(f"  - {table[0]}")
        
        logger.info("✅ SQLAlchemy connection test successful")
        return True
    except Exception as e:
        logger.error(f"❌ SQLAlchemy connection test failed: {e}")
        return False

def test_database_structure():
    """Test the database structure."""
    logger.info("Testing database structure...")
    
    try:
        # Create engine
        engine = create_engine(MYSQL_URI)
        
        # Test connection
        with engine.connect() as conn:
            # Test users table
            result = conn.execute(text("DESCRIBE users"))
            columns = result.fetchall()
            logger.info("users table structure:")
            for column in columns:
                logger.info(f"  - {column[0]}: {column[1]}")
            
            # Test pastes table
            result = conn.execute(text("DESCRIBE pastes"))
            columns = result.fetchall()
            logger.info("pastes table structure:")
            for column in columns:
                logger.info(f"  - {column[0]}: {column[1]}")
        
        logger.info("✅ Database structure test successful")
        return True
    except Exception as e:
        logger.error(f"❌ Database structure test failed: {e}")
        return False

def main():
    """Run all tests."""
    logger.info("=" * 50)
    logger.info("Testing MySQL database connection")
    logger.info("=" * 50)
    
    # Run direct connection test
    direct_test = test_direct_connection()
    logger.info("-" * 50)
    
    # Run SQLAlchemy connection test
    sqlalchemy_test = test_sqlalchemy_connection()
    logger.info("-" * 50)
    
    # Run database structure test
    structure_test = test_database_structure()
    logger.info("-" * 50)
    
    # Print summary
    logger.info("Test Summary:")
    logger.info(f"Direct connection: {'✅ PASSED' if direct_test else '❌ FAILED'}")
    logger.info(f"SQLAlchemy connection: {'✅ PASSED' if sqlalchemy_test else '❌ FAILED'}")
    logger.info(f"Database structure: {'✅ PASSED' if structure_test else '❌ FAILED'}")
    logger.info("=" * 50)
    
    # Return overall result
    if direct_test and sqlalchemy_test and structure_test:
        logger.info("All tests passed! The MySQL connection is working correctly.")
        return 0
    else:
        logger.info("Some tests failed. Please check the logs for details.")
        return 1

if __name__ == "__main__":
    sys.exit(main())