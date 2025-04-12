"""
Main application entry point for FlaskBin

This file serves as the entry point for the application when running locally.
It imports the Flask application instance from app.py and runs it.
"""
import os
import pymysql
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

from app import create_app

app = create_app()

if __name__ == "__main__":
    # Run the app with debug=True for local development
    app.run(host="0.0.0.0", port=5000, debug=True)