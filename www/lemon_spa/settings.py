"""Settings for lemon_spa project."""

from __future__ import annotations

import os
from pathlib import Path
from urllib.parse import urlparse

from django.core.exceptions import ImproperlyConfigured

BASE_DIR = Path(__file__).resolve().parent.parent


def _load_env_file(path: Path) -> None:
    """Populate ``os.environ`` with values from a simple ``.env`` file."""

    if not path.exists():
        return

    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        key, _, value = line.partition("=")
        if not key:
            continue
        cleaned = value.strip().strip('"').strip("'")
        os.environ.setdefault(key.strip(), cleaned)


ENV_FILE_NAME = os.environ.get("DJANGO_ENV_FILE", ".env")
if ENV_FILE_NAME:
    env_path = Path(ENV_FILE_NAME)
    if not env_path.is_absolute():
        env_path = BASE_DIR / env_path
    _load_env_file(env_path)


def _env(key: str, default: str | None = None) -> str:
    try:
        return os.environ[key]
    except KeyError as exc:
        if default is not None:
            return default
        raise ImproperlyConfigured(f"Missing required environment variable: {key}") from exc


def _env_bool(key: str, default: bool = False) -> bool:
    value = os.environ.get(key)
    if value is None:
        return default
    return value.lower() in {"1", "true", "t", "yes", "on"}


def _env_list(key: str, default: list[str] | None = None) -> list[str]:
    value = os.environ.get(key)
    if value is None:
        return default[:] if default else []
    return [item.strip() for item in value.split(",") if item.strip()]


def _database_settings() -> dict[str, str]:
    database_url = os.environ.get("DATABASE_URL")
    if database_url:
        return _parse_database_url(database_url)

    if os.environ.get("POSTGRES_DB"):
        return {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": os.environ.get("POSTGRES_DB", ""),
            "USER": os.environ.get("POSTGRES_USER", ""),
            "PASSWORD": os.environ.get("POSTGRES_PASSWORD", ""),
            "HOST": os.environ.get("POSTGRES_HOST", ""),
            "PORT": os.environ.get("POSTGRES_PORT", ""),
        }

    return {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": str(BASE_DIR / "db.sqlite3"),
    }


def _parse_database_url(url: str) -> dict[str, str]:
    result = urlparse(url)
    scheme = result.scheme.split("+", 1)[0]
    engine_map = {
        "postgres": "django.db.backends.postgresql",
        "postgresql": "django.db.backends.postgresql",
        "pgsql": "django.db.backends.postgresql",
    }

    engine = engine_map.get(scheme)
    if engine is None:
        raise ImproperlyConfigured(f"Unsupported database scheme: {result.scheme}")

    return {
        "ENGINE": engine,
        "NAME": result.path.lstrip("/"),
        "USER": result.username or "",
        "PASSWORD": result.password or "",
        "HOST": result.hostname or "",
        "PORT": str(result.port or ""),
    }


SECRET_KEY = _env("DJANGO_SECRET_KEY")
DEBUG = _env_bool("DJANGO_DEBUG")
ALLOWED_HOSTS = _env_list("DJANGO_ALLOWED_HOSTS", default=["localhost"])
CSRF_TRUSTED_ORIGINS = _env_list("DJANGO_CSRF_TRUSTED_ORIGINS")

INSTALLED_APPS = [
    "rest_framework",
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "accounts",
    "client_dashboard",
    "therapist_panel",
    "questionnaires",
    "appointments",
    "phone_verification",
    "scheduling",
]

AUTH_USER_MODEL = "accounts.AccountUser"

AUTHENTICATION_BACKENDS = [
    "accounts.backends.PhoneNumberBackend",
    "django.contrib.auth.backends.ModelBackend",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "lemon_spa.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "lemon_spa.wsgi.application"
ASGI_APPLICATION = "lemon_spa.asgi.application"

DATABASES = {
    "default": _database_settings()
}

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",
    },
]

LANGUAGE_CODE = "en-us"
TIME_ZONE = os.environ.get("DJANGO_TIME_ZONE", "UTC")
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"

SECURE_SSL_REDIRECT = _env_bool("DJANGO_SECURE_SSL_REDIRECT")
SESSION_COOKIE_SECURE = _env_bool("DJANGO_SESSION_COOKIE_SECURE", default=SECURE_SSL_REDIRECT)
CSRF_COOKIE_SECURE = _env_bool("DJANGO_CSRF_COOKIE_SECURE", default=SECURE_SSL_REDIRECT)
SECURE_CONTENT_TYPE_NOSNIFF = _env_bool("DJANGO_SECURE_CONTENT_TYPE_NOSNIFF", default=not DEBUG)
SECURE_REFERRER_POLICY = os.environ.get("DJANGO_SECURE_REFERRER_POLICY", "same-origin")

_hsts_seconds = os.environ.get("DJANGO_SECURE_HSTS_SECONDS")
try:
    SECURE_HSTS_SECONDS = int(_hsts_seconds) if _hsts_seconds else 0
except ValueError as exc:
    raise ImproperlyConfigured("DJANGO_SECURE_HSTS_SECONDS must be an integer") from exc

SECURE_HSTS_INCLUDE_SUBDOMAINS = SECURE_HSTS_SECONDS > 0 and _env_bool(
    "DJANGO_SECURE_HSTS_INCLUDE_SUBDOMAINS", default=True
)
SECURE_HSTS_PRELOAD = SECURE_HSTS_SECONDS > 0 and _env_bool(
    "DJANGO_SECURE_HSTS_PRELOAD", default=True
)

PHONE_VERIFICATION = {
    "CODE_LENGTH": 4,
    "CODE_TTL_SECONDS": 5 * 60,
    "RESEND_INTERVAL_SECONDS": 60,
    "MAX_VERIFICATION_ATTEMPTS": 3,
    "MAX_SEND_COUNT": 3,
    "MESSAGE_TEMPLATE": "Your Lemon Spa verification code is {code}. It expires in 5 minutes.",
}
PHONE_VERIFICATION_SMS_BACKEND = os.environ.get(
    "PHONE_VERIFICATION_SMS_BACKEND",
    "phone_verification.sms.dummy.DummySmsProvider",
)
PHONE_VERIFICATION_TWILIO = {
    "ACCOUNT_SID": os.environ.get("TWILIO_ACCOUNT_SID"),
    "AUTH_TOKEN": os.environ.get("TWILIO_AUTH_TOKEN"),
    "FROM_NUMBER": os.environ.get("TWILIO_FROM_NUMBER"),
}

USE_X_FORWARDED_HOST = _env_bool("DJANGO_USE_X_FORWARDED_HOST")
SECURE_PROXY_SSL_HEADER = (
    ("HTTP_X_FORWARDED_PROTO", "https")
    if _env_bool("DJANGO_USE_SECURE_PROXY_HEADER")
    else None
)

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
        }
    },
    "root": {
        "handlers": ["console"],
        "level": os.environ.get("DJANGO_LOG_LEVEL", "INFO"),
    },
}
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

LOGIN_URL = "accounts:login"
LOGIN_REDIRECT_URL = "client_dashboard:index"
LOGOUT_REDIRECT_URL = "accounts:login"
