from django.test import TestCase
from django.contrib.auth.models import User
from apps.listening.models import TokiPonaPhrase, ListeningExerciseProgress


class TokiPonaPhraseModelTests(TestCase):
    def setUp(self):
        self.phrase = TokiPonaPhrase.objects.create(
            title="Test Phrase",
            text="mi pona.",
            translations=["I am good.", "I am fine."],
            difficulty=TokiPonaPhrase.DifficultyLevel.BEGINNER,
        )

    def test_phrase_creation(self):
        """Test that a phrase can be created with the appropriate fields"""
        self.assertEqual(self.phrase.title, "Test Phrase")
        self.assertEqual(self.phrase.text, "mi pona.")
        self.assertEqual(self.phrase.translations, ["I am good.", "I am fine."])
        self.assertEqual(
            self.phrase.difficulty, TokiPonaPhrase.DifficultyLevel.BEGINNER
        )
        self.assertEqual(str(self.phrase), "Test Phrase")

    def test_phrase_defaults(self):
        """Test that default values are correctly applied"""
        phrase = TokiPonaPhrase.objects.create(
            text="sina pona.", translations=["You are good."]
        )
        self.assertEqual(phrase.title, "Toki Pona Exercise")
        self.assertEqual(phrase.difficulty, TokiPonaPhrase.DifficultyLevel.BEGINNER)
        self.assertEqual(phrase.transcript, "")
        self.assertIsNone(phrase.youtube_video_id)


class ProgressModelTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="testuser", email="test@example.com", password="testpassword"
        )
        self.phrase = TokiPonaPhrase.objects.create(
            title="Test Phrase",
            text="mi pona.",
            translations=["I am good."],
            difficulty=TokiPonaPhrase.DifficultyLevel.BEGINNER,
        )
        self.progress = ListeningExerciseProgress.objects.create(
            user=self.user,
            phrase=self.phrase,
            total_attempts=10,
            correct_attempts=7,
            completed=True,
        )

    def test_progress_creation(self):
        """Test that progress tracking can be created and tracked"""
        self.assertEqual(self.progress.user, self.user)
        self.assertEqual(self.progress.phrase, self.phrase)
        self.assertEqual(self.progress.total_attempts, 10)
        self.assertEqual(self.progress.correct_attempts, 7)
        self.assertTrue(self.progress.completed)

    def test_accuracy_calculation(self):
        """Test the accuracy percentage calculation"""
        self.assertEqual(self.progress.accuracy, 70.0)

        # Create a new phrase for the empty progress test
        new_phrase = TokiPonaPhrase.objects.create(
            title="Another Test Phrase",
            text="sina pona.",
            translations=["You are good."],
            difficulty=TokiPonaPhrase.DifficultyLevel.BEGINNER,
        )

        # Test edge case with no attempts using a different phrase
        empty_progress = ListeningExerciseProgress.objects.create(
            user=self.user,
            phrase=new_phrase,  # Use the new phrase instead
            total_attempts=0,
            correct_attempts=0,
        )
        self.assertEqual(empty_progress.accuracy, 0)
