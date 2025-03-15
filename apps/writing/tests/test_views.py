from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User
from apps.writing.models import Glyph, GlyphPracticeProgress
import json


class WritingViewsTests(TestCase):
    def setUp(self):
        # Create test user
        self.user = User.objects.create_user(
            username="testuser", email="test@example.com", password="testpassword"
        )

        # Create test glyphs at different difficulty levels
        self.beginner_glyph = Glyph.objects.create(
            name="beginner",
            meaning="beginner test",
            difficulty=Glyph.DifficultyLevel.BEGINNER,
        )

        self.intermediate_glyph = Glyph.objects.create(
            name="intermediate",
            meaning="intermediate test",
            difficulty=Glyph.DifficultyLevel.INTERMEDIATE,
        )

        self.advanced_glyph = Glyph.objects.create(
            name="advanced",
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

    def test_index_view(self):
        """Test that index view displays correctly with categorized glyphs"""
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

    def test_practice_view(self):
        """Test that practice view displays correctly"""
        response = self.client.get(reverse("writing:practice", args=["beginner"]))

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "writing/practice.html")

        # Check context
        self.assertEqual(response.context["glyph"], self.beginner_glyph)
        self.assertEqual(response.context["progress"], self.progress)
        self.assertEqual(response.context["recent_accuracy"], 60)

    def test_check_drawing(self):
        """Test that drawing can be submitted and evaluated"""
        # Test data for the drawing submission
        post_data = {
            "glyph_name": "beginner",
            # Break the long line into multiple lines
            "image_data": (
                "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAA"  # Minimal test data
            ),
        }

        # Since we're using a simulated recognition, this should work
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

    def test_authentication_required(self):
        """Test that all views require authentication"""
        # Logout first
        self.client.logout()

        # Try to access the pages
        index_response = self.client.get(reverse("writing:index"))
        practice_response = self.client.get(
            reverse("writing:practice", args=["beginner"])
        )
        check_response = self.client.post(
            reverse("writing:check_drawing"),
            json.dumps({"glyph_name": "beginner", "image_data": "test"}),
            content_type="application/json",
        )

        # All should redirect to login
        self.assertEqual(index_response.status_code, 302)
        self.assertIn("/accounts/login/", index_response.url)

        self.assertEqual(practice_response.status_code, 302)
        self.assertIn("/accounts/login/", practice_response.url)

        self.assertEqual(check_response.status_code, 302)
        self.assertIn("/accounts/login/", check_response.url)
