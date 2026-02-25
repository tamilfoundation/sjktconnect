"""WSGI config for SJK(T) Connect."""

import os

from django.core.wsgi import get_wsgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "sjktconnect.settings.production")

application = get_wsgi_application()
