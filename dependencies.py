"""
List of dependencies required for the application.
You can install them using: pip install -r requirements.txt

Create a requirements.txt file with these contents:

bleach==6.0.0
email-validator==2.0.0
Flask==2.3.3
Flask-Login==0.6.2
Flask-SQLAlchemy==3.0.5
Flask-WTF==1.1.1
gunicorn==23.0.0
psycopg2-binary==2.9.9
Pygments==2.16.1
python-dotenv==1.0.0
SQLAlchemy==2.0.19
Werkzeug==2.3.7
WTForms==3.0.1
"""

# You can also run this file to print out the dependencies
if __name__ == "__main__":
    print("Required dependencies:")
    dependencies = [
        "bleach==6.0.0",
        "email-validator==2.0.0",
        "Flask==2.3.3",
        "Flask-Login==0.6.2",
        "Flask-SQLAlchemy==3.0.5",
        "Flask-WTF==1.1.1",
        "gunicorn==23.0.0",
        "psycopg2-binary==2.9.9",
        "Pygments==2.16.1",
        "python-dotenv==1.0.0",
        "SQLAlchemy==2.0.19",
        "Werkzeug==2.3.7",
        "WTForms==3.0.1"
    ]
    for dep in dependencies:
        print(dep)