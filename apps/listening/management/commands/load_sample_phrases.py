import os
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand

from apps.listening.models import TokiPonaPhrase


class Command(BaseCommand):
    help = "Loads sample Toki Pona phrases for testing"

    def handle(self, *args, **kwargs):
        self.stdout.write(self.style.NOTICE("Loading sample Toki Pona phrases..."))

        # Create media directories if they don't exist
        audio_dir = os.path.join(settings.MEDIA_ROOT, "audio")
        os.makedirs(audio_dir, exist_ok=True)

        # Clear existing phrases if needed
        # TokiPonaPhrase.objects.all().delete()

        # Sample phrases
        sample_phrases = [
            {
                "title": "Basic Greetings",
                "text": "toki!",
                "translations": ["Hello!", "Hi!", "Greetings!"],
                "difficulty": TokiPonaPhrase.DifficultyLevel.BEGINNER,
                "transcript": "WEBVTT\n\n00:00:00.000 --> 00:00:02.000\ntoki!",
                "youtube_video_id": None,
            },
            {
                "title": "Simple Statement",
                "text": "mi pona.",
                "translations": ["I am good.", "I am fine.", "I am well."],
                "difficulty": TokiPonaPhrase.DifficultyLevel.BEGINNER,
                "transcript": "WEBVTT\n\n00:00:00.000 --> 00:00:02.000\nmi pona.",
                "youtube_video_id": None,
            },
            {
                "title": "Basic Question",
                "text": "sina pona ala pona?",
                "translations": ["Are you good?", "Are you well?", "How are you?"],
                "difficulty": TokiPonaPhrase.DifficultyLevel.BEGINNER,
                "transcript": (
                    "WEBVTT\n\n00:00:00.000 --> 00:00:03.000\nsina pona ala pona?"
                ),
                "youtube_video_id": None,
            },
            {
                "title": "Lesson on Numbers",
                "text": "olin li pona",
                "translations": [
                    "Love is good",
                    "Love is nice",
                    "Affection is positive",
                ],
                "difficulty": TokiPonaPhrase.DifficultyLevel.INTERMEDIATE,
                "youtube_video_id": "2EZihKCB9iw",
            },
            {
                "title": "Complex Sentence",
                "text": "jan pona mi li tawa ma ante.",
                "translations": [
                    "My friend goes to another country.",
                    "My friend is going to a different land.",
                ],
                "difficulty": TokiPonaPhrase.DifficultyLevel.ADVANCED,
                "transcript": (
                    "WEBVTT\n\n00:00:00.000 --> 00:00:05.000\n"
                    "jan pona mi li tawa ma ante."
                ),
                "youtube_video_id": None,
            },
        ]

        # Process sample VTT file from the project files
        vtt_source_path = Path("listening-app/utils/captions_lesson_01.vtt")
        if vtt_source_path.exists():
            with open(vtt_source_path, "r", encoding="utf-8") as f:
                full_lesson_transcript = f.read()

            # Add a full lesson example
            sample_phrases.append(
                {
                    "title": "First Lesson: What is Toki Pona?",
                    "text": (
                        "toki! mi jan Misali. kulupu ni pi sitelen tawa la "
                        "sina ken kama sona e toki pona."
                    ),
                    "translations": [
                        (
                            "Hello! I am Misali. In this video series, "
                            "you can learn Toki Pona."
                        ),
                        (
                            "Hi! I'm Misali. With this video group, "
                            "you can learn Toki Pona."
                        ),
                    ],
                    "difficulty": TokiPonaPhrase.DifficultyLevel.BEGINNER,
                    "transcript": full_lesson_transcript,
                    "youtube_video_id": "2EZihKCB9iw",
                }
            )

        # Create the phrases
        for phrase_data in sample_phrases:
            # Extract the data we need
            title = phrase_data.pop("title")
            text = phrase_data.pop("text")
            translations = phrase_data.pop("translations")

            # Create or update the phrase
            phrase, created = TokiPonaPhrase.objects.update_or_create(
                title=title,
                defaults={"text": text, "translations": translations, **phrase_data},
            )

            # Report status
            if created:
                self.stdout.write(self.style.SUCCESS(f"Created phrase: {phrase.title}"))
            else:
                self.stdout.write(self.style.WARNING(f"Updated phrase: {phrase.title}"))

        self.stdout.write(self.style.SUCCESS("Successfully loaded sample phrases!"))
