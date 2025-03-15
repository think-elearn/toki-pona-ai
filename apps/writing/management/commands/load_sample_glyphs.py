from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand
from django.conf import settings
from pathlib import Path

from apps.writing.models import Glyph


class Command(BaseCommand):
    help = "Load sample Sitelen Pona glyphs for testing"

    def handle(self, *args, **kwargs):
        self.stdout.write(self.style.NOTICE("Loading sample Sitelen Pona glyphs..."))

        # Check if we have a media directory
        media_dir = Path(settings.MEDIA_ROOT)
        if not media_dir.exists():
            media_dir.mkdir(parents=True)

        # Create the glyphs subdirectory if it doesn't exist
        glyphs_dir = media_dir / "glyphs"
        if not glyphs_dir.exists():
            glyphs_dir.mkdir(parents=True)

        # Define some basic glyphs
        basic_glyphs = [
            {
                "name": "toki",
                "meaning": "language, communicate, talk, speech",
                "difficulty": "beginner",
                "category": "basic",
                "example_sentence": "toki pona li pona",
                "description": ("The glyph for 'toki' resembles a mouth talking."),
            },
            {
                "name": "pona",
                "meaning": "good, simple, positive",
                "difficulty": "beginner",
                "category": "basic",
                "example_sentence": "sina pona",
                "description": (
                    "The glyph for 'pona' has a simple design representing goodness."
                ),
            },
            {
                "name": "mi",
                "meaning": "I, me, we, us",
                "difficulty": "beginner",
                "category": "basic",
                "example_sentence": "mi moku",
                "description": ("The glyph for 'mi' points to oneself."),
            },
            {
                "name": "sina",
                "meaning": "you",
                "difficulty": "beginner",
                "category": "basic",
                "example_sentence": "sina suli",
                "description": ("The glyph for 'sina' points outward to someone else."),
            },
            {
                "name": "jan",
                "meaning": "person, human, somebody",
                "difficulty": "beginner",
                "category": "basic",
                "example_sentence": "jan li pona",
                "description": (
                    "The glyph for 'jan' resembles a simple figure of a person."
                ),
            },
            {
                "name": "moku",
                "meaning": "food, eat, drink",
                "difficulty": "beginner",
                "category": "basic",
                "example_sentence": "mi moku",
                "description": (
                    "The glyph for 'moku' resembles a bowl or plate with food."
                ),
            },
            {
                "name": "li",
                "meaning": "verb marker",
                "difficulty": "intermediate",
                "category": "grammar",
                "example_sentence": "jan li moku",
                "description": "The glyph for 'li' connects a subject to a verb.",
            },
            {
                "name": "lape",
                "meaning": "sleep, rest",
                "difficulty": "intermediate",
                "category": "basic",
                "example_sentence": "mi lape",
                "description": (
                    "The glyph for 'lape' shows a resting or sleeping state."
                ),
            },
            {
                "name": "olin",
                "meaning": "love, affection, compassion",
                "difficulty": "intermediate",
                "category": "basic",
                "example_sentence": "mi olin e sina",
                "description": (
                    "The glyph for 'olin' represents emotional connection."
                ),
            },
            {
                "name": "tenpo",
                "meaning": "time, duration, period",
                "difficulty": "advanced",
                "category": "basic",
                "example_sentence": "tenpo ni la mi lape",
                "description": (
                    "The glyph for 'tenpo' represents the passing of time."
                ),
            },
        ]

        # Create each glyph
        for glyph_data in basic_glyphs:
            name = glyph_data["name"]
            # Check if glyph already exists
            if Glyph.objects.filter(name=name).exists():
                self.stdout.write(
                    self.style.WARNING(f"Glyph '{name}' already exists, skipping...")
                )
                continue

            # Create the glyph
            glyph = Glyph(
                name=name,
                meaning=glyph_data["meaning"],
                difficulty=glyph_data["difficulty"],
                category=glyph_data["category"],
                example_sentence=glyph_data["example_sentence"],
                description=glyph_data["description"],
            )

            # Save first to create the model instance
            glyph.save()

            # Create a simple SVG placeholder
            svg_content = f"""<svg xmlns="http://www.w3.org/2000/svg"
                width="100" height="100" viewBox="0 0 100 100">
                <rect width="98" height="98" x="1" y="1"
                fill="white" stroke="black" stroke-width="2"/>
                <text x="50" y="50" font-family="Arial" font-size="20"
                text-anchor="middle" dominant-baseline="middle">{name}</text>
            </svg>"""

            try:
                # Use ContentFile instead of File
                content_file = ContentFile(svg_content.encode("utf-8"))

                # Save the content to the model instance
                glyph.image.save(f"{name}.svg", content_file, save=True)

                self.stdout.write(self.style.SUCCESS(f"Created glyph: {glyph.name}"))
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f"Failed to create SVG for {name}: {str(e)}")
                )
                # Keep the glyph record even if we failed to create the image

        self.stdout.write(self.style.SUCCESS("Successfully loaded sample glyphs!"))
