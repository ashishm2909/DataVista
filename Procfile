web: gunicorn dashboard_platform.wsgi --bind 0.0.0.0:$PORT
release: python manage.py migrate --run-syncdb --verbosity 2
