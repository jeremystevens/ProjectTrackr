#!/usr/bin/env python3
"""
Test MySQL Connection

This script tests the connection to the MySQL database.
"""
import os
import pymysql
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# MySQL connection details
MYSQL_CONFIG = {
    'host': '185.212.71.204',
    'user': 'u213077714_flaskbin',
    'password': 'hOJ27K?5',
    'database': 'u213077714_flaskbin',
    'port': 3306
}

def test_connection():
    """Test connection to the MySQL database."""
    try:
        # Connect to the database
        conn = pymysql.connect(**MYSQL_CONFIG)
        cursor = conn.cursor()
        
        # Execute a simple query
        cursor.execute("SELECT VERSION()")
        version = cursor.fetchone()
        
        logger.info(f"Successfully connected to MySQL database")
        logger.info(f"MySQL version: {version[0]}")
        
        # Get list of tables
        cursor.execute("SHOW TABLES")
        tables = cursor.fetchall()
        
        logger.info(f"Database contains {len(tables)} tables:")
        for table in tables:
            logger.info(f"  - {table[0]}")
            
            # Get column information for each table
            cursor.execute(f"DESCRIBE {table[0]}")
            columns = cursor.fetchall()
            logger.info(f"    Columns: {len(columns)}")
            
            # Count rows in each table
            cursor.execute(f"SELECT COUNT(*) FROM {table[0]}")
            count = cursor.fetchone()[0]
            logger.info(f"    Rows: {count}")
        
        # Close the connection
        cursor.close()
        conn.close()
        
        return True
    except Exception as e:
        logger.error(f"Failed to connect to MySQL database: {e}")
        return False

if __name__ == "__main__":
    logger.info("Testing MySQL connection...")
    success = test_connection()
    
    if success:
        logger.info("MySQL connection test passed!")
    else:
        logger.error("MySQL connection test failed!")