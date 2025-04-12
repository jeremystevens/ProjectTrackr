#!/usr/bin/env python
"""
Update MySQL Config Script

This script updates the necessary application files to use MySQL instead of PostgreSQL.
"""
import os
import sys
import re

# MySQL Database connection string
MYSQL_CONNECTION_STRING = "mysql+pymysql://u213077714_flaskbin:hOJ27K?5@185.212.71.204:3306/u213077714_flaskbin"

def update_file(file_path, patterns):
    """
    Update a file with specified patterns.
    
    Args:
        file_path: Path to the file to update
        patterns: List of (pattern, replacement) tuples
    
    Returns:
        bool: True if successful, False otherwise
    """
    if not os.path.exists(file_path):
        print(f"❌ File not found: {file_path}")
        return False
    
    try:
        with open(file_path, 'r') as file:
            content = file.read()
        
        updated_content = content
        for pattern, replacement in patterns:
            updated_content = re.sub(pattern, replacement, updated_content)
        
        if content == updated_content:
            print(f"⚠️ No changes needed in {file_path}")
            return True
        
        with open(file_path, 'w') as file:
            file.write(updated_content)
        
        print(f"✅ Updated {file_path}")
        return True
    except Exception as e:
        print(f"❌ Error updating {file_path}: {e}")
        return False

def update_app_py():
    """Update app.py to use MySQL."""
    patterns = [
        (r"app\.config\[\"SQLALCHEMY_DATABASE_URI\"\]\s*=\s*os\.environ\.get\(\"DATABASE_URL\"[^)]*\)",
         f'app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL", "{MYSQL_CONNECTION_STRING}")'),
    ]
    return update_file('app.py', patterns)

def update_wsgi_py():
    """Update wsgi.py to use MySQL."""
    patterns = [
        (r"SQLALCHEMY_DATABASE_URI=os\.environ\.get\(\"DATABASE_URL\"[^)]*\)",
         f'SQLALCHEMY_DATABASE_URI=os.environ.get("DATABASE_URL", "{MYSQL_CONNECTION_STRING}")'),
        (r"import os[^\n]*",
         'import os\nimport pymysql')
    ]
    return update_file('wsgi.py', patterns)

def update_render_yaml():
    """Update render.yaml with the MySQL environment variable."""
    if not os.path.exists('render.yaml'):
        print("⚠️ render.yaml not found, skipping")
        return True
    
    patterns = [
        (r"DATABASE_URL:[^\n]*",
         f'DATABASE_URL: "{MYSQL_CONNECTION_STRING}"')
    ]
    return update_file('render.yaml', patterns)

def create_env_file():
    """Create or update .env file with MySQL configuration."""
    env_content = f"""# Environment variables for FlaskBin
DATABASE_URL="{MYSQL_CONNECTION_STRING}"
SESSION_SECRET="your-secure-session-secret-replace-in-production"
"""
    
    try:
        with open('.env', 'w') as f:
            f.write(env_content)
        print("✅ Created .env file with MySQL configuration")
        return True
    except Exception as e:
        print(f"❌ Failed to create .env file: {e}")
        return False

def update_main_py():
    """Update main.py if needed."""
    if not os.path.exists('main.py'):
        print("⚠️ main.py not found, skipping")
        return True
    
    patterns = [
        (r"import os[^\n]*",
         'import os\nimport pymysql')
    ]
    return update_file('main.py', patterns)

def update_requirements():
    """Update requirements.txt to include pymysql."""
    if not os.path.exists('requirements.txt'):
        print("⚠️ requirements.txt not found, creating new one")
        with open('requirements.txt', 'w') as f:
            f.write("pymysql==1.1.0\n")
        print("✅ Created requirements.txt with pymysql")
        return True
    
    try:
        with open('requirements.txt', 'r') as f:
            content = f.read()
        
        if 'pymysql' not in content.lower():
            with open('requirements.txt', 'a') as f:
                f.write("\npymysql==1.1.0\n")
            print("✅ Added pymysql to requirements.txt")
        else:
            print("✅ pymysql already in requirements.txt")
        
        return True
    except Exception as e:
        print(f"❌ Error updating requirements.txt: {e}")
        return False

def create_render_instructions():
    """Create instructions file for Render deployment."""
    instructions = """# Deploying to Render

## Important: MySQL Database Configuration

This application now uses MySQL instead of PostgreSQL. Make sure to set the following environment variables in your Render service:

- `DATABASE_URL`: mysql+pymysql://u213077714_flaskbin:hOJ27K?5@185.212.71.204:3306/u213077714_flaskbin

## Deployment Steps

1. Push your code to your Git repository
2. Connect your repository to Render
3. Set up a Web Service with these settings:

   - Build Command: `pip install -r requirements.txt`
   - Start Command: `gunicorn --bind 0.0.0.0:$PORT wsgi:app`

4. Add the environment variables listed above
5. Deploy the service

The application should now connect to your MySQL database successfully.
"""
    
    try:
        with open('RENDER_DEPLOY.md', 'w') as f:
            f.write(instructions)
        print("✅ Created RENDER_DEPLOY.md with deployment instructions")
        return True
    except Exception as e:
        print(f"❌ Failed to create RENDER_DEPLOY.md: {e}")
        return False

def main():
    """Main function to update MySQL configuration."""
    print("\n" + "="*60)
    print("MYSQL CONFIGURATION UPDATE")
    print("="*60)
    
    # Update main application files
    update_app_py()
    update_wsgi_py()
    update_main_py()
    update_render_yaml()
    
    # Create/update supporting files
    create_env_file()
    update_requirements()
    create_render_instructions()
    
    print("\n" + "="*60)
    print("UPDATE COMPLETE")
    print("="*60)
    print("\nYour application has been updated to use MySQL.")
    print("The MySQL database URL is:")
    print(f"  {MYSQL_CONNECTION_STRING}")
    print("\nTo deploy to Render, follow the instructions in RENDER_DEPLOY.md")

if __name__ == "__main__":
    main()