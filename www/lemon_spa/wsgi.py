"""WSGI config for lemon_spa project."""

import os
from django.core.wsgi import get_wsgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "lemon_spa.settings")

application = get_wsgi_application()
