"""ASGI config for lemon_spa project."""

import os
from django.core.asgi import get_asgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "lemon_spa.settings")

application = get_asgi_application()
