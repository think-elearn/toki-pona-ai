"""
Settings package for Toki Pona AI project.
"""

import os

# Determine which settings to use based on environment variable
environment = os.environ.get("DJANGO_SETTINGS_MODULE", "config.settings.development")

# If just the environment name is provided, convert to full module name
if environment in ("development", "production", "test"):
    os.environ["DJANGO_SETTINGS_MODULE"] = f"config.settings.{environment}"
