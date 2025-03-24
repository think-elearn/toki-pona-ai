from django.core.management.base import BaseCommand

from apps.signing.models import SignReference


class Command(BaseCommand):
    help = "Loads sample Toki Pona signs for testing"

    def handle(self, *args, **kwargs):
        self.stdout.write(self.style.NOTICE("Loading sample Toki Pona signs..."))

        # Sample signs
        sample_signs = [
            {
                "name": "toki",
                "meaning": "communication, language, speech, talk",
                "description": (
                    "The sign involves moving your hand near your mouth, "
                    "representing speech."
                ),
                "difficulty": "beginner",
                "example_sentence": "toki pona li pona",
            },
            {
                "name": "pona",
                "meaning": "good, positive, useful, simple",
                "description": (
                    "The sign is made by raising your thumb up, similar "
                    "to a thumbs-up gesture."
                ),
                "difficulty": "beginner",
                "example_sentence": "sina pona",
            },
            {
                "name": "mi",
                "meaning": "I, me, we, us",
                "description": (
                    "The sign involves pointing to yourself with your index finger."
                ),
                "difficulty": "beginner",
                "example_sentence": "mi moku",
            },
            {
                "name": "sina",
                "meaning": "you",
                "description": (
                    "The sign involves pointing outward with your index finger, "
                    "toward the person you're addressing."
                ),
                "difficulty": "beginner",
                "example_sentence": "sina suli",
            },
            {
                "name": "olin",
                "meaning": "love, affection, compassion",
                "description": (
                    "The sign involves crossing arms over the chest, "
                    "similar to hugging oneself."
                ),
                "difficulty": "intermediate",
                "example_sentence": "mi olin e sina",
            },
            {
                "name": "moku",
                "meaning": "eat, drink, consume, food",
                "description": (
                    "The sign involves bringing your hand to your mouth as if eating."
                ),
                "difficulty": "intermediate",
                "example_sentence": "mi moku e telo",
            },
            {
                "name": "tenpo",
                "meaning": "time, duration, moment, occasion",
                "description": (
                    "The sign involves tapping on your wrist where a watch would be."
                ),
                "difficulty": "advanced",
                "example_sentence": "tenpo ni la mi lape",
            },
        ]

        # Create each sign
        for sign_data in sample_signs:
            name = sign_data["name"]
            # Check if sign already exists
            if SignReference.objects.filter(name=name).exists():
                self.stdout.write(
                    self.style.WARNING(f"Sign '{name}' already exists, updating...")
                )
                sign = SignReference.objects.get(name=name)
            else:
                self.stdout.write(self.style.SUCCESS(f"Creating sign: {name}"))
                sign = SignReference(name=name)

            # Update fields
            sign.meaning = sign_data["meaning"]
            sign.description = sign_data["description"]
            sign.difficulty = sign_data["difficulty"]
            sign.example_sentence = sign_data["example_sentence"]
            sign.save()

        self.stdout.write(self.style.SUCCESS("Successfully loaded sample signs!"))
