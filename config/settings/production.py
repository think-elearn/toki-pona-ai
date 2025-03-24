"""
Production settings for Toki Pona AI project.
"""

from .base import *  # noqa: F403
from .base import ML_MODELS_STORAGE, STORAGES, env

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = env("SECRET_KEY")

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = False

ALLOWED_HOSTS = env.list("ALLOWED_HOSTS")

# Security settings
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SECURE_SSL_REDIRECT = env.bool("SECURE_SSL_REDIRECT", default=True)
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_HSTS_SECONDS = 60 * 60 * 24 * 30  # 30 days
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True

# fly.io tigris S3 storage for media files in production
AWS_ACCESS_KEY_ID = env("AWS_ACCESS_KEY_ID")
AWS_SECRET_ACCESS_KEY = env("AWS_SECRET_ACCESS_KEY")
AWS_STORAGE_BUCKET_NAME = env("BUCKET_NAME")
AWS_S3_REGION_NAME = env("AWS_REGION")  # auto
AWS_S3_ENDPOINT_URL = env("AWS_ENDPOINT_URL_S3")  # https://fly.storage.tigris.dev

# Additional S3 settings
AWS_S3_OBJECT_PARAMETERS = {"CacheControl": "max-age=86400"}
AWS_DEFAULT_ACL = "public-read"

# Media files configuration
MEDIA_URL = f"{AWS_S3_ENDPOINT_URL}/media/"

# Update STORAGES config to use S3
STORAGES = {
    **STORAGES,  # Import base settings
    "default": {"BACKEND": "storages.backends.s3boto3.S3Boto3Storage"},
}

# ML models configuration for production (S3 storage)
ML_MODELS_STORAGE["USE_S3"] = True
ML_MODELS_STORAGE["S3_MODELS_BUCKET_NAME"] = AWS_STORAGE_BUCKET_NAME
ML_MODELS_STORAGE["S3_MODELS_KEY_PREFIX"] = "ml_models/"

# Configure loggers for production
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "verbose": {
            "format": "{levelname} {asctime} {module} {process:d} {thread:d} {message}",
            "style": "{",
        },
    },
    "handlers": {
        "console": {
            "level": "INFO",
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
            "level": "INFO",
            "propagate": False,
        },
    },
}

# Cache configuration
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.redis.RedisCache",
        "LOCATION": env("REDIS_URL"),
    }
}
