web: python manage.py migrate --noinput && gunicorn dashboard_platform.wsgi --bind 0.0.0.0:$PORT
release: python manage.py migrate --noinput --run-syncdb --verbosity 2
