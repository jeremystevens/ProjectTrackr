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
4. Set the start command to: `gunicorn --bind 0.0.0.0:$PORT deploy_wsgi:app`
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

### Database Migrations

If you're updating from a previous version of FlaskBin, you'll need to run the migration scripts to add new tables and columns. Run these scripts in the following order (if they haven't been run before):

1. Basic migrations:
   ```bash
   python add_security_columns.py
   python add_account_lockout_columns.py
   python add_user_ban_columns.py
   ```

2. Paste feature migrations:
   ```bash
   python add_burn_after_read_column.py
   python add_paste_encryption_columns.py
   python add_paste_fork_columns.py
   python add_paste_revisions_table.py
   ```

3. Social feature migrations:
   ```bash
   python add_comments_columns.py
   python add_notifications_table.py
   python add_paste_collections_table.py
   python add_tags_table.py
   ```

4. Premium feature migrations:
   ```bash
   python add_subscription_fields.py
   python add_free_ai_trial_column.py
   ```

5. Administration migrations:
   ```bash
   python add_admin_tables.py
   ```

6. Fix scripts (if needed):
   ```bash
   python fix_download_route.py
   python fix_embed_route.py
   python fix_print_view.py
   ```

## Important Notes

- Ensure PostgreSQL is version 12+ for best compatibility
- This release version has all development files removed
- Check the logs after deployment to ensure proper initialization

## Managing Expired Pastes

FlaskBin includes a maintenance script called `prune_expired.py` that should be set up to run periodically. This script removes pastes that have reached their expiration date, keeping your database clean and optimized.

### Setting Up Scheduled Pruning

#### On Linux/Unix Systems (using cron)

1. Edit the crontab:
   ```bash
   crontab -e
   ```

2. Add a line to run the script daily at midnight:
   ```
   0 0 * * * cd /path/to/flaskbin && python prune_expired.py >> prune_expired.log 2>&1
   ```

#### On Windows (using Task Scheduler)

1. Open Task Scheduler
2. Create a Basic Task
3. Set the trigger to daily at midnight
4. Set the action to "Start a program"
5. Browse to your Python executable and add the full path to prune_expired.py as an argument

#### On Heroku

Use the Heroku Scheduler add-on:
1. Install the add-on: `heroku addons:create scheduler:standard`
2. Configure it to run `python prune_expired.py` daily

#### On Render

Use Render's Cron Jobs feature:
1. Create a new Cron Job service
2. Set the schedule to `0 0 * * *` (daily at midnight)
3. Set the command to `python prune_expired.py`

## Setting Up an Administrator Account

FlaskBin includes an admin dashboard for managing users, reported pastes, and system settings. To set up an administrator account:

1. First, ensure that you have a regular user account registered in the system.

2. Run the `set_admin.py` script with your username:

   ```bash
   python set_admin.py --username your_username
   ```

   Or, if you want to specify a user by email:

   ```bash
   python set_admin.py --email your_email@example.com
   ```

3. The script will confirm the user has been granted admin privileges.

4. Log in with the newly promoted admin account.

5. Access the admin panel via the navigation menu or by visiting `/admin` directly.

The admin dashboard gives you access to:
- Reviewing and moderating flagged/reported content
- Managing user accounts (ban/unban, view activities)
- System statistics and performance metrics
- Configuration settings