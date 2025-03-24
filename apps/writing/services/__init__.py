"""
Services package for the Writing app.
"""

from apps.writing.services.ml_storage import model_storage
from apps.writing.services.recognition import character_recognition
from apps.writing.services.svg import svg_service
from apps.writing.services.templates import template_service

# Initialize services on import
__all__ = ["model_storage", "character_recognition", "template_service", "svg_service"]
