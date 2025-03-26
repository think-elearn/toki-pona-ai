from io import StringIO
from unittest.mock import patch

import pytest
from django.core.management import call_command
from django.test import TestCase

from apps.writing.models import Glyph


class CommandsTestCase(TestCase):
    @pytest.mark.django_db
    @patch("cairosvg.svg2png")
    def test_load_glyphs(self, mock_svg2png):
        """Test that the load_glyphs command creates glyph records from static SVGs"""
        # Set up test SVGs
        pytest.importorskip("pytest_django")

        # Mock the cairosvg conversion to return a simple PNG byte array
        mock_png_data = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x00\x00\x00\x00:~\x9bU\x00\x00\x00\nIDATx\x9cc`\x00\x00\x00\x02\x00\x01H\xaf\xa4q\x00\x00\x00\x00IEND\xaeB`\x82"
        mock_svg2png.return_value = mock_png_data

        # Capture output
        out = StringIO()

        # Mock the static SVG files detection
        with patch(
            "apps.writing.management.commands.load_glyphs.Path.glob"
        ) as mock_glob:
            # Simulate finding SVG files
            mock_files = [
                type("MockPath", (), {"stem": "toki", "name": "toki.svg"}),
                type("MockPath", (), {"stem": "pona", "name": "pona.svg"}),
                type("MockPath", (), {"stem": "mi", "name": "mi.svg"}),
            ]
            mock_glob.return_value = mock_files

            # Mock the open function to return SVG content
            with patch("builtins.open", create=True) as mock_open:
                mock_open.return_value.__enter__.return_value.read.return_value = (
                    "<svg></svg>"
                )

                # Call the command
                call_command("load_glyphs", stdout=out)

        # Check command output
        output = out.getvalue()
        self.assertIn("Loading Sitelen Pona glyphs from static files", output)

        # Check that at least some glyphs were processed
        self.assertTrue(Glyph.objects.exists())

        # Get the list of created glyphs
        created_glyphs = list(Glyph.objects.values_list("name", flat=True))

        # Try running the command again (should skip existing glyphs)
        out = StringIO()
        with patch(
            "apps.writing.management.commands.load_glyphs.Path.glob"
        ) as mock_glob:
            mock_glob.return_value = mock_files
            with patch("builtins.open", create=True) as mock_open:
                mock_open.return_value.__enter__.return_value.read.return_value = (
                    "<svg></svg>"
                )
                call_command("load_glyphs", stdout=out)

        output = out.getvalue()
        if created_glyphs:
            self.assertIn("already exists, skipping", output)
