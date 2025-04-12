"""
This file exists only as a redirector to deploy_wsgi.py.
It's a failsafe in case the deployment environment is hardcoded to use wsgi.py.
"""

# Simply import app from deploy_wsgi
from deploy_wsgi import app

# Nothing else to do, this will use the app instance from deploy_wsgi.py