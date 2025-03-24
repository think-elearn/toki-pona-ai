from django.contrib.auth.models import User
from django.test import TestCase

from apps.signing.models import SigningProgress, SignReference


class SignReferenceModelTests(TestCase):
    def setUp(self):
        self.sign = SignReference.objects.create(
            name="test_sign",
            meaning="test meaning",
            description="test description",
            difficulty=SignReference.DifficultyLevel.BEGINNER,
            example_sentence="mi test",
        )

    def test_str_method(self):
        """Test that the string representation of a sign is its name"""
        self.assertEqual(str(self.sign), "test_sign")

    def test_sign_creation(self):
        """Test that a sign can be created with proper fields"""
        self.assertEqual(self.sign.name, "test_sign")
        self.assertEqual(self.sign.meaning, "test meaning")
        self.assertEqual(self.sign.description, "test description")
        self.assertEqual(self.sign.difficulty, SignReference.DifficultyLevel.BEGINNER)
        self.assertEqual(self.sign.example_sentence, "mi test")
        self.assertEqual(str(self.sign), "test_sign")

    def test_sign_defaults(self):
        """Test that default values are set correctly"""
        sign = SignReference.objects.create(name="defaults", meaning="testing defaults")
        self.assertEqual(sign.difficulty, SignReference.DifficultyLevel.BEGINNER)
        self.assertEqual(sign.description, "")
        self.assertEqual(sign.example_sentence, "")

        # Check that video and thumbnail fields are None since null=True is set
        self.assertIsNone(sign.video.name)
        self.assertIsNone(sign.thumbnail.name)


class SigningProgressTests(TestCase):
    def setUp(self):
        # Create test user
        self.user = User.objects.create_user(
            username="testuser", email="test@example.com", password="testpassword"
        )

        # Create test sign
        self.sign = SignReference.objects.create(
            name="test_sign", meaning="test meaning"
        )

        # Create progress
        self.progress = SigningProgress.objects.create(
            user=self.user, sign=self.sign, attempts=10, successful_attempts=7
        )

    def test_str_method(self):
        """Test the string representation of progress shows user and sign names"""
        expected_str = f"{self.user.username}'s progress on '{self.sign.name}'"
        self.assertEqual(str(self.progress), expected_str)

    def test_progress_creation(self):
        """Test that progress can be created and tracked"""
        self.assertEqual(self.progress.user, self.user)
        self.assertEqual(self.progress.sign, self.sign)
        self.assertEqual(self.progress.attempts, 10)
        self.assertEqual(self.progress.successful_attempts, 7)
        self.assertFalse(self.progress.mastered)

    def test_accuracy_calculation(self):
        """Test the accuracy percentage calculation"""
        # 7 out of 10 = 70%
        self.assertEqual(self.progress.accuracy, 70)

        # Test with no attempts
        empty_progress = SigningProgress.objects.create(
            user=self.user,
            sign=SignReference.objects.create(name="empty", meaning="empty test"),
        )
        self.assertEqual(empty_progress.accuracy, 0)

    def test_mastery_tracking(self):
        """Test that mastery is tracked correctly"""
        # Default is false
        self.assertFalse(self.progress.mastered)

        # Set to true
        self.progress.mastered = True
        self.progress.save()

        # Retrieve and check
        updated_progress = SigningProgress.objects.get(id=self.progress.id)
        self.assertTrue(updated_progress.mastered)
