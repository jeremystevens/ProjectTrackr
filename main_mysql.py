"""
Main entry point file to run the MySQL version from the root directory.
"""
from mysql_version.simple_app import app

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)