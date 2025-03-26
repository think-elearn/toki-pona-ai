"""
Test settings for Toki Pona AI project.
"""

import os
import tempfile

# Override environment variables before importing base settings
# IMPORTANT: DO NOT REORDER THESE IMPORTS - they must happen before importing base settings
import environ  # noqa: E402

env = environ.Env()
environ.Env.read_env()

# Set TEST_SECRET_KEY environment variable
os.environ["SECRET_KEY"] = "django-insecure-test-key-not-for-production"

# Now import base settings
from .base import *  # noqa: E402, F403
from .base import ML_MODELS_STORAGE, STORAGES, TEMPLATES  # noqa: E402

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = False

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

# Media files configuration for tests (using temp directory)
MEDIA_URL = "/media/"
MEDIA_ROOT = os.path.join(tempfile.gettempdir(), "test_media")

# Update STORAGES config to use local storage
STORAGES = {
    **STORAGES,  # Import base settings
    "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
}

# ML models configuration for tests (mock implementation)
ML_MODELS_STORAGE["USE_S3"] = False
ML_MODELS_STORAGE["LOCAL_MODELS_DIR"] = os.path.join(
    tempfile.gettempdir(), "test_ml_models"
)

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
# Ensure app_dirs is not set when loaders is defined
TEMPLATES[0]["APP_DIRS"] = False
