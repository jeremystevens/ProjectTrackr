# FlaskBin Deployment Guide

This is the production-ready version of FlaskBin, a modern pastebin application designed for developers and code sharers.

## Environment Variables

Ensure the following environment variables are properly configured in your deployment environment:

- `DATABASE_URL`: PostgreSQL connection URL
- `SESSION_SECRET`: A secure random string for Flask session encryption
- `SENTRY_DSN`: (Optional) Sentry error tracking DSN
- `SENDGRID_API_KEY`: (Optional) For email notifications
- `TWILIO_ACCOUNT_SID`: (Optional) For SMS notifications
- `TWILIO_AUTH_TOKEN`: (Optional) For SMS notifications
- `TWILIO_PHONE_NUMBER`: (Optional) For SMS notifications
- `OPENAI_API_KEY`: (Optional) For AI features

## Deployment Steps

### Render

1. Create a new Web Service
2. Connect to your GitHub repository containing this release code
3. Set the build command to: `pip install -r requirements.txt`
4. Set the start command to: `gunicorn --bind 0.0.0.0:$PORT main:app`
5. Add the required environment variables
6. Deploy

### Heroku

1. Create a new Heroku app
2. Connect to your GitHub repository
3. Add the Heroku Postgres add-on
4. Configure the environment variables in the app settings
5. Deploy the main branch

### Manual Deployment

1. Set up a Python 3.11+ environment
2. Install dependencies: `pip install -r requirements.txt`
3. Configure environment variables
4. Run using Gunicorn: `gunicorn --bind 0.0.0.0:$PORT main:app`

## Database Initialization

The application will automatically create all necessary database tables on first run through SQLAlchemy's `db.create_all()` called in `app.py`.

## Important Notes

- Ensure PostgreSQL is version 12+ for best compatibility
- This release version has all development files removed
- Check the logs after deployment to ensure proper initialization
- It is recommended to set up a scheduled task for the `prune_expired.py` script to clean expired pastes