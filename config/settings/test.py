"""
Test settings for Toki Pona AI project.
"""

from .base import *  # noqa
from .base import BASE_DIR, STORAGES, ML_MODELS_STORAGE, TEMPLATES

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = False

# Set a static secret key for tests
SECRET_KEY = "django-insecure-test-key-not-for-production"

# Use in-memory SQLite for tests
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": ":memory:",
    }
}

# Use faster password hasher in tests
PASSWORD_HASHERS = [
    "django.contrib.auth.hashers.MD5PasswordHasher",
]

# Use simple cache for tests
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
    }
}

# Media files configuration for tests (in-memory)
MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "test_media"

# Update STORAGES config to use local storage
STORAGES = {
    **STORAGES,  # Import base settings
    "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
}

# ML models configuration for tests (mock implementation)
ML_MODELS_STORAGE["USE_S3"] = False
ML_MODELS_STORAGE["LOCAL_MODELS_DIR"] = BASE_DIR / "test_ml_models"

# Disable most logging during tests
LOGGING = {
    "version": 1,
    "disable_existing_loggers": True,
    "handlers": {
        "null": {
            "class": "logging.NullHandler",
        },
    },
    "root": {
        "handlers": ["null"],
        "level": "WARNING",
    },
}

# Disable template caching in tests for easier debugging
TEMPLATES[0]["OPTIONS"]["loaders"] = [
    "django.template.loaders.filesystem.Loader",
    "django.template.loaders.app_directories.Loader",
]
