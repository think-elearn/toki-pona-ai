"""
Development settings for Toki Pona AI project.
"""

import os

from .base import *  # noqa: F403, F405
from .base import (  # Import directly
    BASE_DIR,
    INSTALLED_APPS,
    MIDDLEWARE,
    ML_MODELS_STORAGE,
    env,
)

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = env(
    "SECRET_KEY", default="django-insecure-development-key-replace-in-production"
)

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

# Extra debugging tools for development
INSTALLED_APPS += [
    "debug_toolbar",
    "django_extensions",
]

# Debug toolbar settings
MIDDLEWARE = [
    "debug_toolbar.middleware.DebugToolbarMiddleware",
] + MIDDLEWARE

DEBUG_TOOLBAR_CONFIG = {
    "DISABLE_PANELS": ["debug_toolbar.panels.redirects.RedirectsPanel"],
    "SHOW_TEMPLATE_CONTEXT": True,
}

INTERNAL_IPS = [
    "127.0.0.1",
]

# Use simple cache for development
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
    }
}

# Email backend for development
EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"

# Media files configuration
MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

# Video storage settings for development
USE_S3_STORAGE = False

# Update ML models configuration for development (local storage)
ML_MODELS_STORAGE.update(
    {
        "USE_S3": False,
        "LOCAL_MODELS_DIR": os.path.join(MEDIA_ROOT, "ml_models"),
        "S3_MODELS_BUCKET_NAME": env("BUCKET_NAME", default=""),
        "S3_MODELS_KEY_PREFIX": "ml_models/",
        "MOBILENET_MODEL_PATH": "mobilenet_v3_small.tflite",
        "MOBILENET_MODEL_URL": "https://storage.googleapis.com/mediapipe-models/image_embedder/mobilenet_v3_small/float32/1/mobilenet_v3_small.tflite",
        # Static paths for glyphs
        "STATIC_GLYPHS_DIR": os.path.join(BASE_DIR, "static", "images", "glyphs"),
    }
)

# Create required directories if they don't exist
os.makedirs(ML_MODELS_STORAGE["LOCAL_MODELS_DIR"], exist_ok=True)
os.makedirs(os.path.join(MEDIA_ROOT, "glyphs"), exist_ok=True)
os.makedirs(os.path.join(MEDIA_ROOT, "glyphs/reference"), exist_ok=True)
os.makedirs(os.path.join(MEDIA_ROOT, "templates"), exist_ok=True)
os.makedirs(os.path.join(MEDIA_ROOT, "sitelen_pona_svgs"), exist_ok=True)

# Add development specific logging
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "verbose": {
            "format": "{levelname} {asctime} {module} {message}",
            "style": "{",
        },
    },
    "handlers": {
        "console": {
            "level": "DEBUG",
            "class": "logging.StreamHandler",
            "formatter": "verbose",
        }
    },
    "root": {
        "handlers": ["console"],
        "level": "INFO",
    },
    "loggers": {
        "django": {
            "handlers": ["console"],
            "level": env.str("DJANGO_LOG_LEVEL", "INFO"),
            "propagate": False,
        },
        "apps": {
            "handlers": ["console"],
            "level": "DEBUG",
            "propagate": False,
        },
    },
}
