#!/usr/bin/env python3
"""
Runner script that executes the MySQL version of FlaskBin

This script helps you run the MySQL-only version of the application
without any PostgreSQL dialect conflicts.
"""
import os
import subprocess
import sys

def main():
    """Run the MySQL version of FlaskBin"""
    print("Starting MySQL version of FlaskBin...")
    
    # Change to the mysql_version directory
    os.chdir('mysql_version')
    
    # Run with gunicorn for production-like environment
    cmd = [
        "gunicorn",
        "--bind", "0.0.0.0:5000",
        "--reuse-port",
        "--reload",
        "wsgi_entry:app"
    ]
    
    try:
        subprocess.run(cmd)
    except KeyboardInterrupt:
        print("\nShutting down...")
    except Exception as e:
        print(f"Error: {e}")
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())