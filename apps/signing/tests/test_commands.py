from io import StringIO

from django.core.management import call_command
from django.test import TestCase

from apps.signing.models import SignReference


class CommandsTestCase(TestCase):
    def test_load_sample_signs(self):
        """Test that the load_sample_signs command creates sign records"""
        # Capture output
        out = StringIO()

        # Call the command
        call_command("load_sample_signs", stdout=out)

        # Check command output
        output = out.getvalue()
        self.assertIn("Loading sample Toki Pona signs", output)
        self.assertIn("Successfully loaded sample signs", output)

        # Check that signs were created
        self.assertTrue(SignReference.objects.exists())

        # Check for specific signs
        expected_signs = ["toki", "pona", "mi", "sina", "olin"]
        for name in expected_signs:
            self.assertTrue(
                SignReference.objects.filter(name=name).exists(),
                f"Sign '{name}' was not created",
            )

        # Check sign counts by difficulty
        beginner_count = SignReference.objects.filter(
            difficulty=SignReference.DifficultyLevel.BEGINNER
        ).count()
        intermediate_count = SignReference.objects.filter(
            difficulty=SignReference.DifficultyLevel.INTERMEDIATE
        ).count()
        advanced_count = SignReference.objects.filter(
            difficulty=SignReference.DifficultyLevel.ADVANCED
        ).count()

        self.assertGreaterEqual(beginner_count, 4)
        self.assertGreaterEqual(intermediate_count, 2)
        self.assertGreaterEqual(advanced_count, 1)

        # Try running the command again (should update existing signs)
        out = StringIO()
        call_command("load_sample_signs", stdout=out)
        output = out.getvalue()
        self.assertIn("already exists, updating", output)
