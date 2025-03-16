from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User
from apps.signing.models import SignReference, SigningProgress
import json


class SigningViewsTests(TestCase):
    def setUp(self):
        # Create test user
        self.user = User.objects.create_user(
            username="testuser", email="test@example.com", password="testpassword"
        )

        # Create test signs at different difficulty levels
        self.beginner_sign = SignReference.objects.create(
            name="beginner",
            meaning="beginner test",
            difficulty=SignReference.DifficultyLevel.BEGINNER,
        )

        self.intermediate_sign = SignReference.objects.create(
            name="intermediate",
            meaning="intermediate test",
            difficulty=SignReference.DifficultyLevel.INTERMEDIATE,
        )

        self.advanced_sign = SignReference.objects.create(
            name="advanced",
            meaning="advanced test",
            difficulty=SignReference.DifficultyLevel.ADVANCED,
        )

        # Create progress for one sign
        self.progress = SigningProgress.objects.create(
            user=self.user, sign=self.beginner_sign, attempts=5, successful_attempts=3
        )

        # Set up client
        self.client = Client()

        # Log in the test user
        self.client.login(username="testuser", password="testpassword")

    def test_index_view(self):
        """Test that index view displays correctly with categorized signs"""
        response = self.client.get(reverse("signing:index"))

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "signing/index.html")

        # Check that signs are correctly categorized
        self.assertIn(self.beginner_sign, response.context["beginner_signs"])
        self.assertIn(self.intermediate_sign, response.context["intermediate_signs"])
        self.assertIn(self.advanced_sign, response.context["advanced_signs"])

        # Check that user progress is included
        self.assertIn("user_progress", response.context)
        self.assertIn(self.beginner_sign.id, response.context["user_progress"])
        self.assertEqual(
            response.context["user_progress"][self.beginner_sign.id]["accuracy"],
            60,  # 3/5 = 60%
        )

    def test_practice_view(self):
        """Test that practice view displays correctly"""
        response = self.client.get(
            reverse("signing:practice", args=[self.beginner_sign.id])
        )

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "signing/practice.html")

        # Check context
        self.assertEqual(response.context["sign"], self.beginner_sign)
        self.assertEqual(response.context["progress"], self.progress)

    def test_analyze_sign(self):
        """Test that sign analysis works"""
        # Test data for the sign submission
        post_data = {
            "sign_id": self.beginner_sign.id,
            "landmarks": [[0.1, 0.1, 0.1], [0.2, 0.2, 0.1]],  # Minimal test data
        }

        # Since we're using a simulated recognition, this should work
        response = self.client.post(
            reverse("signing:analyze_sign"),
            json.dumps(post_data),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)

        # Parse the response
        data = json.loads(response.content)

        # Validate response structure
        self.assertIn("similarity_score", data)
        self.assertIn("feedback", data)
        self.assertIn("is_successful", data)
        self.assertIn("areas_for_improvement", data)
        self.assertIn("attempts", data)
        self.assertIn("successful_attempts", data)
        self.assertIn("accuracy", data)

        # Check that progress was updated
        progress = SigningProgress.objects.get(user=self.user, sign=self.beginner_sign)
        self.assertEqual(progress.attempts, 6)  # 5 existing + 1 new

    def test_authentication_required(self):
        """Test that all views require authentication"""
        # Logout first
        self.client.logout()

        # Try to access the pages
        index_response = self.client.get(reverse("signing:index"))
        practice_response = self.client.get(
            reverse("signing:practice", args=[self.beginner_sign.id])
        )
        analyze_response = self.client.post(
            reverse("signing:analyze_sign"),
            json.dumps({"sign_id": self.beginner_sign.id, "landmarks": []}),
            content_type="application/json",
        )

        # All should redirect to login
        self.assertEqual(index_response.status_code, 302)
        self.assertIn("/accounts/login/", index_response.url)

        self.assertEqual(practice_response.status_code, 302)
        self.assertIn("/accounts/login/", practice_response.url)

        self.assertEqual(analyze_response.status_code, 302)
        self.assertIn("/accounts/login/", analyze_response.url)
