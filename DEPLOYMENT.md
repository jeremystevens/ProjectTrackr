# Deployment Guide for FlaskBin

This guide explains how to deploy the FlaskBin application to production environments, focusing on deployment to Render.com.

## SQLAlchemy Mapper Conflicts

One of the main challenges we've faced is SQLAlchemy mapper conflicts during deployment. These conflicts occur because:

1. SQLAlchemy complains about models being registered multiple times when using complex import structures
2. Circular imports between modules create initialization issues
3. The application factory pattern combined with blueprint registration can lead to duplicate model registration

## Solution: Simplified Deployment Structure

We've resolved these issues using a simplified deployment structure with the following components:

1. `deploy_wsgi.py`: A specialized WSGI entry point for production that:
   - Uses a flat structure without the application factory pattern
   - Avoids circular imports by careful import ordering
   - Explicitly provides dependencies to modules that need them
   - Includes explicit URL prefixes for all blueprints

2. Direct PostgreSQL Access:
   - Added `db.py` functions for direct PostgreSQL connections using psycopg2
   - Created `utils/bulk_operations.py` module for efficient bulk data operations
   - Uses PostgreSQL's native COPY command for high-performance data transfers

3. Utility Function Integration:
   - Integrated critical utility functions into proper module structure
   - Made dependencies optional with try/except blocks to improve resilience

## Deploying to Render.com

### Prerequisites

- A Render.com account
- PostgreSQL database (can be provisioned on Render.com)
- Environment variables (see below)

### Environment Variables

Set the following environment variables in Render Dashboard:

- `DATABASE_URL`: PostgreSQL connection string
- `SESSION_SECRET`: Secret key for Flask sessions
- `OPENAI_API_KEY`: (Optional) For AI code summarization features
- `SENTRY_DSN`: (Optional) For error tracking

### Deployment Steps

1. Push your code to a Git repository
2. Connect the repository to Render
3. Select the "Web Service" type
4. Configure with:
   - Build Command: `pip install -r requirements.txt`
   - Start Command: `gunicorn --bind 0.0.0.0:$PORT deploy_wsgi:app`
   - Environment: Python 3.11
   - Add your environment variables

### render.yaml Configuration

```yaml
services:
  - type: web
    name: flaskbin
    env: python
    buildCommand: pip install -r requirements.txt
    startCommand: gunicorn --bind 0.0.0.0:$PORT deploy_wsgi:app
    envVars:
      - key: PYTHON_VERSION
        value: 3.11.0
```

## Troubleshooting

### Common Issues

1. **500 Server Errors**: Check Render logs for specific error messages
2. **URL Build Errors**: Verify blueprint registration in `deploy_wsgi.py`
3. **Database Connection Issues**: Confirm DATABASE_URL is correctly formatted
4. **Import Errors**: Ensure all required packages are in `requirements.txt`

### Debugging

- Use Sentry for error tracking
- Increase log level in `deploy_wsgi.py` with `logging.basicConfig(level=logging.DEBUG)`
- Check the Render logs for detailed error messages

## Performance Optimization

The direct PostgreSQL access introduced in this deployment approach offers significant performance benefits:

- Bypasses SQLAlchemy ORM overhead for bulk operations
- Uses native PostgreSQL COPY commands for efficient data transfer
- Avoids mapper registration issues that can cause slowdowns

## Security Considerations

- Always use environment variables for secrets
- Ensure proper CSRF protection is enabled
- Consider enabling HTTPS-only cookies
- Review database user permissions

## Additional Resources

- [Flask Documentation](https://flask.palletsprojects.com/)
- [SQLAlchemy Documentation](https://docs.sqlalchemy.org/)
- [Render.com Documentation](https://render.com/docs)