from pathlib import Path

from django.conf import settings as django_settings
from django.test import SimpleTestCase, override_settings


class StartupConfigTests(SimpleTestCase):
    def test_deploy_commands_run_migrations_before_start(self):
        project_root = Path(__file__).resolve().parent.parent

        procfile = (project_root / 'Procfile').read_text()
        self.assertIn('python manage.py migrate', procfile)
        self.assertIn('gunicorn', procfile)

        render_config = (project_root / 'render.yaml').read_text()
        self.assertIn('python manage.py migrate', render_config)
        self.assertIn('gunicorn', render_config)

        railway_config = (project_root / 'railway.json').read_text()
        self.assertIn('python manage.py migrate', railway_config)
        self.assertIn('gunicorn', railway_config)

    def test_healthcheck_route_exists(self):
        response = self.client.get('/health/')
        self.assertEqual(response.status_code, 200)
        self.assertIn('ok', response.json()['status'].lower())

    @override_settings(
        DEBUG=False,
        SECURE_SSL_REDIRECT=True,
        SESSION_COOKIE_SECURE=True,
        CSRF_COOKIE_SECURE=True,
        SECURE_BROWSER_XSS_FILTER=True,
    )
    def test_production_security_defaults_are_enabled(self):
        self.assertTrue(django_settings.SECURE_SSL_REDIRECT)
        self.assertTrue(django_settings.SESSION_COOKIE_SECURE)
        self.assertTrue(django_settings.CSRF_COOKIE_SECURE)
        self.assertTrue(django_settings.SECURE_BROWSER_XSS_FILTER)
