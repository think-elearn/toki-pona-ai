from django.contrib.auth.models import User
from django.test import Client, TestCase
from django.urls import reverse

from apps.listening.models import ListeningExerciseProgress, TokiPonaPhrase


class ListeningViewsTests(TestCase):
    def setUp(self):
        # Create a test user
        self.user = User.objects.create_user(
            username="testuser", email="test@example.com", password="testpassword"
        )

        # Create some test phrases
        self.beginner_phrase = TokiPonaPhrase.objects.create(
            title="Beginner Phrase",
            text="toki!",
            translations=["Hello!", "Hi!"],
            difficulty=TokiPonaPhrase.DifficultyLevel.BEGINNER,
        )

        self.intermediate_phrase = TokiPonaPhrase.objects.create(
            title="Intermediate Phrase",
            text="mi wile moku.",
            translations=["I want to eat.", "I need food."],
            difficulty=TokiPonaPhrase.DifficultyLevel.INTERMEDIATE,
        )

        self.advanced_phrase = TokiPonaPhrase.objects.create(
            title="Advanced Phrase",
            text="jan pona mi li tawa ma ante.",
            translations=["My friend goes to another country."],
            difficulty=TokiPonaPhrase.DifficultyLevel.ADVANCED,
        )

        # Set up the test client
        self.client = Client()

        # Log in the test user
        self.client.login(username="testuser", password="testpassword")

    def test_index_view(self):
        """Test the index view displays correctly"""
        response = self.client.get(reverse("listening:index"))

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "listening/index.html")

        # Check that phrases are correctly categorized
        self.assertIn(self.beginner_phrase, response.context["beginner_phrases"])
        self.assertIn(
            self.intermediate_phrase, response.context["intermediate_phrases"]
        )
        self.assertIn(self.advanced_phrase, response.context["advanced_phrases"])

    def test_exercise_view(self):
        """Test the exercise view displays correctly"""
        response = self.client.get(
            reverse("listening:exercise", args=[self.beginner_phrase.id])
        )

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "listening/practice.html")
        self.assertIn("phrase", response.context)
        self.assertEqual(response.context["phrase"], self.beginner_phrase)

    def test_check_translation_success(self):
        """Test that correct translations are validated properly"""
        response = self.client.post(
            reverse("listening:check_translation"),
            {"phrase_id": self.beginner_phrase.id, "translation": "Hello!"},
            headers={"hx-request": "true"},  # Simulate HTMX request
        )

        self.assertEqual(response.status_code, 200)

        # Check that progress was updated
        progress = ListeningExerciseProgress.objects.get(
            user=self.user, phrase=self.beginner_phrase
        )

        self.assertEqual(progress.correct_attempts, 1)
        self.assertEqual(progress.total_attempts, 1)
        self.assertTrue(progress.completed)

        # Check response contains success indicators
        self.assertIn(b"alert-success", response.content)
        self.assertIn(b"Correct", response.content)

    def test_check_translation_failure(self):
        """Test that incorrect translations are properly handled"""
        response = self.client.post(
            reverse("listening:check_translation"),
            {
                "phrase_id": self.beginner_phrase.id,
                "translation": "Goodbye!",  # Incorrect translation
            },
            headers={"hx-request": "true"},  # Simulate HTMX request
        )

        self.assertEqual(response.status_code, 200)

        # Check that progress was updated (only total attempts)
        progress = ListeningExerciseProgress.objects.get(
            user=self.user, phrase=self.beginner_phrase
        )

        self.assertEqual(progress.correct_attempts, 0)
        self.assertEqual(progress.total_attempts, 1)
        self.assertFalse(progress.completed)

        # Check response contains failure indicators
        self.assertIn(b"alert-warning", response.content)
        self.assertIn(b"Try Again", response.content)

    def test_authentication_required(self):
        """Test that views require authentication"""
        # Log out
        self.client.logout()

        # Try to access views
        index_response = self.client.get(reverse("listening:index"))
        exercise_response = self.client.get(
            reverse("listening:exercise", args=[self.beginner_phrase.id])
        )
        check_response = self.client.post(
            reverse("listening:check_translation"),
            {"phrase_id": self.beginner_phrase.id, "translation": "Hello!"},
            headers={"hx-request": "true"},
        )

        # All should redirect to login
        self.assertEqual(index_response.status_code, 302)
        self.assertTrue(index_response.url.startswith("/accounts/login/"))

        self.assertEqual(exercise_response.status_code, 302)
        self.assertTrue(exercise_response.url.startswith("/accounts/login/"))

        self.assertEqual(check_response.status_code, 302)
        self.assertTrue(check_response.url.startswith("/accounts/login/"))
