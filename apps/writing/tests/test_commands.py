from io import StringIO
from django.core.management import call_command
from django.test import TestCase
from apps.writing.models import Glyph


class CommandsTestCase(TestCase):
    def test_load_sample_glyphs(self):
        """Test that the load_sample_glyphs command creates glyph records"""
        # Capture output
        out = StringIO()

        # Call the command
        call_command("load_sample_glyphs", stdout=out)

        # Check command output
        output = out.getvalue()
        self.assertIn("Loading sample Sitelen Pona glyphs", output)
        self.assertIn("Successfully loaded sample glyphs", output)

        # Check that glyphs were created
        self.assertTrue(Glyph.objects.exists())

        # Check for specific glyphs
        expected_glyphs = ["toki", "pona", "mi", "sina", "jan"]
        for name in expected_glyphs:
            self.assertTrue(
                Glyph.objects.filter(name=name).exists(),
                f"Glyph '{name}' was not created",
            )

        # Check glyph counts by difficulty
        beginner_count = Glyph.objects.filter(
            difficulty=Glyph.DifficultyLevel.BEGINNER
        ).count()
        intermediate_count = Glyph.objects.filter(
            difficulty=Glyph.DifficultyLevel.INTERMEDIATE
        ).count()
        advanced_count = Glyph.objects.filter(
            difficulty=Glyph.DifficultyLevel.ADVANCED
        ).count()

        self.assertGreaterEqual(beginner_count, 5)
        self.assertGreaterEqual(intermediate_count, 3)
        self.assertGreaterEqual(advanced_count, 1)

        # Try running the command again (should skip existing glyphs)
        out = StringIO()
        call_command("load_sample_glyphs", stdout=out)
        output = out.getvalue()
        self.assertIn("already exists, skipping", output)
