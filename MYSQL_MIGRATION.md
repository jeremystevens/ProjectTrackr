# MySQL Migration Guide

## Overview

This document provides information on how to use the MySQL version of the FlaskBin application. The application has been migrated from PostgreSQL to MySQL to better suit environments where MySQL is the preferred database system.

## Why the Migration?

The original FlaskBin was built with PostgreSQL, but some users may prefer MySQL for various reasons:

- Existing infrastructure using MySQL
- Familiarity with MySQL administration
- Better performance for certain workloads
- Hosting environments that only support MySQL

## How to Run the MySQL Version

### Method 1: Using the Runner Script

The simplest way to run the MySQL version is to use the provided runner script:

```bash
./run_mysql_app.py
```

This script will automatically:
1. Change to the mysql_version directory
2. Start Gunicorn with the correct configuration
3. Serve the application on port 5000

### Method 2: Manual Execution

If you prefer to run the commands manually:

```bash
cd mysql_version
gunicorn --bind 0.0.0.0:5000 --reuse-port --reload wsgi_entry:app
```

### Method 3: Using Python Directly

For development purposes, you can also run the app directly with Python:

```bash
python main_mysql.py
```

## Database Configuration

The MySQL connection is configured with the following parameters in `mysql_version/simple_app.py`:

```python
DB_CONFIG = {
    'host': '185.212.71.204',
    'port': 3306,
    'user': 'u213077714_flaskbin',
    'password': 'hOJ27K?5',
    'database': 'u213077714_flaskbin',
    'charset': 'utf8mb4',
    'cursorclass': pymysql.cursors.DictCursor
}
```

To use your own MySQL database, update these settings accordingly.

## Technical Implementation

The MySQL version is a clean implementation that:

1. Avoids SQLAlchemy dialect conflicts between PostgreSQL and MySQL
2. Uses direct pymysql connections for database operations
3. Implements a Flask-Login-like user authentication system
4. Maintains all the core functionality of the original FlaskBin

## Features

The MySQL version currently supports:

- Creating, viewing, and downloading pastes
- User registration and authentication
- Syntax highlighting for code snippets
- Public/private paste visibility
- Expiring pastes
- Burn-after-read functionality
- Dark/light theme toggle

## Differences from PostgreSQL Version

- Direct database access using pymysql instead of SQLAlchemy ORM
- Simplified schema without some advanced features
- Different query syntax for some operations (MySQL vs PostgreSQL SQL dialect)

## Future Work

The following enhancements are planned:

1. Add all advanced features from the PostgreSQL version
2. Improve error handling and logging
3. Add additional MySQL-specific optimizations
4. Create database migration scripts