"""
WSGI entry point for Render deployment

This is a dedicated WSGI file for deployment to Render that properly sets up
the application with MySQL support.
"""
import os
import pymysql
import logging

# Setup PyMySQL as the dialect used
import sqlalchemy.dialects.mysql
sqlalchemy.dialects.mysql.dialect = sqlalchemy.dialects.mysql.pymysql.dialect
sqlalchemy.dialects.mysql.base.dialect = sqlalchemy.dialects.mysql.pymysql.dialect

# Patch sqlalchemy dialect's imports to prevent PostgreSQL dependency loading
import types
import sqlalchemy.dialects.postgresql
sqlalchemy.dialects.postgresql.psycopg2 = types.ModuleType('psycopg2_stub')
sqlalchemy.dialects.postgresql.psycopg2.dialect = type('dialect', (), {})
sqlalchemy.dialects.postgresql.psycopg2.dialect.dbapi = pymysql
sqlalchemy.dialects.postgresql.psycopg2.dialect.on_connect = lambda: None
sqlalchemy.dialects.postgresql.psycopg2._psycopg2_extras = types.ModuleType('_psycopg2_extras_stub')

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
logger.info("Starting Render WSGI entry point")

# MySQL connection string
MYSQL_CONNECTION_STRING = "mysql+pymysql://u213077714_flaskbin:hOJ27K?5@185.212.71.204:3306/u213077714_flaskbin"

# Set up environment variables if not already set
if "DATABASE_URL" not in os.environ:
    os.environ["DATABASE_URL"] = MYSQL_CONNECTION_STRING
    logger.info(f"Set DATABASE_URL to {MYSQL_CONNECTION_STRING}")

# Import app after environment setup
from app import create_app

# Create the application instance
app = create_app()

# Log successful initialization
logger.info("WSGI application initialized successfully")

if __name__ == "__main__":
    # This is only used when running with gunicorn directly
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))