import os

from catalog.otel import setup_telemetry

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "catalog.settings")
setup_telemetry()

from django.core.wsgi import get_wsgi_application  # noqa: E402

application = get_wsgi_application()
