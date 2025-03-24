"""
Tests for Writing app views.
"""

import base64
import json
from io import BytesIO
from unittest.mock import patch

import pytest
from django.contrib.auth.models import User
from django.test import Client, TestCase
from django.urls import reverse
from PIL import Image

from apps.writing.models import Glyph, GlyphPracticeProgress
from apps.writing.tests.mocks import (
    MockCharacterRecognitionService,
    MockSVGService,
    MockTemplateService,
)


@pytest.mark.django_db
class WritingViewsTests(TestCase):
    """Tests for Writing app views with mocked services."""

    def setUp(self):
        """Set up test data."""
        # Create test user
        self.user = User.objects.create_user(
            username="testuser", email="test@example.com", password="testpassword"
        )

        # Create test glyphs at different difficulty levels
        self.beginner_glyph = Glyph.objects.create(
            name="a",
            meaning="beginner test",
            difficulty=Glyph.DifficultyLevel.BEGINNER,
        )

        self.intermediate_glyph = Glyph.objects.create(
            name="b",
            meaning="intermediate test",
            difficulty=Glyph.DifficultyLevel.INTERMEDIATE,
        )

        self.advanced_glyph = Glyph.objects.create(
            name="c",
            meaning="advanced test",
            difficulty=Glyph.DifficultyLevel.ADVANCED,
        )

        # Create progress for one glyph
        self.progress = GlyphPracticeProgress.objects.create(
            user=self.user, glyph=self.beginner_glyph, attempts=5, successful_attempts=3
        )

        # Set up client
        self.client = Client()

        # Log in the test user
        self.client.login(username="testuser", password="testpassword")

        # Set up mocks
        self.mock_recognition = MockCharacterRecognitionService()
        self.mock_svg = MockSVGService()
        self.mock_template = MockTemplateService()

    @patch("apps.writing.views.svg_service", MockSVGService())
    def test_index_view(self):
        """Test that index view displays correctly with categorized glyphs."""
        response = self.client.get(reverse("writing:index"))

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "writing/index.html")

        # Check that glyphs are correctly categorized
        self.assertIn(self.beginner_glyph, response.context["beginner_glyphs"])
        self.assertIn(self.intermediate_glyph, response.context["intermediate_glyphs"])
        self.assertIn(self.advanced_glyph, response.context["advanced_glyphs"])

        # Check that user progress is included
        self.assertIn("user_progress", response.context)
        self.assertIn(self.beginner_glyph.id, response.context["user_progress"])
        self.assertEqual(
            response.context["user_progress"][self.beginner_glyph.id]["accuracy"],
            60,  # 3/5 = 60%
        )

        # Check that SVG URLs are included
        self.assertIn("svg_urls", response.context)

    @patch("apps.writing.views.svg_service", MockSVGService())
    def test_practice_view(self):
        """Test that practice view displays correctly."""
        response = self.client.get(reverse("writing:practice", args=["a"]))

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "writing/practice.html")

        # Check context
        self.assertEqual(response.context["glyph"], self.beginner_glyph)
        self.assertEqual(response.context["progress"], self.progress)
        self.assertEqual(response.context["recent_accuracy"], 60)
        self.assertIn("svg_url", response.context)

    @patch(
        "apps.writing.views.character_recognition", MockCharacterRecognitionService()
    )
    def test_check_drawing(self):
        """Test that drawing can be submitted and evaluated."""
        # Create a simple test image and convert to base64
        image = Image.new("RGB", (100, 100), color=(255, 255, 255))
        buffer = BytesIO()
        image.save(buffer, format="PNG")
        base64_image = (
            "data:image/png;base64," + base64.b64encode(buffer.getvalue()).decode()
        )

        # Test data for the drawing submission
        post_data = {
            "glyph_name": "a",
            "image_data": base64_image,
        }

        # Submit the drawing
        response = self.client.post(
            reverse("writing:check_drawing"),
            json.dumps(post_data),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)

        # Parse the response
        data = json.loads(response.content)

        # Validate response structure
        self.assertIn("is_correct", data)
        self.assertIn("similarity", data)
        self.assertIn("feedback", data)
        self.assertIn("attempts", data)
        self.assertIn("successful_attempts", data)
        self.assertIn("accuracy", data)

        # Check that progress was updated
        progress = GlyphPracticeProgress.objects.get(
            user=self.user, glyph=self.beginner_glyph
        )
        self.assertEqual(progress.attempts, 6)  # 5 existing + 1 new

    @patch("apps.writing.views.svg_service", MockSVGService())
    def test_get_svg_content(self):
        """Test getting SVG content."""
        response = self.client.get(reverse("writing:get_svg_content", args=["a"]))

        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertIn("svg_content", data)
        self.assertIn("<svg", data["svg_content"])

        # Test non-existent SVG
        response = self.client.get(
            reverse("writing:get_svg_content", args=["nonexistent"])
        )
        self.assertEqual(response.status_code, 404)

    def test_authentication_required(self):
        """Test that all views require authentication."""
        # Logout first
        self.client.logout()

        # Try to access the pages
        index_response = self.client.get(reverse("writing:index"))
        practice_response = self.client.get(reverse("writing:practice", args=["a"]))
        check_response = self.client.post(
            reverse("writing:check_drawing"),
            json.dumps({"glyph_name": "a", "image_data": "test"}),
            content_type="application/json",
        )
        svg_response = self.client.get(reverse("writing:get_svg_content", args=["a"]))

        # All should redirect to login
        self.assertEqual(index_response.status_code, 302)
        self.assertIn("/accounts/login/", index_response.url)

        self.assertEqual(practice_response.status_code, 302)
        self.assertIn("/accounts/login/", practice_response.url)

        self.assertEqual(check_response.status_code, 302)
        self.assertIn("/accounts/login/", check_response.url)

        self.assertEqual(svg_response.status_code, 302)
        self.assertIn("/accounts/login/", svg_response.url)
