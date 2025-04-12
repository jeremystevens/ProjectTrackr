# MySQL Migration Documentation

## Overview

This project has been migrated from PostgreSQL to MySQL. This document outlines the changes made and how to work with the MySQL database.

## Connection Details

The application now uses MySQL with the following connection parameters:

- **Host**: 185.212.71.204
- **Port**: 3306
- **Database**: u213077714_flaskbin
- **User**: u213077714_flaskbin
- **Password**: `hOJ27K?5`

The full connection string is:
```
mysql+pymysql://u213077714_flaskbin:hOJ27K?5@185.212.71.204:3306/u213077714_flaskbin
```

## Environment Variables

The `DATABASE_URL` environment variable should be set to the MySQL connection string in production environments:

```
DATABASE_URL=mysql+pymysql://u213077714_flaskbin:hOJ27K?5@185.212.71.204:3306/u213077714_flaskbin
```

## Database Schema

The database schema has been created in MySQL with all the necessary tables. The schema is the same as the PostgreSQL schema, but using MySQL data types.

## MySQL vs PostgreSQL Differences

Some key differences to be aware of:

1. **Data Types**:
   - PostgreSQL `SERIAL` -> MySQL `AUTO_INCREMENT`
   - PostgreSQL `BYTEA` -> MySQL `BLOB`
   - PostgreSQL `BOOLEAN` -> MySQL `TINYINT(1)`
   - PostgreSQL arrays are not supported in MySQL
   - PostgreSQL `JSONB` -> MySQL `JSON`

2. **SQL Syntax**:
   - MySQL doesn't support `RETURNING` clauses
   - MySQL uses different string functions
   - MySQL has different transaction isolation levels

3. **Performance**:
   - Indexes work differently
   - Query optimization may require different approaches

## Accessing the Database

You can access the MySQL database using phpMyAdmin or any MySQL client like MySQL Workbench.

## Troubleshooting

Common issues when working with MySQL:

1. **Connection Errors**: Make sure the host is accessible and firewall rules allow connections
2. **Authentication Errors**: Verify username and password
3. **Schema Errors**: MySQL is case-sensitive for table names on some platforms

