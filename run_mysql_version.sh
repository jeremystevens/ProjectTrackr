#!/bin/bash
# Script to run the MySQL version of FlaskBin
cd mysql_version
gunicorn --bind 0.0.0.0:5000 --reuse-port --reload wsgi_entry:app