"""Serrives module for the Tutor application."""

from apps.tutor.services.claude_service import ClaudeService
from apps.tutor.services.quiz_service import QuizService
from apps.tutor.services.transcript_service import TranscriptService
from apps.tutor.services.translation_service import TranslationService
from apps.tutor.services.youtube_service import YouTubeService

# Initialize services on import
__all__ = [
    "ClaudeService",
    "QuizService",
    "TranscriptService",
    "TranslationService",
    "YouTubeService",
]
