# Deploying to Render

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
